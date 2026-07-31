from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class Folder:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(
            self,
            folder_id: UUID,
            deleted: bool = False
    ) -> list[dict]:
        """
        Required scopes: docs:folder:list
        :param folder_id: UUID of the folder
        :param deleted: If true, returns deleted items
        :return: Returns a list of folder`s children.
        """
        return await self._transport.request(
            method='GET',
            path=f'/folders/{folder_id}/children',
            params={
                'deleted': deleted
            }
        )

    @extract_key_from_response(key='data')
    async def create(
            self,
            parent_id: UUID,
            name: str = 'new folder from api'
    ) -> UUID:
        """
        Creates a new folder.
        Required scopes: docs:folder:create
        :param parent_id: UUID of the parent folder
        :param name: Name of the folder
        :return: UUID of the created folder.
        """
        return await self._transport.request(
            method='PUT',
            path='/folders',
            json={
                'parentId': parent_id,
                'name': name
            }
        )

    async def rename(
            self,
            folder_id: UUID,
            name: str
    ) -> None:
        """
        Updates a folder - rename
        Required scopes: docs:folder:update
        :param folder_id: UUID of the folder
        :param name: New name of the folder
        :return: None
        """
        return await self._transport.request(
            method='PATCH',
            path='/folders',
            json={
                'id': folder_id,
                'name': name
            }
        )
