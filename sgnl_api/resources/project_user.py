from uuid import UUID

from ..transport import Transport


class ProjectUser:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def add(self, user_ids: list[UUID], project_ids: list[UUID]) -> None:
        """
        Adds a batch of users to multiple projects.
        Required scopes: hub:project:user:create
        """
        return await self._transport.request(
            method='PUT', path='/project-users', json={'userIds': user_ids, 'projectIds': project_ids}
        )

    async def delete(self, user_ids: list[UUID], project_ids: list[UUID]) -> None:
        """
        Removes a batch of users from multiple projects.
        Required scopes: hub:project:user:delete
        """
        return await self._transport.request(
            method='DELETE', path='/project-users', json={'userIds': user_ids, 'projectIds': project_ids}
        )
