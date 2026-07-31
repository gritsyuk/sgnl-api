from ..transport import Transport


class IssueAccesses:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict) -> list[dict]:
        """
        Returns a list of issue access rules.
        Required scopes: docs:issue:list
        :param filter: IssueAccessesFind payload, e.g. {"issueTypeIds": [...]}
        """
        return await self._transport.request(method='POST', path='/issues/accesses', json=filter)
