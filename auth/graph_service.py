"""
graph_service.py
Corresponds to Java: GraphService (com.axaxl.sumcomp.server.authorization.GraphService)

Two Graph API client identities are used:
  1. graphAppClient  -> ClientSecretCredential (SPN)  -> queries global /groups
  2. temporary graphClient -> user access token        -> queries /me/memberOf

Note: /me/memberOf does not support server-side $filter,
      so the Java code filters by prefix on the client side. Python matches this behavior.
"""
import logging

import httpx
from azure.identity import ClientSecretCredential
from cachetools import TTLCache

from .exceptions import AdGroupMembershipException, PermissionMappingException
from .helper import transform_group_keys
from .settings import ADProperties

log = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"


class GraphService:
    def __init__(self, settings: ADProperties) -> None:
        self.settings = settings

        # Corresponds to Java: graphAppClient using SPN identity -> queries global groups
        self._credential = ClientSecretCredential(
            tenant_id=settings.tenant,
            client_id=settings.client_id,
            client_secret=settings.client_secret,
        )

        # Cache for getGroupIdNameMapping results (5-minute TTL)
        # Java has no caching, but this call is expensive so caching is recommended
        self._mapping_cache: TTLCache = TTLCache(maxsize=1, ttl=300)

    # ------------------------------------------------------------------
    # Internal: obtain SPN access token
    # ------------------------------------------------------------------
    def _app_token(self) -> str:
        return self._credential.get_token(GRAPH_SCOPE).token

    # ------------------------------------------------------------------
    # Corresponds to Java: getUserGroupMembership(String accessToken)
    # Uses the user's own token -> GET /me/memberOf
    # Returns list of AD group IDs matching the configured prefix
    # ------------------------------------------------------------------
    async def get_user_group_membership(
        self, access_token: str
    ) -> list[str]:
        prefix = self.settings.group_prefix
        headers = {
            "Authorization": f"Bearer {access_token}",
            # Java: new HeaderOption("ConsistencyLevel", "eventual")
            "ConsistencyLevel": "eventual",
        }
        url = (
            f"{GRAPH_BASE}/me/memberOf"
            "?$select=id,displayName,@odata.type"
            "&$top=999"
        )
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            return [
                obj["id"]
                for obj in data.get("value", [])
                # Corresponds to Java: directoryObject instanceof Group
                if obj.get("@odata.type") == "#microsoft.graph.group"
                # Corresponds to Java: .filter(startswith(displayName, '%s'))
                and obj.get("displayName", "").startswith(prefix)
            ]

        except Exception as exc:
            log.error(
                "Exception while trying to get user group membership",
                exc_info=exc,
            )
            raise AdGroupMembershipException(
                "Failed to get user group membership"
            ) from exc

    # ------------------------------------------------------------------
    # Corresponds to Java: getGroupIdNameMapping()
    # Uses SPN token -> GET /groups
    # Returns {groupId: groupDisplayName} for groups defined in config only
    # ------------------------------------------------------------------
    def get_group_id_name_mapping(self) -> dict[str, str]:
        if "mapping" in self._mapping_cache:
            return self._mapping_cache["mapping"]

        # Corresponds to Java: Helper.transformGroupKeys(ADproperties.getGroups())
        auth_groups = transform_group_keys(self.settings.groups)
        prefix = self.settings.group_prefix

        headers = {
            "Authorization": f"Bearer {self._app_token()}",
            "ConsistencyLevel": "eventual",
        }
        url = (
            f"{GRAPH_BASE}/groups"
            f"?$filter=startswith(displayName,'{prefix}')"
            "&$select=id,displayName"
            "&$count=true"
            "&$top=999"
        )
        try:
            with httpx.Client() as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            mapping = {
                obj["id"]: obj["displayName"]
                for obj in data.get("value", [])
                # Corresponds to Java: authGroups.containsKey(group.displayName)
                if obj.get("displayName") in auth_groups
            }
            self._mapping_cache["mapping"] = mapping
            log.info(
                "Group id->name mapping refreshed, %d groups loaded",
                len(mapping),
            )
            return mapping

        except Exception as exc:
            log.error("Failed to get group id name mapping", exc_info=exc)
            raise PermissionMappingException(
                "Failed to get group id name mapping"
            ) from exc
