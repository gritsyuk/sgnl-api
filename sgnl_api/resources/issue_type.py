from ..transport import Transport


class IssueType:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict) -> list[dict]:
        """
        Returns a list of issue types matching the given filter.
        Required scopes: docs:issue:list
        :param filter: IssueTypeFind payload, e.g. {"projectId": ...}
        """
        return await self._transport.request(method='POST', path='/issues/types', json=filter)
