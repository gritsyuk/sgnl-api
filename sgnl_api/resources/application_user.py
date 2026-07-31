from uuid import UUID

from ..transport import Transport


class ApplicationUser:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def upsert(self, user_ids: list[UUID], application_ids: list[UUID], role: str) -> None:
        """
        Grants specific application roles to a batch of users across multiple applications.
        Required scopes: hub:application:user:update
        :param role: "Admin" or "User"
        """
        return await self._transport.request(
            method='PUT',
            path='/application-users',
            json={'userIds': user_ids, 'applicationIds': application_ids, 'role': role}
        )

    async def delete(self, user_ids: list[UUID], application_ids: list[UUID]) -> None:
        """
        Revokes access for a batch of users across multiple applications.
        Required scopes: hub:application:user:delete
        """
        return await self._transport.request(
            method='DELETE',
            path='/application-users',
            json={'userIds': user_ids, 'applicationIds': application_ids}
        )
