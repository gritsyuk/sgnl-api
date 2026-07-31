from uuid import UUID

from ..transport import Transport


class CompanyUserCustomRole:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def set(self, user_id: UUID, custom_role_ids: list[UUID]) -> None:
        """
        Assigns or updates the custom roles for a specific user at the company level.
        This overwrites the user's existing company-level custom roles with the provided list.
        Required scopes: company:role:update
        """
        return await self._transport.request(
            method='PUT',
            path='/company-user-custom-roles',
            json={'userId': user_id, 'customRoleIds': custom_role_ids}
        )
