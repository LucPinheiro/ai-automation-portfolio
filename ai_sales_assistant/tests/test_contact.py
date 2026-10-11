"""/contacto: demo support details and the contact form (demo mode: validated, never sent)."""

import html
import logging
import re

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.schemas.contact import CONTACT_LIMITS, ContactCategory, ContactMessage
from app.services.contact import ContactService

BROWSER = {"Origin": "http://testserver"}
DEMO_RESULT = "Formulario en modo demostración: hemos comprobado tus datos, pero el mensaje no se ha enviado."
VALID = {
    "name": "Ana Ruiz",
    "email": "ana@example.com",
    "category": "api",
    "subject": "Error 502 al generar",
    "message": "Al generar un email recibo un error 502.\nOcurre desde esta mañana.",
    "privacy_accepted": "yes",
}


def post(client: TestClient, **overrides: str):
    return client.post("/contacto", data={**VALID, **overrides}, headers=BROWSER)


def field_error(page: str, field: str) -> str | None:
    match = re.search(rf'id="contact-{field}-error">([^<]*)<', page)
    return html.unescape(match.group(1)) if match else None


# --- Support details ----------------------------------------------------------------------------------


def test_demo_support_details_with_links(anon_client: TestClient) -> None:
    page = anon_client.get("/contacto").text

    assert '<a href="mailto:soporte@aisalesassistant.demo">soporte@aisalesassistant.demo</a>' in page
    assert '<a href="tel:+34600123456">+34 600 123 456</a>' in page
    assert "Lunes a viernes · 09:00–18:00" in page
    assert '<span class="demo-badge" id="demo-data-badge">Datos de demostración</span>' in page


def test_demo_defaults_are_marked_in_the_settings() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.support_email == "soporte@aisalesassistant.demo"
    assert settings.support_phone == "+34 600 123 456"
    assert (settings.support_hours_open, settings.support_hours_close) == ("09:00", "18:00")
    assert settings.support_contact_is_demo is True
    assert settings.contact_form_mode == "demo"


def test_real_details_hide_the_demo_label(anon_client: TestClient, test_settings: Settings) -> None:
    test_settings.support_contact_is_demo = False
    test_settings.support_email = "help@example.com"
    test_settings.support_hours_open = "08:30"

    page = anon_client.get("/contacto").text

    assert 'id="demo-data-badge"' not in page
    assert "mailto:help@example.com" in page
    assert "Lunes a viernes · 08:30–18:00" in page


def test_api_incidents_section(anon_client: TestClient) -> None:
    page = anon_client.get("/contacto").text
    incidents = page.split('id="incidents"')[1].split("</section>")[0]

    for item in ("La fecha y hora en que ocurrió.", "La operación que estabas realizando.", "El mensaje de error que viste."):
        assert f"<li>{item}</li>" in incidents
    assert "Nunca envíes contraseñas, tokens, claves de API ni claves privadas." in incidents
    assert '<a href="/docs" target="_blank" rel="noopener">Abrir la documentación de la API</a>' in incidents


def test_support_details_come_before_the_form(anon_client: TestClient) -> None:
    page = anon_client.get("/contacto").text

    assert page.index('class="contact-info"') < page.index('id="contact-form"')


# --- Form rendering -------------------------------------------------------------------------------------


def test_form_fields_and_button(anon_client: TestClient) -> None:
    page = anon_client.get("/contacto").text
    form = page.split('<form id="contact-form"')[1].split("</form>")[0]

    assert 'method="post" action="/contacto"' in page
    for name, label in (("name", "Nombre"), ("email", "Email"), ("category", "Tipo de consulta"),
                        ("subject", "Asunto"), ("message", "Mensaje")):
        assert f'name="{name}"' in form
        assert f'>{label} <span aria-hidden="true">*</span></label>' in form
    assert '<textarea id="contact-message" name="message"' in form and 'rows="7"' in form
    assert 'type="email"' in form
    assert '<button type="submit" id="contact-submit" class="btn-access-primary">Enviar mensaje</button>' in form
    assert "Envíanos un mensaje" in page
    assert "Formulario en versión de demostración: por ahora no envía mensajes." in page


def test_category_options(anon_client: TestClient) -> None:
    page = anon_client.get("/contacto").text
    select = page.split('<select id="contact-category"')[1].split("</select>")[0]

    options = re.findall(r'<option value="([^"]*)"[^>]*>([^<]+)</option>', select)
    assert options == [
        ("", "Selecciona una opción"),
        ("soporte_tecnico", "Soporte técnico"),
        ("api", "Problema con la API"),
        ("cuenta", "Cuenta y acceso"),
        ("facturacion", "Facturación"),
        ("comercial", "Consulta comercial"),
        ("otra", "Otra consulta"),
    ]
    assert [value for value, _ in options[1:]] == [category.value for category in ContactCategory]


