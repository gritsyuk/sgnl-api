from ..transport import Transport


class AttributeValue:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def list_issues(self, filter: dict) -> list[dict]:
        """
        Returns a list of issues attributes values matching the given filter.
        Required scopes: docs:attribute:list
        :param filter: IssueAttributeValueFind payload, e.g. {"projectId": ..., "issueIds": [...]}
        """
        return await self._transport.request(method='POST', path='/attributes/values/issues', json=filter)

    async def list_items(self, filter: dict) -> list[dict]:
        """
        Returns a list of items attributes values matching the given filter.
        Required scopes: docs:attribute:list
        :param filter: ItemAttributeValueFind payload, e.g. {"projectId": ..., "itemIds": [...]}
        """
        return await self._transport.request(method='POST', path='/attributes/values/items', json=filter)

    async def list_folders(self, filter: dict) -> list[dict]:
        """
        Returns a list of folders attributes values matching the given filter.
        Required scopes: docs:attribute:list
        :param filter: FolderAttributeValueFind payload, e.g. {"projectId": ..., "folderIds": [...]}
        """
        return await self._transport.request(method='POST', path='/attributes/values/folders', json=filter)

    async def set(self, values: dict) -> None:
        """
        Sets attribute values for the specified entity.
        Required scopes: docs:attribute:update
        :param values: AttributeValuesSet payload, e.g. {"type": "Item", "itemId": ..., "values": [...]}
        """
        return await self._transport.request(method='POST', path='/attributes/values/set', json=values)
