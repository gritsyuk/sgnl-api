from ..transport import Transport


class Attribute:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict) -> list[dict]:
        """
        Returns a list of attributes matching the given filter.
        Required scopes: docs:attribute:list
        :param filter: AttributeFind payload, e.g. {"projectId": ..., "type": "Structure"|"Issue"}
        """
        return await self._transport.request(method='POST', path='/attributes', json=filter)
