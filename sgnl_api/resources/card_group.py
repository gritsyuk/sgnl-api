from ..transport import Transport


class CardGroup:
    """Dashboard card groups (the "Group" tag in the API spec)."""

    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns the card groups of a dashboard. Deleted groups, and groups of a deleted dashboard,
        are never returned.
        Required scopes: dash:group:list
        :param filter: GroupFind payload, e.g. {"boardId": ...}
        """
        return await self._transport.request(
            method='POST', path='/boards/groups', params={'Take': take, 'Skip': skip}, json=filter
        )
