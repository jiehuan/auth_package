"""
auth package
Azure AD authentication and permission control, migrated from Java Spring Boot to FastAPI.

Main exports:
  - require_permission    Route permission guard
  - get_user_permissions  Resolves the current user's permission set
  - azure_scheme          FastAPI OAuth2 scheme (enables Swagger UI login)
"""
from .dependencies import (
    azure_scheme,
    get_user_permissions,
    require_any_permission,
    require_permission,
)
from .exceptions import AdGroupMembershipException, PermissionMappingException
from .settings import ADProperties

__all__ = [
    "azure_scheme",
    "get_user_permissions",
    "require_permission",
    "require_any_permission",
    "ADProperties",
    "AdGroupMembershipException",
    "PermissionMappingException",
]
