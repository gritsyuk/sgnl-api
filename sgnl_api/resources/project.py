from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport
from ..utils import drop_none


class Project:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def root_folder(self, project_id: UUID) -> dict:
        """
        Required scopes: project:read
        :param project_id: UUID of the project
        :return: Returns information about a project in Docs.
        """
        return await self._transport.request(
            method='GET',
            path=f'/docs/projects/{project_id}'
        )

    @extract_key_from_response(key='root_folder_id')
    async def root_folder_id(self, project_id: UUID) -> UUID:
        """
        Required scopes: project:read
        :param project_id: UUID of the project
        :return:  Returns root folder UUID of the project.
        """
        return await self.root_folder(project_id)

    async def get_list(
            self,
            take: int = 100,
            skip: int = 0
    ) -> list[dict]:
        """
        Required scopes: project:list
        :param take: The number of items to return. Default value is 100. Maximum value is 200.
        :param skip: The number of items to skip. Default value is 0.
        :return: Returns a list of projects.
        """
        return await self._transport.request(
            method='GET',
            path='/projects',
            params={
                'Take': take,
                'Skip': skip
            }
        )

    async def info(
            self,
            project_id: UUID
    ) -> dict:
        """
        Required scopes: project:read
        :param project_id: UUID of the project
        :return: Returns information about a project in Docs.
        """
        return await self._transport.request(
            method='GET',
            path=f'/projects/{project_id}'
        )

    async def users(
            self,
            project_id: UUID,
            take: int = 100,
            skip: int = 0
    ) -> list[dict]:
        """
        Required scopes: project:user:list
        :param project_id: Project UUID
        :param take: The number of items to return. Default value is 100. Maximum value is 200
        :param skip: The number of items to skip. Default value is 0.
        :return: Returns a list of users associated with a given project.
        """
        return await self._transport.request(
            method='GET',
            path=f'/projects/{project_id}/users',
            params={
                'Take': take,
                'Skip': skip
            }
        )

    async def roles(
            self,
            project_id: UUID,
            take: int = 100,
            skip: int = 0
    ) -> list[dict]:
        """
        Required scopes: project:role:list.
        :param project_id: Project UUID
        :param take: The number of items to return. Default value is 100. Maximum value is 200
        :param skip: The number of items to skip. Default value is 0
        :return: Returns a list of roles associated with a given project.
        """
        return await self._transport.request(
            method='GET',
            path=f'/projects/{project_id}/roles',
            params={
                'Take': take,
                'Skip': skip
            }
        )

    @extract_key_from_response(key='roles')
    async def users_permissions(
            self,
            project_id: UUID,
            user_id: UUID
    ) -> list[str]:
        """
        Required scopes: project:user:read
        :param project_id: Project UUID
        :param user_id: User UUID
        :return: Returns information about a specific user's permissions in a project.
        """
        return await self._transport.request(
            method='GET',
            path=f'/projects/{project_id}/users/{user_id}/permissions'
        )

    @extract_key_from_response(key='data')
    async def get_storage_id(self, project_id: UUID) -> UUID:
        """
        Retrieves the unique identifier of the storage assigned to a specific project.
        Required scopes: project:read
        """
        return await self._transport.request(
            method='GET', path='/docs/projects/storage-id', params={'projectId': project_id}
        )

    async def update(
            self,
            *,
            project_id: UUID,
            name: str,
            time_zone_offset: str,
            code: str = None,
            address: str = None,
            lat: float = None,
            lng: float = None,
            is_default_for_new_users: bool = None
    ) -> None:
        """
        Updates an existing project's basic information.
        Required scopes: project:update
        :param time_zone_offset: TimeZoneOffset value, e.g. "Utc", "UtcPlus3", "UtcMinus5"
        """
        return await self._transport.request(
            method='PATCH',
            path='/projects',
            json=drop_none(
                id=project_id,
                name=name,
                code=code,
                address=address,
                lat=lat,
                lng=lng,
                timeZoneOffset=time_zone_offset,
                isDefaultForNewUsers=is_default_for_new_users
            )
        )
