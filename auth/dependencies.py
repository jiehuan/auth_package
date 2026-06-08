"""
dependencies.py
FastAPI dependency injection layer

Corresponds to Java:
  - Spring Security OIDC token validation -> fastapi-azure-auth
  - @PreAuthorize / hasAuthority()        -> require_permission()
  - @Profile("!noauth")                   -> NOAUTH env variable

Usage:
  # Protect a route
  @router.get("/report", dependencies=[Depends(require_permission("read"))])
  async def get_report(): ...

  # Or inject permissions into a handler
  @router.get("/me")
  async def get_me(perms: set[str] = Depends(get_user_permissions)): ...
"""
import os
import logging
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer

from .graph_service import GraphService
from .settings import ADProperties
from .user_details import AuthorizedUserDetailsService

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Singletons: settings / graph_service / user_details_service
# lru_cache ensures each is only initialized once
# ------------------------------------------------------------------
@lru_cache
def get_settings() -> ADProperties:
    return ADProperties()


@lru_cache
def get_graph_service() -> GraphService:
    return GraphService(settings=get_settings())


@lru_cache
def get_user_details_service() -> AuthorizedUserDetailsService:
    return AuthorizedUserDetailsService(
        graph_service=get_graph_service(),
        settings=get_settings(),
    )


# ------------------------------------------------------------------
# Lazy initialization of azure_scheme
# Avoids crashing at module load time when env vars are missing (e.g. in tests)
# ------------------------------------------------------------------
_azure_scheme_instance: SingleTenantAzureAuthorizationCodeBearer | None = None


def get_azure_scheme() -> SingleTenantAzureAuthorizationCodeBearer:
    global _azure_scheme_instance
    if _azure_scheme_instance is None:
        s = get_settings()
        _azure_scheme_instance = SingleTenantAzureAuthorizationCodeBearer(
            app_client_id=s.client_id,
            tenant_id=s.tenant,
            scopes={
                f"api://{s.client_id}/user_impersonation": "Access the API",
            },
        )
    return _azure_scheme_instance


# Alias exposed via __init__.py
azure_scheme = get_azure_scheme

# ------------------------------------------------------------------
# No-auth mode (corresponds to Java @Profile("!noauth"))
# Set NOAUTH=true in environment to bypass authentication locally
# ------------------------------------------------------------------
NOAUTH_MODE = os.getenv("NOAUTH", "false").lower() == "true"

if NOAUTH_MODE:
    log.warning("NOAUTH mode enabled — authentication is DISABLED")


async def get_user_permissions(
    svc: AuthorizedUserDetailsService = Depends(get_user_details_service),
    token=Depends(get_azure_scheme),
) -> set[str]:
    """
    Validates the token then resolves the current user's permission set.
    Corresponds to Java: userService Bean + AuthorizedUserDetailsService
    """
    if NOAUTH_MODE:
        # In no-auth mode, grant all configured permissions
        all_perms: set[str] = set()
        for perms in svc.settings.groups.values():
            all_perms.update(perms)
        return all_perms

    raw_token: str = token.access_token
    return await svc.get_user_permissions(raw_token)


# ------------------------------------------------------------------
# Route permission guards
# Corresponds to Java: @PreAuthorize("hasAuthority('read')")
# ------------------------------------------------------------------
def require_permission(permission: str):
    """
    Usage:
      @router.get("/data", dependencies=[Depends(require_permission("read"))])
    """
    async def _checker(
        perms: set[str] = Depends(get_user_permissions),
    ) -> None:
        if permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: '{permission}'",
            )
    return _checker


def require_any_permission(*permissions: str):
    """
    Passes if the user holds at least one of the listed permissions.

    Usage:
      @router.get("/data", dependencies=[Depends(require_any_permission("read", "admin"))])
    """
    async def _checker(
        perms: set[str] = Depends(get_user_permissions),
    ) -> None:
        if not any(p in perms for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing one of required permissions: {list(permissions)}",
            )
    return _checker
