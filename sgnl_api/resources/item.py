from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class Item:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(
            self,
            folder_id: UUID,
            deleted: bool = False,
            take: int = 100,
            skip: int = 0
    ) -> list[dict]:
        """
        Required scopes: docs:item:list
        :param folder_id: UUID of the folder
        :param deleted: If true, returns deleted items
        :param take: Number of items to return
        :param skip: Number of items to skip
        :return: Returns a folder`s not nested items list.
        """
        return await self._transport.request(
            method='GET',
            path='/items',
            params={
                'folderId': folder_id,
                'take': take,
                'skip': skip,
                'deleted': deleted
            }
        )

    @extract_key_from_response(key="data")
    async def count(
            self,
            folder_id: UUID,
            deleted: bool = False
    ) -> int:
        """
        Required scopes: docs:item:list
        :param folder_id: UUID of the folder
        :param deleted: If true, returns deleted items
        :return: Returns a count items in folder`s not nested items list.
        """
        return await self._transport.request(
            method='GET',
            path='/items/count',
            params={
                'folderId': folder_id,
                'deleted': deleted
            }
        )

    @extract_key_from_response(key='data')
    async def create_file(
            self,
            name: str,
            folder_id: UUID,
            version_id: UUID
    ) -> UUID:
        """
        Creates a new File item with a version and attaches it to the item. Returns the id of the created item.
        Required scopes: docs:item:create
        :param name: Name of item to create
        :param folder_id: UUID of the folder
        :param version_id: UUID of the version
        :return: UUID of the created item
        """
        return await self._transport.request(
            method='PUT',
            path='/items/file',
            json={
                'name': name,
                'folderId': folder_id,
                'versionId': version_id
            }
        )

    @extract_key_from_response(key='data')
    async def create_link(
            self,
            name: str,
            folder_id: UUID,
            version_id: UUID
    ) -> UUID:
        """
        Creates a new Link item. Returns the id of the created item.
        Required scopes: docs:item:create
        :param name:
        :param folder_id:
        :param version_id:
        :return: UUID of the created link.
        """
        return await self._transport.request(
            method='PUT',
            path='/items/link',
            json={
                'name': name,
                'folderId': folder_id,
                'versionId': version_id
            }
        )

    async def get_link(
            self,
            item_id: UUID,
            version_id: UUID,
            file_name: str = None
    ) -> dict:
        """
        Required scopes: docs:item:read.
        :param item_id: Item UUID
        :param version_id: Version UUID
        :param file_name: ...
        :return: Returns S3 download link
        """
        params = {
            'itemId': item_id,
            'versionId': version_id
        }
        if file_name:
            params['fileName'] = file_name
        return await self._transport.request(
            method='GET',
            path='/items/download',
            params=params
        )

    async def add_version(
            self,
            item_id: UUID,
            version_id: UUID
    ) -> None:
        """
        Attaches a version to an existing item.
        Required scopes: docs:version:create
        :param item_id:
        :param version_id:
        :return: None
        """
        return await self._transport.request(
            method='PUT',
            path='/items/versions',
            json={
                'itemId': item_id,
                'versionId': version_id
            }
        )
