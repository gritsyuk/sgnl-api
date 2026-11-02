from uuid import UUID

from ..transport import Transport


class ReviewType:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_names(self, project_id: UUID) -> list[dict]:
        """
        Retrieves a list of review type names for the specified project.
        Required scopes: docs:review:list
        """
        return await self._transport.request(
            method='GET', path='/reviews/types/names', params={'projectId': project_id}
        )
