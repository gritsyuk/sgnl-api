from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class Issue:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns a list of issues matching the given filter (with pagination).
        Required scopes: docs:issue:list
        :param filter: IssueFind payload, e.g. {"projectId": ...}
        """
        return await self._transport.request(
            method='POST', path='/issues', params={'Take': take, 'Skip': skip}, json=filter
        )

    async def update(self, items: list[dict]) -> None:
        """
        Updates multiple issues in a batch operation.
        Required scopes: docs:issue:update
        :param items: list of IssueUpdate payloads, each requiring "id" (min 1, max 25 items)
        """
        return await self._transport.request(method='PATCH', path='/issues', json=items)

    @extract_key_from_response(key='data')
    async def count(self, filter: dict) -> int:
        """
        Returns the total number of issues matching the given filter.
        Required scopes: docs:issue:list
        """
        return await self._transport.request(method='POST', path='/issues/count', json=filter)

    async def item_issues_count(
            self,
            project_id: UUID,
            item_ids: list[UUID],
            included_statuses: list[str] = None,
            excluded_statuses: list[str] = None
    ) -> list[dict]:
        """
        Returns the number of issues linked to each of the specified items.
        Required scopes: docs:issue:list
        :param included_statuses: optional set of IssueStatus values to include
        :param excluded_statuses: optional set of IssueStatus values to exclude
        """
        payload = {'projectId': project_id, 'itemIds': item_ids}
        if included_statuses is not None:
            payload['includedStatuses'] = included_statuses
        if excluded_statuses is not None:
            payload['excludedStatuses'] = excluded_statuses
        return await self._transport.request(method='POST', path='/issues/items/counts', json=payload)
