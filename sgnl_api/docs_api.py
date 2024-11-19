import httpx
from uuid import UUID
from datetime import datetime, timedelta
from .scopes import SCOPES_DEFAULT
from .decorators import extract_key_from_response
from .file import read_file


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
            except httpx.RequestError as e:
                raise Exception(f"Ошибка запроса: {e}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"Ошибка HTTP {e.response.status_code}: {e.response.text}")

    async def _make_request(
            self,
            method: str,
            url: str,
            params: dict = None,
            json: dict = None,
            headers: dict = None) -> str:
        try:
            await self._ensure_token()
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise Exception(f"Ошибка запроса: {e}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Ошибка HTTP {e.response.status_code}: {e.response.text}")

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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/items/count',
                params={
                    'folderId': folder_id,
                    'deleted': deleted
                },
                headers=self.api._get_headers()
            )

        async def download_link(
                self,
                folder_id: UUID,
                version_id: UUID,
                file_name: str = None
        ):
            params = {
                'folderId': folder_id,
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

        async def create(
                self,
                name: str,
                folder_id: UUID,
                version_id: UUID
        ) -> dict:
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

        async def create_link(
                self,
                name: str,
                folder_id: UUID,
                version_id: UUID
        ) -> dict:
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

        async def new_version(
                self,
                item_id: UUID,
                version_id: UUID
        ) -> dict:
            return await self.api._make_request(
                method='PUT',
                url=f'{self.api.base_url}/items/versions',
                json={
                    'folderId': item_id,
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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/folders/{folder_id}/children',
                params={
                    'deleted': deleted
                },
                headers=self.api._get_headers()
            )

        async def create(
                self,
                parent_id: UUID,
                name: str = 'new folder from api'
        ) -> dict:
            return await self.api._make_request(
                method='PUT',
                url=f'{self.api.base_url}/folders',
                json={
                    'parentId': parent_id,
                    'name': name
                },
                headers=self.api._get_headers()
            )

        async def update(
                self,
                folder_id: UUID,
                name: str
        ) -> dict:
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

        async def root_folder(
                self,
                project_id: UUID) -> dict:
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/docs/projects/{project_id}',
                headers=self.api._get_headers()
            )

        @extract_key_from_response(key='rootFolderId')
        async def root_folder_id(self, project_id: UUID) -> dict:
            return await self.root_folder(project_id)

        async def get_list(
                self,
                take: int = 100,
                skip: int = 0
        ) -> list[dict]:
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
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects/{project_id}/roles',
                params={
                    'Take': take,
                    'Skip': skip
                },
                headers=self.api._get_headers()
            )

        async def users_permissions(
                self,
                project_id: UUID,
                user_id: UUID
        ) -> dict:
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects/{project_id}/users/{user_id}/permission',
                headers=self.api._get_headers()
            )

    class Company:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def users_list(self, take: int = 100, skip: int = 0) -> list[dict]:
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

        async def list(
                self,
                item_id: UUID,
                take: int = 100,
                skip: int = 0
        ) -> list[dict]:
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
        ) -> dict:
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/versions',
                params={
                    'itemId': item_id
                },
                headers=self.api._get_headers()
            )

        async def new(
                self,
                *,
                object_id: UUID,
                project_id: UUID,
                name: str
        ) -> dict:
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
        ) -> dict:
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
                    object_upload.get("signedUrl"),
                    content=file_data
                )

                if upload_response.status_code != 200:
                    raise ConnectionAbortedError

            result_status = await self.commit_uploading(project_id, object_upload.get("objectId"))

            return result_status
