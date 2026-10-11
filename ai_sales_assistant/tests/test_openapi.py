from typing import Any

import pytest

from app.main import app

EXPECTED_OPERATIONS = {
    ("get", "/"): {"200", "500"},
    ("get", "/health"): {"200", "500", "503"},
    ("post", "/api/v1/auth/register"): {"201", "400", "403", "409", "422", "500"},
    ("post", "/api/v1/auth/login"): {"200", "400", "401", "403", "422", "500"},
    ("post", "/api/v1/auth/logout"): {"204", "401", "403", "500"},
    ("get", "/api/v1/auth/me"): {"200", "401", "500"},
    ("post", "/api/v1/auth/change-password"): {"204", "400", "401", "403", "422", "500"},
    ("post", "/api/v1/auth/guest"): {"201", "403", "500"},
    ("post", "/api/v1/auth/forgot-password"): {"202", "400", "403", "422", "500"},
    ("post", "/api/v1/auth/reset-password"): {"204", "400", "403", "422", "500"},
    ("post", "/api/v1/generate"): {"201", "400", "401", "403", "422", "500", "502", "503"},
    ("get", "/api/v1/generations"): {"200", "401", "422", "500"},
    ("get", "/api/v1/generations/{generation_id}"): {"200", "401", "404", "422", "500"},
    ("put", "/api/v1/generations/{generation_id}"): {"200", "400", "401", "403", "404", "422", "500", "502", "503"},
    ("get", "/api/v1/pricing/discount"): {"200", "401", "422", "500"},
    ("delete", "/api/v1/generations/{generation_id}"): {"204", "401", "403", "404", "422", "500"},
}


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    return app.openapi()


def operations(spec: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(method, path): op for path, ops in spec["paths"].items() for method, op in ops.items()}


def test_only_expected_operations_are_exposed(spec: dict[str, Any]) -> None:
    assert set(operations(spec)) == set(EXPECTED_OPERATIONS)


@pytest.mark.parametrize("operation", list(EXPECTED_OPERATIONS))
def test_operation_is_fully_documented(spec: dict[str, Any], operation: tuple[str, str]) -> None:
    op = operations(spec)[operation]

    assert op["summary"]
    assert op["description"]
    assert set(op["responses"]) == EXPECTED_OPERATIONS[operation]
    for code, response in op["responses"].items():
        assert response["description"] != "Successful Response", code
        if code.startswith(("4", "5")):
            assert "example" in response["content"]["application/json"], code


def test_schemas_provide_examples(spec: dict[str, Any]) -> None:
    schemas = spec["components"]["schemas"]

    assert schemas["GenerationRead"]["examples"]
    assert schemas["GenerationList"]["examples"]
    assert all("examples" in field for field in schemas["GenerationCreate"]["properties"].values())
    assert all("description" in field for field in schemas["GenerationCreate"]["properties"].values())


def test_tags_are_described(spec: dict[str, Any]) -> None:
    assert {tag["name"] for tag in spec["tags"]} == {"System", "Authentication", "Generations", "Pricing"}
