from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport
from ..utils import drop_none


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
                'Take': take,
                'Skip': skip,
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
            version_id: UUID,
            naming_pattern_id: UUID = None
    ) -> UUID:
        """
        Creates a new File item with a version and attaches it to the item. Returns the id of the created item.
        Required scopes: docs:item:create
        :param name: Name of item to create
        :param folder_id: UUID of the folder
        :param version_id: UUID of the version
        :param naming_pattern_id: Identifier of the naming pattern to apply
        :return: UUID of the created item
        """
        payload = {'name': name, 'folderId': folder_id, 'versionId': version_id}
        if naming_pattern_id is not None:
            payload['namingPatternId'] = naming_pattern_id
        return await self._transport.request(method='PUT', path='/items/file', json=payload)

    @extract_key_from_response(key='data')
    async def create_link(
            self,
            name: str,
            folder_id: UUID,
            link: str
    ) -> UUID:
        """
        Creates a new Link item. Returns the id of the created item.
        Required scopes: docs:item:create
        :param name: Name of the link item
        :param folder_id: UUID of the folder
        :param link: Target URL of the link item
        :return: UUID of the created link.
        """
        return await self._transport.request(
            method='PUT',
            path='/items/link',
            json={
                'name': name,
                'folderId': folder_id,
                'link': link
            }
        )

    async def get_link(
            self,
            item_id: UUID,
            version_id: UUID,
            file_name: str = None,
            url_ttl_sec_override: int = None
    ) -> dict:
        """
        Required scopes: docs:item:read.
        :param item_id: Item UUID
        :param version_id: Version UUID
        :param file_name: ...
        :param url_ttl_sec_override: Download url ttl in seconds. Can be set only for custom storages
        :return: Returns S3 download link
        """
        params = {
            'itemId': item_id,
            'versionId': version_id
        }
        if file_name:
            params['fileName'] = file_name
        if url_ttl_sec_override is not None:
            params['urlTtlSecOverride'] = url_ttl_sec_override
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

    async def search(
            self,
            folder_id: UUID,
            name: str = None,
            suffixes: list[str] = None,
            take: int = 100,
            skip: int = 0,
            *,
            ids: list[UUID] = None,
            added_by: UUID = None,
            modified_by: UUID = None,
            added_from: str = None,
            added_to: str = None,
            modified_from: str = None,
            modified_to: str = None
    ) -> list[dict]:
        """
        Returns a folder`s nested items search result.
        Required scopes: docs:item:list
        :param folder_id: Identifier for search within the folder and its subfolders
        :param name: Filter by item name
        :param suffixes: Filter by file suffixes (e.g., extensions)
        :param ids: Filter by item identifiers
        :param added_from: ISO date-time; the other *_from / *_to bounds work the same way
        """
        return await self._transport.request(
            method='POST',
            path='/items/search',
            params={'Take': take, 'Skip': skip},
            json=drop_none(
                folderId=folder_id,
                name=name,
                suffixes=suffixes,
                ids=ids,
                addedBy=added_by,
                modifiedBy=modified_by,
                addedFrom=added_from,
                addedTo=added_to,
                modifiedFrom=modified_from,
                modifiedTo=modified_to
            )
        )

    async def get_item_version(self, id: UUID) -> dict:
        """
        Retrieves a specific item version by its unique identifier.
        Required scopes: docs:item:read
        """
        return await self._transport.request(method='GET', path='/items/item-version', params={'id': id})

    async def update(self, item_id: UUID, name: str = None, link: str = None) -> None:
        """
        Updates an existing item.
        Required scopes: docs:item:update
        :param link: New link, only applicable for Link items
        """
        payload = {'id': item_id}
        if name is not None:
            payload['name'] = name
        if link is not None:
            payload['link'] = link
        return await self._transport.request(method='PATCH', path='/items/update', json=payload)

    async def update_version(self, item_version_id: UUID, comment: str = None) -> None:
        """
        Updates an existing item version.
        Required scopes: docs:version:update
        """
        payload = {'id': item_version_id}
        if comment is not None:
            payload['comment'] = comment
        return await self._transport.request(method='PATCH', path='/items/versions/update', json=payload)

    async def delete(self, item_id: UUID) -> None:
        """
        Moves an item to the trash.
        Required scopes: docs:item:delete
        """
        return await self._transport.request(method='DELETE', path=f'/items/{item_id}')

    async def move(
            self,
            item_id: UUID,
            new_folder_id: UUID,
            new_name: str = None,
            naming_pattern_id: UUID = None
    ) -> None:
        """
        Moves an item to another folder.
        Required scopes: docs:item:update
        """
        return await self._transport.request(
            method='PATCH',
            path='/items/move',
            json=drop_none(id=item_id, newFolderId=new_folder_id, newName=new_name, namingPatternId=naming_pattern_id)
        )
