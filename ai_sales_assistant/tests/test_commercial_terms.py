"""Mandatory commercial terms: extraction, formatting, verification and the single retry."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import Language
from app.core.exceptions import CommercialTermsMissingError
from app.repositories import GenerationRepository, UserRepository
from app.schemas.generation import GenerationCreate
from app.services.commercial_terms import figures_in, find_missing, needs_terms, terms_for
from app.services.generation_service import GenerationService
from tests.factories import OWNER, generation_payload, make_user
from tests.fakes import FakeAIProvider

SCALE = (
    "Oferta por volumen:\n"
    "- De 1 a 5 contenedores: precio habitual, sin descuento.\n"
    "- De 6 a 10 contenedores: 5 % de descuento.\n"
    "- De 11 a 20 contenedores: 10 % de descuento.\n"
    "- De 21 a 50 contenedores: 15 % de descuento.\n"
    "- Más de 50 contenedores: 20 % de descuento."
)
TIERS = [
    "De 1 a 5 contenedores: precio habitual, sin descuento.",
    "De 6 a 10 contenedores: 5 % de descuento.",
    "De 11 a 20 contenedores: 10 % de descuento.",
    "De 21 a 50 contenedores: 15 % de descuento.",
    "Más de 50 contenedores: 20 % de descuento.",
]
STRUCTURED = ["Precio habitual: 15.000,00 €", "Descuento aplicado: 15 %", "Ahorro: 2.250,00 €", "Precio final: 12.750,00 €"]


def all_terms(needs: str = SCALE, price: str | None = "15000", discount: str | None = "15"):
    return terms_for(
        language=Language.SPANISH,
        customer_needs=needs,
        price=Decimal(price) if price else None,
        discount_percent=Decimal(discount) if discount else None,
    )


def email(*lines: str) -> str:
    return "Asunto: Oferta\n\nEstimada María:\n\nLe presentamos la oferta.\n" + "\n".join(lines) + "\n\nAtentamente,\nCarlos Vila"


def missing_texts(text: str, **kwargs) -> list[str]:
    return [term.text for term in find_missing(all_terms(**kwargs), text)]


# --- Extraction ------------------------------------------------------------------------------------------


def test_the_container_example_gives_four_structured_lines_and_five_tiers() -> None:
    assert [term.text for term in all_terms()] == STRUCTURED + TIERS


def test_lines_without_figures_are_not_mandatory() -> None:
    needs = "Asunto: Oferta especial\nCuantos más contenedores adquiera, mayor será el ahorro.\n" + SCALE

    assert [term.text for term in needs_terms(needs)] == TIERS


def test_dates_deadlines_and_rates_are_kept() -> None:
    needs = "Entrega en 15 días laborables. Oferta válida hasta el 31/12/2026.\nTarifa: 49,99 € al mes."

    assert [term.text for term in needs_terms(needs)] == [
        "Entrega en 15 días laborables.",
        "Oferta válida hasta el 31/12/2026.",
        "Tarifa: 49,99 € al mes.",
    ]


def test_without_structured_pricing_only_the_needs_are_mandatory() -> None:
    assert [term.text for term in all_terms(price=None, discount=None)] == TIERS


def test_price_without_discount() -> None:
    assert [term.text for term in all_terms(needs="", price="179", discount=None)] == ["Precio: 179,00 €"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("15.000,00 €", ["15000.00"]),
        ("€15,000.00", ["15000.00"]),
        ("15 000,00 €", ["15000.00"]),
        ("15000", ["15000.00"]),
        ("2.250", ["2250.00"]),
        ("49,99 € y 49.99 €", ["49.99", "49.99"]),
        ("15 % o 15%", ["15.00", "15.00"]),
        ("De 21 a 50", ["21.00", "50.00"]),
        ("hasta el 31/12/2026", ["date:31/12/2026"]),
    ],
)
def test_figures_are_compared_by_value(text: str, expected: list[str]) -> None:
    assert figures_in(text) == expected


# --- Verification ---------------------------------------------------------------------------------------


def test_complete_text_misses_nothing() -> None:
    assert missing_texts(email(*STRUCTURED, "Oferta por volumen:", *TIERS)) == []


def test_other_number_formats_are_accepted() -> None:
    text = email(
        "Precio habitual: 15000 €", "Descuento: 15%", "Ahorro de 2250,00 €", "Precio final: 12.750 €",
        "- 1 a 5 contenedores: sin descuento", "- 6-10 contenedores: 5%", "- 11-20 contenedores: 10%",
        "- 21-50 contenedores: 15%", "- más de 50 contenedores: 20%",
    )

    assert missing_texts(text) == []


TIERS_EN = [
    "1 to 5 containers: regular price, no discount.",
    "6 to 10 containers: 5% discount.",
    "11 to 20 containers: 10% discount.",
    "21 to 50 containers: 15% discount.",
    "More than 50 containers: 20% discount.",
]
STRUCTURED_EN = ["Regular price: €15,000.00", "Discount applied: 15%", "Saving: €2,250.00", "Final price: €12,750.00"]


def test_terms_translated_into_the_output_language_are_accepted() -> None:
    # Only the figures are verified, so the AI may translate the Spanish wording of each term.
    assert missing_texts(email(*STRUCTURED_EN, "Volume offer:", *TIERS_EN)) == []


def test_a_changed_figure_in_a_translated_term_is_detected() -> None:
    changed = [*TIERS_EN[:3], "21 to 50 containers: 16% discount.", *TIERS_EN[4:]]

    assert missing_texts(email(*STRUCTURED_EN, *changed)) == [TIERS[3]]


def test_a_missing_tier_is_detected() -> None:
    assert missing_texts(email(*STRUCTURED, *TIERS[:2], *TIERS[3:])) == [TIERS[2]]


def test_a_changed_figure_is_detected() -> None:
    changed = [*TIERS[:1], "De 6 a 10 contenedores: 6 % de descuento.", *TIERS[2:]]

    assert missing_texts(email(*STRUCTURED, *changed)) == [TIERS[1]]


def test_a_summarised_scale_is_detected() -> None:
    assert missing_texts(email(*STRUCTURED, "Ofrecemos descuentos de hasta el 20 % por volumen.")) == TIERS


def test_keeping_only_the_highest_discount_is_detected() -> None:
    assert missing_texts(email(*STRUCTURED, TIERS[-1])) == TIERS[:-1]


def test_missing_structured_values_are_detected() -> None:
    assert missing_texts(email("Precio final: 12.750,00 €", *TIERS)) == [STRUCTURED[0], STRUCTURED[1], STRUCTURED[2]]


def test_the_15_percent_tier_does_not_count_as_the_structured_discount() -> None:
    # Independent data: the tier line belongs to the tier, the structured 15 % needs its own mention.
    text = email("Precio habitual: 15.000,00 €", "Ahorro: 2.250,00 €", "Precio final: 12.750,00 €", *TIERS)

    assert missing_texts(text) == ["Descuento aplicado: 15 %"]


def test_numbers_scattered_across_lines_do_not_count_as_a_tier() -> None:
    text = email(*STRUCTURED, "Tenemos 6 tipos de contenedor.", "Entrega en 10 días.", "Margen del 5 %.", *TIERS[:1], *TIERS[2:])

    assert missing_texts(text) == [TIERS[1]]


def test_the_real_ollama_output_from_the_bug_report() -> None:
    # What llama3.2:3b returned for the container example before this change.
    text = (
        "Asunto: Oferta especial por volumen – Contenedores para el sector pesquero\n\n"
        "Nuestra oferta por volumen ofrece descuentos cada vez más significativos según la cantidad.\n"
        "Atentamente,\nCarlos Vila\nSinerkia"
    )

    assert missing_texts(text) == STRUCTURED + TIERS


# --- Retry in the service ---------------------------------------------------------------------------------


@pytest.fixture
def owner(db_session: Session) -> None:
    db_session.add(make_user(id=OWNER))
    db_session.commit()


def service(db_session: Session, provider: FakeAIProvider, **options) -> GenerationService:
    return GenerationService(db_session, GenerationRepository(db_session), lambda: provider, **options)


def case_3() -> GenerationCreate:
    return GenerationCreate.model_validate(generation_payload(customer_needs=SCALE, price="15000", discount_percent="15"))


COMPLETE = email(*STRUCTURED, "Oferta por volumen:", *TIERS)
INCOMPLETE = email("Precio final: 12.750,00 €", "Descuentos de hasta el 20 %.")


def test_complete_first_answer_needs_no_retry(db_session: Session, owner: None) -> None:
    provider = FakeAIProvider(content=COMPLETE)

    result = service(db_session, provider).generate(case_3(), user_id=OWNER)

    assert len(provider.prompts) == 1
    assert result.missing_commercial_terms == []


def test_incomplete_answer_is_retried_once_and_the_complete_one_is_kept(db_session: Session, owner: None) -> None:
    provider = FakeAIProvider()
    provider.responses = [INCOMPLETE, COMPLETE]

    result = service(db_session, provider).generate(case_3(), user_id=OWNER)

    assert len(provider.prompts) == 2
    assert result.generated_content == COMPLETE
    assert result.missing_commercial_terms == []
    retry = provider.prompts[1].user
    assert "<previous_draft>" in retry and INCOMPLETE.splitlines()[0] in retry
    assert "Your previous draft left out these mandatory commercial terms:\n- Precio habitual: 15.000,00 €" in retry
    # Token usage covers both calls; the AI-call counter too.
    stored = GenerationRepository(db_session).get_by_id(result.id)
    assert (stored.prompt_tokens, stored.completion_tokens) == (200, 100)
    assert UserRepository(db_session).ai_generation_count(OWNER) == 2


def test_still_incomplete_after_the_retry_is_saved_with_the_warning(db_session: Session, owner: None) -> None:
    provider = FakeAIProvider(content=INCOMPLETE)

    result = service(db_session, provider).generate(case_3(), user_id=OWNER)

    assert len(provider.prompts) == 2  # exactly one retry
    assert result.generated_content == INCOMPLETE  # never edited by the application
    assert result.missing_commercial_terms == STRUCTURED[:3] + TIERS


def test_the_retry_keeps_the_better_attempt(db_session: Session, owner: None) -> None:
    provider = FakeAIProvider()
    provider.responses = [email(*STRUCTURED, *TIERS[:4]), INCOMPLETE]

    result = service(db_session, provider).generate(case_3(), user_id=OWNER)

    assert result.missing_commercial_terms == [TIERS[4]]


def test_retries_can_be_disabled(db_session: Session, owner: None) -> None:
    provider = FakeAIProvider(content=INCOMPLETE)

    service(db_session, provider, commercial_terms_max_retries=0).generate(case_3(), user_id=OWNER)

    assert len(provider.prompts) == 1


def test_strict_mode_rejects_without_saving(db_session: Session, owner: None) -> None:
    provider = FakeAIProvider(content=INCOMPLETE)

    with pytest.raises(CommercialTermsMissingError) as error:
        service(db_session, provider, commercial_terms_strict=True).generate(case_3(), user_id=OWNER)

    assert error.value.status_code == 502
    assert error.value.missing == STRUCTURED[:3] + TIERS
    assert GenerationRepository(db_session).count(user_id=OWNER) == 0
    assert UserRepository(db_session).ai_generation_count(OWNER) == 2  # the calls still count


def test_regenerate_is_verified_too(db_session: Session, owner: None) -> None:
    provider = FakeAIProvider(content=COMPLETE)
    created = service(db_session, provider).generate(case_3(), user_id=OWNER)
    provider.responses = [INCOMPLETE, COMPLETE]

    updated = service(db_session, provider).regenerate(created.id, case_3(), user_id=OWNER)

    assert len(provider.prompts) == 3
    assert updated.missing_commercial_terms == []


def test_no_commercial_data_means_no_check_and_no_retry(db_session: Session, owner: None) -> None:
    provider = FakeAIProvider(content="Texto sin cifras.")

    result = service(db_session, provider).generate(
        GenerationCreate.model_validate(generation_payload()), user_id=OWNER
    )

    assert len(provider.prompts) == 1
    assert result.missing_commercial_terms == []


# --- Through the API: the three cases, guests and strict mode ---------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "complete", "expected_terms"),
    [
        ({"customer_needs": SCALE}, email(*TIERS), TIERS),
        ({"price": "15000", "discount_percent": "15"}, email(*STRUCTURED), STRUCTURED),
        ({"customer_needs": SCALE, "price": "15000", "discount_percent": "15"}, COMPLETE, STRUCTURED + TIERS),
    ],
    ids=["case-1-needs-only", "case-2-structured-only", "case-3-both"],
)
def test_three_cases_through_the_api(
    client: TestClient, fake_ai_provider: FakeAIProvider, overrides: dict, complete: str, expected_terms: list[str]
) -> None:
    fake_ai_provider.responses = ["Texto que lo omite todo.", complete]

    response = client.post("/api/v1/generate", json=generation_payload(**overrides))

    assert response.status_code == 201
    body = response.json()
    assert body["missing_commercial_terms"] == []
    assert body["generated_content"] == complete
    mandatory = fake_ai_provider.prompts[0].user.split("<mandatory_commercial_terms>")[1]
    for term in expected_terms:
        assert f"- {term}" in mandatory
    # The user's text is stored unchanged.
    assert body["customer_needs"] == generation_payload(**overrides)["customer_needs"]


def test_api_reports_missing_terms_in_create_list_and_get(client: TestClient, fake_ai_provider: FakeAIProvider) -> None:
    fake_ai_provider.content = INCOMPLETE

    created = client.post("/api/v1/generate", json=case_3().model_dump(mode="json")).json()

    expected = STRUCTURED[:3] + TIERS
    assert created["missing_commercial_terms"] == expected
    assert client.get(f"/api/v1/generations/{created['id']}").json()["missing_commercial_terms"] == expected
    assert client.get("/api/v1/generations").json()["items"][0]["missing_commercial_terms"] == expected


def test_strict_mode_through_the_api(client: TestClient, fake_ai_provider: FakeAIProvider, test_settings) -> None:
    test_settings.commercial_terms_strict = True
    fake_ai_provider.content = INCOMPLETE

    response = client.post("/api/v1/generate", json=case_3().model_dump(mode="json"))

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "commercial_terms_missing"
    assert client.get("/api/v1/generations").json()["total"] == 0


def test_guest_retry_respects_the_generation_limit(anon_client: TestClient, fake_ai_provider: FakeAIProvider, test_settings) -> None:
    test_settings.guest_max_generations = 1
    anon_client.post("/api/v1/auth/guest")
    fake_ai_provider.content = INCOMPLETE

    body = anon_client.post("/api/v1/generate", json=case_3().model_dump(mode="json")).json()

    # Only one call allowed: no retry, and the warning tells the guest what is missing.
    assert len(fake_ai_provider.prompts) == 1
    assert body["missing_commercial_terms"]


def test_strict_mode_is_off_by_default(test_settings) -> None:
    assert test_settings.commercial_terms_strict is False
    assert test_settings.commercial_terms_max_retries == 1