@pytest.mark.parametrize("field", ["name", "email", "subject", "message"])
def test_inputs_carry_the_length_limits(anon_client: TestClient, field: str) -> None:
    page = anon_client.get("/contacto").text

    assert re.search(rf'id="contact-{field}"[^>]*maxlength="{CONTACT_LIMITS[field][1]}"', page)


# --- Submission -----------------------------------------------------------------------------------------


def test_valid_message_shows_the_demo_notice_and_clears_the_form(anon_client: TestClient) -> None:
    response = post(anon_client)

    assert response.status_code == 200
    assert f'<div class="alert alert-info" role="status" id="contact-demo-result">{DEMO_RESULT}</div>' in response.text
    assert "Ana Ruiz" not in response.text  # form cleared
    assert 'id="contact-errors"' not in response.text


def test_demo_mode_sends_stores_and_logs_nothing(
    anon_client: TestClient, fake_email_sender, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        post(anon_client)

    assert fake_email_sender.messages == []
    assert "Error 502 al generar" not in caplog.text
    assert "ana@example.com" not in caplog.text


def test_contact_service_never_claims_delivery() -> None:
    result = ContactService("demo").submit(ContactMessage.model_validate(VALID))

    assert (result.delivered, result.mode) == (False, "demo")


@pytest.mark.parametrize(
    ("overrides", "field", "message"),
    [
        ({"name": ""}, "name", "Este campo es obligatorio."),
        ({"name": "A"}, "name", "Escribe al menos 2 caracteres."),
        ({"name": "x" * 101}, "name", "Escribe como máximo 100 caracteres."),
        ({"email": "no-es-un-email"}, "email", "Introduce un email válido."),
        ({"email": ""}, "email", "Introduce un email válido."),
        ({"category": ""}, "category", "Selecciona un tipo de consulta de la lista."),
        ({"category": "hacker"}, "category", "Selecciona un tipo de consulta de la lista."),
        ({"subject": "Hi"}, "subject", "Escribe al menos 3 caracteres."),
        ({"subject": "Hola\r\nBcc: victima@example.com"}, "subject", "Escríbelo en una sola línea."),
        ({"name": "Ana\nRuiz"}, "name", "Escríbelo en una sola línea."),
        ({"message": "corto"}, "message", "Escribe al menos 10 caracteres."),
        ({"message": "x" * 4001}, "message", "Escribe como máximo 4000 caracteres."),
        ({"message": "<script>alert(1)</script> hola hola"}, "message", "No se permiten etiquetas HTML ni los caracteres < y >."),
        ({"name": "<b>Ana</b>"}, "name", "No se permiten etiquetas HTML ni los caracteres < y >."),
        ({"subject": "Asunto \x07 raro"}, "subject", "Contiene caracteres no permitidos."),
    ],
)
def test_invalid_fields_are_reported_in_spanish(anon_client: TestClient, overrides: dict, field: str, message: str) -> None:
    response = post(anon_client, **overrides)

    assert response.status_code == 422
    assert field_error(response.text, field) == message
    assert 'id="contact-errors"' in response.text
    assert DEMO_RESULT not in response.text


def test_typed_values_are_kept_and_escaped_after_an_error(anon_client: TestClient) -> None:
    response = post(anon_client, name="<b>Ana</b>", subject='Asunto con "comillas" & más')

    assert "<b>Ana</b>" not in response.text  # never rendered as HTML
    assert "&lt;b&gt;Ana&lt;/b&gt;" in response.text
    assert "Asunto con &#34;comillas&#34; &amp; más" in response.text
    assert ">Al generar un email recibo un error 502.\nOcurre desde esta mañana.</textarea>" in response.text


def test_errors_do_not_reveal_internals(anon_client: TestClient) -> None:
    page = post(anon_client, email="x", category="nope").text

    for internal in ("Traceback", "pydantic", "value_error", "ValidationError", "enum"):
        assert internal not in page


def test_message_with_accents_up_to_the_limit_is_accepted(anon_client: TestClient) -> None:
    # 4000 accented characters are far more than 4 KB once URL-encoded.
    response = post(anon_client, message="ñ" * 4000)

    assert response.status_code == 200
    assert DEMO_RESULT in response.text


def test_oversized_body_is_rejected_without_being_parsed(anon_client: TestClient) -> None:
    response = post(anon_client, message="x" * 40_000)

    assert response.status_code == 422


def test_cross_site_posts_are_rejected(anon_client: TestClient) -> None:
    response = anon_client.post("/contacto", data=VALID, headers={"Origin": "https://evil.example"})

    assert response.status_code == 403


def test_works_for_logged_in_users_and_guests(client: TestClient) -> None:
    assert post(client).status_code == 200


def test_crlf_in_the_message_is_normalised() -> None:
    message = ContactMessage.model_validate({**VALID, "message": "Línea uno\r\nLínea dos\rLínea tres"})

    assert message.message == "Línea uno\nLínea dos\nLínea tres"


def test_unknown_fields_are_rejected_by_the_schema() -> None:
    with pytest.raises(ValidationError):
        ContactMessage.model_validate({**VALID, "admin": "true"})


def test_every_category_has_a_spanish_label() -> None:
    from app.i18n.es import MESSAGES

    assert all(f"contact.category.{category.value}" in MESSAGES for category in ContactCategory)


# --- GDPR: consent checkbox and first-layer information ---------------------------------------


def consent_checkbox(page: str) -> str:
    match = re.search(r'<input id="contact-privacy"[^>]*>', page)
    assert match, "consent checkbox not found"
    return match.group(0)


def test_consent_checkbox_is_required_and_unticked_by_default(anon_client: TestClient) -> None:
    checkbox = consent_checkbox(anon_client.get("/contacto").text)

    assert 'type="checkbox"' in checkbox and 'name="privacy_accepted"' in checkbox and 'value="yes"' in checkbox
    assert "required" in checkbox
    assert "checked" not in checkbox


def test_consent_label_links_to_the_privacy_policy(anon_client: TestClient) -> None:
    page = anon_client.get("/contacto").text
    label = page.split('<label for="contact-privacy"')[1].split("</label>")[0]

    assert "He leído y acepto la" in label
    assert '<a href="/privacidad" target="_blank" rel="noopener">política de privacidad</a>' in label


def test_consent_comes_right_before_the_send_button(anon_client: TestClient) -> None:
    form = anon_client.get("/contacto").text.split('<form id="contact-form"')[1].split("</form>")[0]

    assert form.index('id="contact-message"') < form.index('id="contact-privacy"') < form.index('id="contact-submit"')


@pytest.mark.parametrize("value", [None, "", "no", "false", "0"])
def test_message_is_rejected_without_explicit_consent(anon_client: TestClient, value: str | None) -> None:
    data = {key: val for key, val in VALID.items() if key != "privacy_accepted"}
    if value is not None:
        data["privacy_accepted"] = value

    response = anon_client.post("/contacto", data=data, headers=BROWSER)

    assert response.status_code == 422
    assert field_error(response.text, "privacy_accepted") == "Debes aceptar la política de privacidad para enviar el mensaje."
    assert "checked" not in consent_checkbox(response.text)
    assert DEMO_RESULT not in response.text


def test_consent_given_by_the_user_is_kept_after_another_error(anon_client: TestClient) -> None:
    response = post(anon_client, email="no-es-un-email")

    assert response.status_code == 422
    assert "checked" in consent_checkbox(response.text)  # the user ticked it: not pre-ticked by us


def test_form_is_reset_to_unticked_after_a_successful_submission(anon_client: TestClient) -> None:
    response = post(anon_client)

    assert DEMO_RESULT in response.text
    assert "checked" not in consent_checkbox(response.text)


def test_schema_requires_explicit_consent() -> None:
    data = {key: val for key, val in VALID.items() if key != "privacy_accepted"}

    for consent in (False, "no"):
        with pytest.raises(ValidationError):
            ContactMessage.model_validate({**data, "privacy_accepted": consent})
    with pytest.raises(ValidationError):
        ContactMessage.model_validate(data)
    assert ContactMessage.model_validate({**data, "privacy_accepted": True}).privacy_accepted is True


def test_first_layer_information_is_right_below_the_form(anon_client: TestClient) -> None:
    page = anon_client.get("/contacto").text
    panel = page.split('<section class="contact-form-panel"')[1]

    assert panel.index("</form>") < panel.index('id="contact-gdpr"')
    gdpr = panel.split('id="contact-gdpr"')[1].split("</section>")[0]
    assert "Información básica sobre protección de datos" in gdpr
    for heading in ("Responsable", "Finalidad", "Legitimación", "Destinatarios", "Derechos", "Información adicional"):
        assert f"<dt>{heading}</dt>" in gdpr
    assert "Responder a tu consulta o solicitud de soporte." in gdpr
    assert "Tu consentimiento, que das al marcar la casilla de aceptación." in gdpr
    assert '<a href="/privacidad" target="_blank" rel="noopener">Consulta la política de privacidad</a>' in gdpr
    assert "los datos que escribas no se envían ni se guardan" in gdpr


def test_first_layer_invents_no_legal_data(anon_client: TestClient) -> None:
    gdpr = anon_client.get("/contacto").text.split('id="contact-gdpr"')[1].split("</section>")[0]

    # Controller and recipients are not defined yet: they must not be invented.
    assert gdpr.count("<dd>Pendiente de completar.</dd>") == 2
    for invented in ("CIF", "NIF", "S.L.", "S.A.", "@", "Calle", "+34", "dpo"):
        assert invented not in gdpr, invented
