from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport
from ..utils import drop_none


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

    async def create(
            self,
            *,
            project_id: UUID,
            review_type_id: UUID,
            name: str,
            cipher: str,
            behalf_user_id: UUID,
            plan_date: str = None,
            contract_date: str = None,
            comment: str = None
    ) -> UUID:
        """
        Creates a new review. Returns its id.
        Required scopes: docs:review:create
        :param plan_date: ISO date-time string
        :param contract_date: ISO date-time string
        """
        return await self._transport.request(
            method='POST',
            path='/reviews/create',
            json=drop_none(
                projectId=project_id,
                reviewTypeId=review_type_id,
                name=name,
                cipher=cipher,
                planDate=plan_date,
                contractDate=contract_date,
                behalfUserId=behalf_user_id,
                comment=comment
            )
        )

    async def set_comment(self, review_id: UUID, comment: str, author_id: UUID) -> None:
        """
        Sets or clears the comment of the latest review version, in any review status except deleted.
        Required scopes: docs:review:update
        :param comment: New comment; pass an empty string to clear it
        """
        return await self._transport.request(
            method='PATCH',
            path='/reviews/comment',
            json={'id': review_id, 'comment': comment, 'authorId': author_id}
        )

    async def set_type(self, review_id: UUID, review_type_id: UUID) -> None:
        """
        Sets or updates the type of existing review.
        Required scopes: docs:review:update
        """
        return await self._transport.request(
            method='PATCH', path='/reviews/type', json={'id': review_id, 'reviewTypeId': review_type_id}
        )
