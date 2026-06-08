"""
exceptions.py
Corresponds to Java custom exceptions:
  - AdGroupMembershipException
  - PermissionMappingException
"""


class AdGroupMembershipException(Exception):
    """Raised when the Graph API call to /me/memberOf fails."""
    pass


class PermissionMappingException(Exception):
    """Raised when the Graph API call to /groups fails or permission mapping errors occur."""
    pass
