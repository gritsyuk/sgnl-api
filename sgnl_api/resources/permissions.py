from uuid import UUID

from ..transport import Transport


class Permissions:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def upsert_batch(self, folder_id: UUID, items: list[dict]) -> None:
        """
        Creates or updates user and role permissions for a specific folder.
        Required scopes: docs:permissions:update
        :param items: list of PermissionUpsertBatchItem payloads,
            e.g. [{"sourceId": ..., "sourceType": "User", "read": True}]
        """
        return await self._transport.request(
            method='POST', path='/permissions/folders/upsert', json={'folderId': folder_id, 'items': items}
        )

    async def get_tree(self, project_id: UUID) -> dict:
        """
        Returns a tree structure of project folders with their associated permissions.
        Required scopes: docs:permissions:read
        """
        return await self._transport.request(
            method='GET', path='/permissions/tree', params={'projectId': project_id}
        )

    async def delete(self, permission_id: UUID) -> None:
        """
        Deletes a specific permission.
        Required scopes: docs:permissions:delete
        """
        return await self._transport.request(method='DELETE', path=f'/permissions/{permission_id}')
