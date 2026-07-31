from ..transport import Transport


class Storage:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, is_system: bool = None) -> list[dict]:
        """
        Returns a list of document storages matching the given filter.
        Required scopes: docs:storage:list
        """
        payload = {}
        if is_system is not None:
            payload['isSystem'] = is_system
        return await self._transport.request(method='POST', path='/storages', json=payload)
