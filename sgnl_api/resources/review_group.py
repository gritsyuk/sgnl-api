from ..transport import Transport


class ReviewGroup:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Retrieves a list of review groups for the specified project.
        Required scopes: docs:review:list
        :param filter: ReviewGroupFind payload, e.g. {"projectId": ...}
        """
        return await self._transport.request(
            method='POST', path='/reviews/groups', params={'Take': take, 'Skip': skip}, json=filter
        )
