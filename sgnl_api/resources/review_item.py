from uuid import UUID

from ..transport import Transport


class ReviewItem:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_statuses(self, project_id: UUID, item_version_ids: list[UUID], review_id: UUID = None) -> list[dict]:
        """
        Returns a list of review statuses for specific item versions.
        Required scopes: docs:review:list
        :param item_version_ids: min 1, max 50 items
        :param review_id: optionally filter statuses by a specific review
        """
        payload = {'projectId': project_id, 'itemVersionIds': item_version_ids}
        if review_id is not None:
            payload['reviewId'] = review_id
        return await self._transport.request(method='POST', path='/reviews/items', json=payload)
