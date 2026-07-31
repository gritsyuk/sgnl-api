from uuid import UUID

import httpx

from ..exceptions import SgnlRequestError
from ..file import read_file
from ..transport import Transport


class File:
    def __init__(self, transport: Transport):
        self._transport = transport

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
        return await self._transport.request(
            method='PUT',
            path='/objects',
            json={
                "projectId": project_id,
                "mimeType": mime_type,
                "size": size
            }
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
        return await self._transport.request(
            method='POST',
            path=f'/objects/{object_id}/uploading/commit'
        )

    async def upload(self, project_id: UUID, file_path: str) -> None:
        file_info = await read_file(file_path)
        if file_info is None:
            raise FileNotFoundError(file_path)
        file_data, mime_type, size = file_info

        object_upload = await self.get_object_upload(project_id, mime_type, size)

        try:
            upload_response = await self._transport.client.put(
                object_upload.get("signed_url"),
                content=file_data
            )
        except httpx.HTTPError as e:
            raise SgnlRequestError(f"File upload failed: {e}") from e

        if not upload_response.is_success:
            raise SgnlRequestError(
                f"File upload failed with status {upload_response.status_code}: {upload_response.text}",
                status_code=upload_response.status_code
            )

        return await self.commit_uploading(object_upload.get("object_id"))
