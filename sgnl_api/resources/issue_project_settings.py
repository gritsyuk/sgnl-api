from uuid import UUID

from ..transport import Transport


class IssueProjectSettings:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get(self, project_id: UUID) -> dict:
        """
        Returns project settings by the given project identifier.
        Required scopes: docs:issue:read
        """
        return await self._transport.request(
            method='GET', path='/issues/settings/project', params={'projectId': project_id}
        )
