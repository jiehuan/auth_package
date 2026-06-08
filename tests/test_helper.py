"""
test_helper.py
Python port of Java HelperTest.testTransformGroupKeys()
"""
import pytest
from auth.helper import (
    extract_user_id_from_document_path,
    get_claim_by_key,
    get_filename_from_path,
    transform_group_keys,
)


def test_transform_group_keys():
    """Directly mirrors Java HelperTest.testTransformGroupKeys()"""
    input_groups = {
        "R02_UG_Axiom_SDLC_AxiomAI-SummComp_Developer_SPI": ["Developer"],
        "AnotherGroup": ["Admin"],
    }

    result = transform_group_keys(input_groups)

    # Java: assertEquals(2, result.size())
    assert len(result) == 2

    # Java: assertTrue(result.containsKey("R02_UG_Axiom_SDLC_AxiomAI-Summ&Comp_Developer_SPI"))
    assert "R02_UG_Axiom_SDLC_AxiomAI-Summ&Comp_Developer_SPI" in result

    # Java: assertEquals(List.of("Developer"), result.get(...))
    assert result["R02_UG_Axiom_SDLC_AxiomAI-Summ&Comp_Developer_SPI"] == ["Developer"]

    # Java: assertTrue(result.containsKey("AnotherGroup"))
    assert "AnotherGroup" in result

    # Java: assertEquals(List.of("Admin"), result.get("AnotherGroup"))
    assert result["AnotherGroup"] == ["Admin"]


def test_transform_group_keys_no_replacement_needed():
    """Groups without 'SummComp' are returned unchanged."""
    input_groups = {"NormalGroup": ["read", "write"]}
    result = transform_group_keys(input_groups)
    assert result == {"NormalGroup": ["read", "write"]}


def test_transform_group_keys_empty():
    assert transform_group_keys({}) == {}


def test_get_claim_by_key():
    claims = {"email": "user@example.com", "sub": "12345", "count": 3}
    assert get_claim_by_key(claims, "email") == "user@example.com"
    assert get_claim_by_key(claims, "count") == "3"
    assert get_claim_by_key(claims, "missing") is None


def test_get_filename_from_path():
    assert get_filename_from_path("/some/path/to/file.pdf") == "file.pdf"
    assert get_filename_from_path("file.pdf") == "file.pdf"


def test_extract_user_id_from_document_path():
    assert extract_user_id_from_document_path("user123/sub456/doc.pdf") == "user123"
    assert extract_user_id_from_document_path(None) is None
    assert extract_user_id_from_document_path("") is None
