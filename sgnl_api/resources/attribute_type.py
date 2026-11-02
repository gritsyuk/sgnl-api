from uuid import UUID

from ..transport import Transport
from ..utils import drop_none


class AttributeType:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict) -> list[dict]:
        """
        Returns a list of attribute types matching the given filter.
        Required scopes: docs:attribute:list
        :param filter: AttributeTypeFind payload, e.g. {"projectId": ...}
        """
        return await self._transport.request(method='POST', path='/attributes/types', json=filter)

    async def create(
            self,
            *,
            project_id: UUID,
            type: str,
            name: str,
            order: int,
            is_required: bool,
            data_type: str = None,
            list_items: list[dict] = None
    ) -> UUID:
        """
        Creates a new attribute type. Returns its id.
        Required scopes: docs:attribute:create
        :param type: AttributeTypeInfo value: "Text", "Bool", "Date" or "List"
        :param data_type: AllowedAttributeDataType value: "Item" or "Folder"
        :param list_items: values for a List type, e.g. [{"name": "A", "position": 1}] (max 50)
        """
        return await self._transport.request(
            method='POST',
            path='/attributes/types/create',
            json=drop_none(
                type=type,
                projectId=project_id,
                name=name,
                order=order,
                isRequired=is_required,
                dataType=data_type,
                list=list_items
            )
        )

    async def update(self, project_id: UUID, data: list[dict]) -> None:
        """
        Updates existing attribute types.
        Required scopes: docs:attribute:update
        :param data: list of AttributeTypeUpdate payloads, each requiring "id" (max 50),
            e.g. [{"id": ..., "name": "New name", "deleted": False}]
        """
        return await self._transport.request(
            method='PATCH', path='/attributes/types', json={'projectId': project_id, 'data': data}
        )
