from ..transport import Transport


class UserLog:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict = None) -> list[dict]:
        """
        Returns user logs matching the given filter.
        Required scopes: logs:user:list
        :param filter: UserLogFind payload, e.g. {"projectIds": [...], "from": "...", "take": 100}
        """
        return await self._transport.request(method='POST', path='/user-logs', json=filter or {})
