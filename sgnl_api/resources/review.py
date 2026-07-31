from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class Review:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(
            self,
            find: dict,
            order: str = None,
            is_order_asc: bool = None,
            take: int = 20,
            skip: int = 0
    ) -> list[dict]:
        """
        Retrieves a list of reviews for the specified project.
        Required scopes: docs:review:list
        :param find: ReviewFind payload, e.g. {"projectId": ...}
        :param order: ReviewFindOrder value, e.g. "Number", "Cipher", "Name", "PlanDate"
        """
        payload = {'find': find}
        if order is not None:
            payload['order'] = order
        if is_order_asc is not None:
            payload['isOrderAsc'] = is_order_asc
        return await self._transport.request(
            method='POST', path='/reviews', params={'Take': take, 'Skip': skip}, json=payload
        )

    async def update(self, review: dict) -> None:
        """
        Updates review basic information.
        Required scopes: docs:review:update
        :param review: ReviewUpdate payload, requires "id"
        """
        return await self._transport.request(method='PATCH', path='/reviews', json=review)

    @extract_key_from_response(key='data')
    async def count(self, filter: dict) -> int:
        """
        Retrieves the total number of reviews matching the specified filter.
        Required scopes: docs:review:list
        """
        return await self._transport.request(method='POST', path='/reviews/count', json=filter)

    async def get_versions(self, review_version_ids: list[UUID]) -> list[dict]:
        """
        Returns review versions by the specified identifiers.
        Required scopes: docs:review:list
        """
        return await self._transport.request(
            method='POST', path='/reviews/versions', json={'reviewVersionIds': review_version_ids}
        )

    async def find_item_version_ids_by_review_version_ids(self, review_version_ids: list[UUID]) -> dict:
        """
        Retrieves item version identifiers grouped by review version identifiers.
        Required scopes: docs:review:list
        """
        return await self._transport.request(
            method='POST',
            path='/reviews/versions/item-versions',
            json={'reviewVersionIds': review_version_ids}
        )
