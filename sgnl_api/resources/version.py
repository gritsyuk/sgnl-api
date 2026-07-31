from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class Version:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(
            self,
            item_id: UUID,
            take: int = 100,
            skip: int = 0
    ) -> list[dict]:
        """
        Returns a list of versions of item
        Required scopes: docs:version:list
        :param item_id: Item UUID
        :param take: The number of items to return. Default value is 100. Maximum value is 200.
        :param skip: The number of items to skip. Default value is 0.
        :return: list of versions of item
        """
        return await self._transport.request(
            method='GET',
            path='/versions',
            params={
                'itemId': item_id,
                'Take': take,
                'Skip': skip
            }
        )

    @extract_key_from_response(key="data")
    async def count(
            self,
            item_id: UUID
    ) -> int:
        """
        Returns the count of item`s versions.
        Required scopes: docs:version:list
        :param item_id: Item UUID
        :return: count items
        """
        return await self._transport.request(
            method='GET',
            path='/versions',
            params={
                'itemId': item_id
            }
        )

    @extract_key_from_response(key="data")
    async def create(
            self,
            *,
            object_id: UUID,
            project_id: UUID,
            name: str
    ) -> UUID:
        """
        Creates a new version of an object. Returns the id of the created version.
        Required scopes: docs:version:create
        :param object_id: UUID of the object
        :param project_id: UUID of the project
        :param name: ...
        :return: UUID of the created version
        """
        return await self._transport.request(
            method='POST',
            path='/versions',
            json={
                'objectId': object_id,
                'projectId': project_id,
                'name': name
            }
        )
