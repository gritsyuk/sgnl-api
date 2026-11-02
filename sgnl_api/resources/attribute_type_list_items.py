from uuid import UUID

from ..transport import Transport


class AttributeTypeListItems:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def create(self, attribute_type_id: UUID, items: list[dict]) -> None:
        """
        Creates items for a list attribute type.
        Required scopes: docs:attribute:create
        :param items: e.g. [{"name": "Option A", "position": 1}] (max 50)
        """
        return await self._transport.request(
            method='POST',
            path='/attributes/types/list/items/create',
            json={'attributeTypeId': attribute_type_id, 'items': items}
        )

    async def update(self, attribute_type_id: UUID, items: list[dict]) -> None:
        """
        Updates items for a list attribute type.
        Required scopes: docs:attribute:update
        :param items: list of AttributeTypeListItemUpdate payloads, each requiring "id" (max 50),
            e.g. [{"id": ..., "name": "Renamed", "position": 2, "deleted": False}]
        """
        return await self._transport.request(
            method='PATCH',
            path='/attributes/types/list/items',
            json={'attributeTypeId': attribute_type_id, 'items': items}
        )
