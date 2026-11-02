from ..transport import Transport


class Board:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns the dashboards of a project. Deleted dashboards are never returned.
        Required scopes: dash:board:list
        :param filter: BoardFind payload, e.g. {"projectId": ...}
        """
        return await self._transport.request(
            method='POST', path='/boards', params={'Take': take, 'Skip': skip}, json=filter
        )
