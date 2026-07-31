from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class IssueComment:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns a list of comments for issues in the specified project.
        Required scopes: docs:issue:list
        :param filter: IssueCommentFind payload, e.g. {"projectId": ..., "issueIds": [...]}
        """
        return await self._transport.request(
            method='POST', path='/issues/comments', params={'Take': take, 'Skip': skip}, json=filter
        )

    @extract_key_from_response(key='data')
    async def create(self, issue_id: UUID, text: str) -> UUID:
        """
        Creates a new comment for the specified issue.
        Required scopes: docs:issue:create
        """
        return await self._transport.request(
            method='PUT', path='/issues/comments', json={'issueId': issue_id, 'text': text}
        )

    @extract_key_from_response(key='data')
    async def count(self, filter: dict) -> int:
        """
        Returns the total number of comments matching the given filter.
        Required scopes: docs:issue:list
        """
        return await self._transport.request(method='POST', path='/issues/comments/count', json=filter)
