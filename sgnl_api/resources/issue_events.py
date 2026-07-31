from ..decorators import extract_key_from_response
from ..transport import Transport


class IssueEvents:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns a list of issue events matching the given filter (with pagination).
        Required scopes: docs:issue:list
        :param filter: IssueEventFind payload, e.g. {"issueId": ...}
        """
        return await self._transport.request(
            method='POST', path='/issues/events', params={'Take': take, 'Skip': skip}, json=filter
        )

    @extract_key_from_response(key='data')
    async def count(self, filter: dict) -> int:
        """
        Returns the total number of issue events matching the given filter.
        Required scopes: docs:issue:list
        """
        return await self._transport.request(method='POST', path='/issues/events/count', json=filter)
