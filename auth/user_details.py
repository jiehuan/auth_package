"""
user_details.py
Corresponds to Java: AuthorizedUserDetailsService
         (com.axaxl.sumcomp.server.authorization.AuthorizedUserDetailsService)

Two-layer permission mapping:
  groupId -> groupName  (from Graph API)
  groupName -> permissions (from config file)
"""
import logging

from .graph_service import GraphService
from .helper import transform_group_keys
from .settings import ADProperties

log = logging.getLogger(__name__)


class AuthorizedUserDetailsService:
    def __init__(
        self,
        graph_service: GraphService,
        settings: ADProperties,
    ) -> None:
        self.graph = graph_service
        self.settings = settings

    async def get_user_permissions(self, access_token: str) -> set[str]:
        """
        Corresponds to Java: getUserPermissions(String accessToken)

        Steps:
        1. Use user token -> Graph API -> fetch AD group ID list
        2. group ID -> group name (from SPN-level global mapping)
        3. group name -> permissions (from config file)
        4. Return union of all permissions as a Set
        """
        # Step 1: fetch group IDs the user belongs to
        group_ids = await self.graph.get_user_group_membership(access_token)

        # Step 2: groupId -> groupName mapping
        id_name_map = self.graph.get_group_id_name_mapping()

        # Step 3: groupName -> permissions mapping (with '&' restoration)
        name_perm_map = transform_group_keys(self.settings.groups)

        # Step 4: mirrors Java stream pipeline:
        # groupIds.stream()
        #   .map(groupIdNameMap::get)
        #   .filter(Objects::nonNull)
        #   .map(groupNamePermissionMapping::get)
        #   .filter(Objects::nonNull)
        #   .flatMap(Collection::stream)
        #   .collect(Collectors.toSet())
        permissions: set[str] = set()
        for gid in group_ids:
            group_name = id_name_map.get(gid)
            if group_name:
                perms = name_perm_map.get(group_name, [])
                permissions.update(perms)

        log.info(
            "User belongs to AD groups: %s, resolved permissions: %s",
            [id_name_map.get(gid) for gid in group_ids if id_name_map.get(gid)],
            permissions,
        )
        return permissions
