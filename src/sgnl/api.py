import httpx
from typing import List
from datetime import datetime, timedelta
from .scopes import SCOPES_DEFAULT


class DocsApi:
    def __init__(self,
                 *,
                 client_id: str,
                 client_secret: str,
                 scopes: List[str] = SCOPES_DEFAULT) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = [*scopes]
        self.base_url = "https://api.sgnl.pro/public/v1"
        self._jwt = None
        self._jwt_expires_at = None

        self.item = self.Item(self)
        self.folder = self.Folder(self)
        self.project = self.Project(self)

    @classmethod
    async def create(
            cls,
            *,
            client_id: str,
            client_secret: str,
            scopes: List[str] = SCOPES_DEFAULT):
        instance = cls(client_id=client_id, client_secret=client_secret, scopes=scopes)
        await instance.ensure_token()
        return instance

    async def _make_request(
            self,
            method: str,
            url: str,
            params: dict = None,
            json: dict = None,
            headers: dict = None) -> str:
        try:
            await self.ensure_token()
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers)
                response.raise_for_status()
                return response.text
        except httpx.RequestError as e:
            raise Exception(f"Ошибка запроса: {e}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Ошибка HTTP {e.response.status_code}: {e.response.text}")

    async def ensure_token(self):
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

    def _get_headers(self, additional_headers: dict = None) -> dict:
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self._jwt}"
        }
        if additional_headers:
            headers.update(additional_headers)
        return headers


    async def get_users(self, take: int = 100, skip: int = 0):
        return await self._make_request(
            method='GET',
            url=f'{self.base_url}/company/users?Take={take}&Skip={skip}',
            headers=self._get_headers()
        )

    class Item:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def get_list(
                self,
                folder_id: str,
                deleted: bool = False,
                take: int = 100,
                skip: int = 0
        ):
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

        async def get_count(
                self,
                folder_id: str,
                deleted: bool = False
        ):
            return await self.api._make_request(
                method='GET',
                url=f'{self.base_url}/items/count',
                params={
                    'folderId': folder_id,
                    'deleted': deleted
                },
                headers=self.api._get_headers()
            )

        async def get_download_link(
                self,
                folder_id: str,
                version_id: str,
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

    class Folder:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def get_list(
                self,
                folder_id: str,
                deleted: bool = False
        ):
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/folders/{folder_id}/children',
                params={
                    # 'folderId': folder_id,
                    'deleted': deleted
                },
                headers=self.api._get_headers()
            )

        async def create(
                self,
                parent_id: str,
                name: str = 'new folder from api'
        ):
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
                id: str,
                name: str
        ):
            return await self.api._make_request(
                method='PATCH',
                url=f'{self.api.base_url}/folders',
                json={
                    'id': id,
                    'name': name
                },
                headers=self.api._get_headers()
            )

    class Project:
        def __init__(self, api: 'DocsApi'):
            self.api = api

        async def root_folder(self, uuid: str):
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/docs/projects/{uuid}',
                headers=self.api._get_headers()
            )

        async def list(
                self,
                take: int = 100,
                skip: int = 0
        ):
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
                project_id: str,
        ):
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects/{project_id}',
                headers=self.api._get_headers()
            )

        async def users(
                self,
                project_id: str,
                take: int = 100,
                skip: int = 0
        ):
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
                project_id: str,
                take: int = 100,
                skip: int = 0
        ):
            return await self.api._make_request(
                method='GET',
                url=f'{self.api.base_url}/projects/{project_id}/roles',
                params={
                    'Take': take,
                    'Skip': skip
                },
                headers=self.api._get_headers()
            )

        # async def user_permission(
        #         self,
        #         project_id: str,
        #         user_id: str
        # ):
        #     return await self.api._make_request(
        #         method='GET',
        #         url=f'{self.api.base_url}/projects/{project_id}/users/{user_id}/permission',
        #         headers=self.api._get_headers()
        #     )
