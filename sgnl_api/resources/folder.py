from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class Folder:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(
            self,
            folder_id: UUID,
            deleted: bool = False
    ) -> list[dict]:
        """
        Required scopes: docs:folder:list
        :param folder_id: UUID of the folder
        :param deleted: If true, returns deleted items
        :return: Returns a list of folder`s children.
        """
        return await self._transport.request(
            method='GET',
            path=f'/folders/{folder_id}/children',
            params={
                'deleted': deleted
            }
        )

    @extract_key_from_response(key='data')
    async def create(
            self,
            parent_id: UUID,
            name: str = 'new folder from api',
            color: str = None
    ) -> UUID:
        """
        Creates a new folder.
        Required scopes: docs:folder:create
        :param parent_id: UUID of the parent folder
        :param name: Name of the folder
        :param color: ColorKey value, e.g. "AccentMain", "AccentRed", "AccentGreen"
        :return: UUID of the created folder.
        """
        payload = {'parentId': parent_id, 'name': name}
        if color is not None:
            payload['color'] = color
        return await self._transport.request(method='PUT', path='/folders', json=payload)

    async def update(
            self,
            folder_id: UUID,
            name: str = None,
            color: str = None
    ) -> None:
        """
        Updates a folder's name and/or color.
        Required scopes: docs:folder:update
        :param folder_id: UUID of the folder
        :param name: New name of the folder
        :param color: New ColorKey value, e.g. "AccentMain", "AccentRed", "AccentGreen"
        :return: None
        """
        payload = {'id': folder_id}
        if name is not None:
            payload['name'] = name
        if color is not None:
            payload['color'] = color
        return await self._transport.request(method='PATCH', path='/folders', json=payload)

    async def rename(
            self,
            folder_id: UUID,
            name: str
    ) -> None:
        """
        Updates a folder - rename
        Required scopes: docs:folder:update
        :param folder_id: UUID of the folder
        :param name: New name of the folder
        :return: None
        """
        return await self.update(folder_id, name=name)

    async def delete(self, folder_id: UUID) -> None:
        """
        Moves a folder to the trash.
        Required scopes: docs:folder:delete
        """
        return await self._transport.request(method='DELETE', path=f'/folders/{folder_id}')

    async def get_project_tree(self, project_id: UUID) -> dict:
        """
        Retrieves the full folder tree of the specified project with user permissions.
        Required scopes: docs:folder:read
        """
        return await self._transport.request(
            method='GET', path=f'/projects/{project_id}/folders/tree'
        )
