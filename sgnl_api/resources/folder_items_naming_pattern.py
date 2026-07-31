from uuid import UUID

from ..transport import Transport


class FolderItemsNamingPattern:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def find(self, folder_id: UUID) -> dict:
        """
        Returns folder's naming patterns for files.
        Required scopes: docs:item:create
        """
        return await self._transport.request(
            method='GET', path='/naming-patterns/folder-items/find', params={'folderId': folder_id}
        )
