from ..transport import Transport


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
