"""
test_user_details.py
Unit tests for AuthorizedUserDetailsService with mocked Graph API calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from auth.user_details import AuthorizedUserDetailsService
from auth.settings import ADProperties


@pytest.fixture
def settings():
    return ADProperties(
        tenant="test-tenant",
        client_id="test-client-id",
        client_secret="test-secret",
        group_prefix="R02_",
        groups={
            # Config stores "SummComp"; transformGroupKeys restores it to "Summ&Comp"
            "R02_UG_Axiom_SDLC_AxiomAI-SummComp_Developer_SPI": ["read", "write"],
            "R02_UG_Admin": ["read", "write", "delete"],
        },
    )


@pytest.fixture
def graph_service():
    return MagicMock()


@pytest.fixture
def svc(graph_service, settings):
    return AuthorizedUserDetailsService(
        graph_service=graph_service,
        settings=settings,
    )


@pytest.mark.asyncio
async def test_get_user_permissions_normal(svc, graph_service):
    """User belongs to Developer group -> receives read + write permissions."""
    group_id = "group-uuid-001"

    graph_service.get_user_group_membership = AsyncMock(return_value=[group_id])
    graph_service.get_group_id_name_mapping = MagicMock(
        return_value={group_id: "R02_UG_Axiom_SDLC_AxiomAI-Summ&Comp_Developer_SPI"}
    )

    perms = await svc.get_user_permissions("fake-token")
    assert perms == {"read", "write"}


@pytest.mark.asyncio
async def test_get_user_permissions_no_matching_group(svc, graph_service):
    """User's group is not in config -> empty permission set."""
    graph_service.get_user_group_membership = AsyncMock(return_value=["unknown-group-id"])
    graph_service.get_group_id_name_mapping = MagicMock(
        return_value={"unknown-group-id": "SomeOtherGroup"}
    )

    perms = await svc.get_user_permissions("fake-token")
    assert perms == set()


@pytest.mark.asyncio
async def test_get_user_permissions_multiple_groups(svc, graph_service):
    """User belongs to multiple groups -> permissions are merged."""
    graph_service.get_user_group_membership = AsyncMock(
        return_value=["id-dev", "id-admin"]
    )
    graph_service.get_group_id_name_mapping = MagicMock(
        return_value={
            "id-dev": "R02_UG_Axiom_SDLC_AxiomAI-Summ&Comp_Developer_SPI",
            "id-admin": "R02_UG_Admin",
        }
    )

    perms = await svc.get_user_permissions("fake-token")
    assert perms == {"read", "write", "delete"}


@pytest.mark.asyncio
async def test_get_user_permissions_empty_groups(svc, graph_service):
    """User belongs to no AD groups -> empty permission set."""
    graph_service.get_user_group_membership = AsyncMock(return_value=[])
    graph_service.get_group_id_name_mapping = MagicMock(return_value={})

    perms = await svc.get_user_permissions("fake-token")
    assert perms == set()
