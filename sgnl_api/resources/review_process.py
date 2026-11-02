from uuid import UUID

from ..transport import Transport
from ..utils import drop_none


class ReviewProcess:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def start(
            self,
            review_id: UUID,
            behalf_user_id: UUID,
            comment: str = None,
            responsibles_by_stage_type_ids: dict = None
    ) -> None:
        """
        Starts the review process for a specific review.
        Required scopes: docs:review:update
        :param responsibles_by_stage_type_ids: maps stage type id to an Identity,
            e.g. {"<stageTypeId>": {"id": ..., "type": "User"}}
        """
        return await self._transport.request(
            method='POST',
            path='/reviews/process/start',
            json=drop_none(
                reviewId=review_id,
                comment=comment,
                responsiblesByStageTypeIds=responsibles_by_stage_type_ids,
                behalfUserId=behalf_user_id
            )
        )
