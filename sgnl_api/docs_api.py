import httpx
from uuid import UUID
from datetime import datetime, timedelta
from .scopes import SCOPES_DEFAULT
from .decorators import extract_key_from_response
from .file import read_file
from .utils import keys_to_snake_case


class DocsApi:
    """DocsApi client for interacting with the SGNL DOCS API.
    Do not initialize this class directly. Use the create() classmethod instead:
    Example:
        ```python
        api = await DocsApi.create(client_id="your_id", client_secret="your_secret")
        ```
    """

    def __init__(self,
                 *,
                 client_id: str,
                 client_secret: str,
                 scopes: list[str] = SCOPES_DEFAULT) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = [*scopes]
        self.base_url = "https://api.sgnl.pro/public/v1"
        self._jwt = None
        self._jwt_expires_at = None

        self.item = self.Item(self)
        self.folder = self.Folder(self)
        self.project = self.Project(self)
        self.company = self.Company(self)
        self.version = self.Version(self)
        self.file = self.File(self)

    @classmethod
    async def create(
            cls,
            *,
            client_id: str,
            client_secret: str,
            scopes: list[str] = SCOPES_DEFAULT) -> "DocsApi":
        """Create and initialize a new DocsApi instance.
               Args:
                   client_id: Your SGNL DOCS API client ID
                   client_secret: Your SGNL DOCS API client secret
                   scopes: List of scopes
               Returns:
                   An initialized DocsApi instance
               Example:
                   ```python
                   api = await DocsApi.create(
                       client_id="your_id",
                       client_secret="your_secret"
                   )
                   ```
               """
        instance = cls(client_id=client_id, client_secret=client_secret, scopes=scopes)
        await instance._ensure_token()
        return instance

    async def _ensure_token(self):
        if self._jwt is None or (self._jwt_expires_at and datetime.now() >= self._jwt_expires_at):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f'{self.base_url}/auth/token',
                        json={
                            "clientId": self.client_id,
                            "clientSecret": self.client_secret,
                            "scopes": self.scopes
                        },
                        headers={'Content-Type': 'application/json'}
                    )
                    response.raise_for_status()
                    data = response.json()
                    self._jwt = data.get('token')
                    expires_in = data.get('expiresIn', 3600)
                    self._jwt_expires_at = datetime.now() + timedelta(seconds=expires_in)
            except Exception as e:
                raise Exception(f"AUTHENTICATION ERROR: {e}")

    async def _make_request(
            self,
            method: str,
            url: str,
            params: dict = None,
            json: dict = None,
            headers: dict = None) -> str:

        error_messages = {
            400: "Bad request",
            401: "The request did not have the correct authorization header credentials.",
            403: "Forbidden",
            404: "Not Found",
            450: "Maximum resource quota reached. To increase the quota, contact support.",
            500: "Api server error"
        }

        try:
            await self._ensure_token()
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=headers)

                if response.is_success:
                    return keys_to_snake_case(response.json())
                else:
                    error_message = error_messages.get(response.status_code, "Неизвестная ошибка")
                    return {
                        "error": response.status_code,
                        "message": error_message
                    }
        except Exception as e:
            raise Exception(f"Error: {e}")

    def _get_headers(self, additional_headers: dict = None) -> dict:
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self._jwt}"
        }
        if additional_headers:
            headers.update(additional_headers)
        return headers

    class Item:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def get_list(
                self,
                folder_id: UUID,
                deleted: bool = False,
                take: int = 100,
                skip: int = 0
        ) -> list[dict]:
            """
            Required scopes: docs:item:list
            :param folder_id: UUID of the folder
            :param deleted: If true, returns deleted items
            :param take: Number of items to return
            :param skip: Number of items to skip
            :return: Returns a folder`s not nested items list.
            """
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/items',
                params={
                    'folderId': folder_id,
                    'take': take,
                    'skip': skip,
                    'deleted': deleted
                },
                headers=self.api._get_headers()
            )

        @extract_key_from_response(key="data")
        async def count(
                self,
                folder_id: UUID,
                deleted: bool = False
        ) -> int:
            """
            Required scopes: docs:item:list
            :param folder_id: UUID of the folder
            :param deleted: If true, returns deleted items
            :return: Returns a count items in folder`s not nested items list.
            """
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/items/count',
                params={
                    'folderId': folder_id,
                    'deleted': deleted
                },
                headers=self.api._get_headers()
            )

        @extract_key_from_response(key='data')
        async def create_file(
                self,
                name: str,
                folder_id: UUID,
                version_id: UUID
        ) -> UUID:
            """
            Creates a new File item with a version and attaches it to the item. Returns the id of the created item.
            Required scopes: docs:item:create
            :param name: Name of item to create
            :param folder_id: UUID of the folder
            :param version_id: UUID of the version
            :return: UUID of the created item
            """
            return await self.api._make_request(
                method='PUT',
                url=f'{self.api.base_url}/items/file',
                json={
                    'name': name,
                    'folderId': folder_id,
                    'versionId': version_id
                },
                headers=self.api._get_headers()
            )

        @extract_key_from_response(key='data')
        async def create_link(
                self,
                name: str,
                folder_id: UUID,
                version_id: UUID
        ) -> UUID:
            """
            Creates a new Link item. Returns the id of the created item.
            Required scopes: docs:item:create
            :param name:
            :param folder_id:
            :param version_id:
            :return: UUID of the created link.
            """
            return await self.api._make_request(
                method='PUT',
                url=f'{self.api.base_url}/items/link',
                json={
                    'name': name,
                    'folderId': folder_id,
                    'versionId': version_id
                },
                headers=self.api._get_headers()
            )

        async def get_link(
                self,
                item_id: UUID,
                version_id: UUID,
                file_name: str = None
        ) -> dict:
            """
            Required scopes: docs:item:read.
            :param item_id: Item UUID
            :param version_id: Version UUID
            :param file_name: ...
            :return: Returns S3 download link
            """
            params = {
                'itemId': item_id,
                'versionId': version_id
            }
            if file_name:
                params['fileName'] = file_name
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/items/download',
                params=params,
                headers=self.api._get_headers()
            )

        async def add_version(
                self,
                item_id: UUID,
                version_id: UUID
        ) -> None:
            """
            Attaches a version to an existing item.
            Required scopes: docs:version:create
            :param item_id:
            :param version_id:
            :return: None
            """
            return await self.api._make_request(
                method='PUT',
                url=f'{self.api.base_url}/items/versions',
                json={
                    'itemId': item_id,
                    'versionId': version_id
                },
                headers=self.api._get_headers()
            )

    class Folder:
        def __init__(self, api: 'DocsApi'):
            self.api = api

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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/folders/{folder_id}/children',
                params={
                    'deleted': deleted
                },
                headers=self.api._get_headers()
            )

        @extract_key_from_response(key='data')
        async def create(
                self,
                parent_id: UUID,
                name: str = 'new folder from api'
        ) -> UUID:
            """
            Creates a new folder.
            Required scopes: docs:folder:create
            :param parent_id: UUID of the parent folder
            :param name: Name of the folder
            :return: UUID of the created folder.
            """
            return await self.api._make_request(
                method='PUT',
                url=f'{self.api.base_url}/folders',
                json={
                    'parentId': parent_id,
                    'name': name
                },
                headers=self.api._get_headers()
            )

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
            return await self.api._make_request(
                method='PATCH',
                url=f'{self.api.base_url}/folders',
                json={
                    'id': folder_id,
                    'name': name
                },
                headers=self.api._get_headers()
            )

    class Project:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def root_folder(self, project_id: UUID) -> dict:
            """
            Required scopes: project:read
            :param project_id: UUID of the project
            :return: Returns information about a project in Docs.
            """
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/docs/projects/{project_id}',
                headers=self.api._get_headers()
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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects',
                params={
                    'Take': take,
                    'Skip': skip
                },
                headers=self.api._get_headers()
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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects/{project_id}',
                headers=self.api._get_headers()
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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects/{project_id}/users',
                params={
                    'Take': take,
                    'Skip': skip
                },
                headers=self.api._get_headers()
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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects/{project_id}/roles',
                params={
                    'Take': take,
                    'Skip': skip
                },
                headers=self.api._get_headers()
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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects/{project_id}/users/{user_id}/permission',
                headers=self.api._get_headers()
            )

    class Company:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def users_list(self, take: int = 100, skip: int = 0) -> list[dict]:
            """
            Required scopes: company:user:list
            :param take: The number of items to return. Default value is 100. Maximum value is 200.
            :param skip: The number of items to skip. Default value is 0.
            :return: Returns a list of users associated with a company.
            """
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/company/users',
                params={
                    'Take': take,
                    'Skip': skip
                },
                headers=self.api._get_headers()
            )

        async def roles_list(self, take: int = 100, skip: int = 0) -> list[dict]:
            """
            Required scopes: company:role:list
            :param take: The number of items to return. Default value is 100. Maximum value is 200.
            :param skip: The number of items to skip. Default value is 0.
            :return: Returns a list of roles associated with a company.
            """
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/company/roles',
                params={
                    'Take': take,
                    'Skip': skip
                },
                headers=self.api._get_headers()
            )

    class Version:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def get_list(
                self,
                item_id: UUID,
                take: int = 100,
                skip: int = 0
        ) -> list[dict]:
            """
            Returns a list of versions of item
            Required scopes: docs:version:list
            :param item_id: Item UUID
            :param take: The number of items to return. Default value is 100. Maximum value is 200.
            :param skip: The number of items to skip. Default value is 0.
            :return: list of versions of item
            """
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/versions',
                params={
                    'itemId': item_id,
                    'Take': take,
                    'Skip': skip
                },
                headers=self.api._get_headers()
            )

        @extract_key_from_response(key="data")
        async def count(
                self,
                item_id: UUID
        ) -> int:
            """
            Returns the count of item`s versions.
            Required scopes: docs:version:list
            :param item_id: Item UUID
            :return: count items
            """
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/versions',
                params={
                    'itemId': item_id
                },
                headers=self.api._get_headers()
            )

        @extract_key_from_response(key="data")
        async def create(
                self,
                *,
                object_id: UUID,
                project_id: UUID,
                name: str
        ) -> UUID:
            """
            Creates a new version of an object. Returns the id of the created version.
            Required scopes: docs:version:create
            :param object_id: UUID of the object
            :param project_id: UUID of the project
            :param name: ...
            :return: UUID of the created version
            """
            return await self.api._make_request(
                method='POST',
                url=f'{self.api.base_url}/versions',
                json={
                    'objectId': object_id,
                    'projectId': project_id,
                    'name': name
                },
                headers=self.api._get_headers()
            )

    class File:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def get_object_upload(
                self,
                project_id: UUID,
                mime_type: str,
                size: int
        ) -> dict:
            """
            Returns the object upload ticket. Each object must be committed.
            Required scopes: docs:object:create
            :param project_id: UUID of the project
            :param mime_type: mime type of the file
            :param size: file size in bytes
            :return: dict: Object upload ticket
            """
            return await self.api._make_request(
                method='PUT',
                url=f'{self.api.base_url}/objects',
                json={
                    "projectId": project_id,
                    "mimeType": mime_type,
                    "size": size
                },
                headers=self.api._get_headers()
            )

        async def commit_uploading(
                self,
                object_id: UUID
        ) -> None:
            """
            Commiting object upload after put it in S3.
            Required scopes: docs:object:create
            :param object_id: UUID S3 object
            :return: None
            """
            return await self.api._make_request(
                method='POST',
                url=f'{self.api.base_url}/objects/{object_id}/uploading/commit',
                headers=self.api._get_headers()
            )

        async def upload(self, project_id: UUID, file_path: str):
            file_info = await read_file(file_path)
            if file_info is None:
                raise FileExistsError
            file_data, mime_type, size = file_info
            object_upload = await self.get_object_upload(project_id, mime_type, size)
            async with httpx.AsyncClient() as client:
                upload_response = await client.put(
                    object_upload.get("signed_url"),
                    content=file_data
                )
                if upload_response.status_code != 200:
                    return {
                        "error": upload_response.status_code,
                        "message": upload_response.text
                    }

            result_status = await self.commit_uploading(project_id, object_upload.get("object_id"))

            return result_status
