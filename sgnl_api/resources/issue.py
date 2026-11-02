from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport
from ..utils import drop_none


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

    async def create(
            self,
            *,
            project_id: UUID,
            author_id: UUID,
            issue_type_id: UUID,
            name: str,
            status: str,
            responsible: dict,
            observers: list[dict] = None,
            item_version_id: UUID = None,
            description: str = None,
            placement: str = None,
            markup_data: str = None,
            bim_data: str = None,
            elimination_date: str = None
    ) -> UUID:
        """
        Creates a new issue. Returns its id.
        Required scopes: docs:issue:create
        :param status: IssueStatus value, e.g. "Draft", "Open", "InProgress"
        :param responsible: Identity, e.g. {"id": ..., "type": "User"} or {"id": ..., "type": "Role"}
        :param observers: list of Identity (max 200)
        :param elimination_date: ISO date string (YYYY-MM-DD)
        """
        return await self._transport.request(
            method='POST',
            path='/issues/create',
            json=drop_none(
                projectId=project_id,
                authorId=author_id,
                issueTypeId=issue_type_id,
                name=name,
                status=status,
                responsible=responsible,
                observers=observers,
                itemVersionId=item_version_id,
                description=description,
                placement=placement,
                markupData=markup_data,
                bimData=bim_data,
                eliminationDate=elimination_date
            )
        )
