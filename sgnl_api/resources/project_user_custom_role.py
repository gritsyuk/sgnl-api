from uuid import UUID

from ..transport import Transport


class ProjectUserCustomRole:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def set(self, project_id: UUID, user_id: UUID, custom_role_ids: list[UUID]) -> None:
        """
        Assigns or updates the custom roles for a specific user within a specific project.
        This overwrites the user's existing custom roles in the project with the provided list.
        Required scopes: project:role:update
        """
        return await self._transport.request(
            method='PUT',
            path='/project-user-custom-roles',
            json={'projectId': project_id, 'userId': user_id, 'customRoleIds': custom_role_ids}
        )
