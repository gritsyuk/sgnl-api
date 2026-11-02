from uuid import UUID

import httpx

from ..exceptions import SgnlRequestError
from ..file import file_info, iter_file
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

    async def upload(self, project_id: UUID, file_path: str, mime_type: str = None) -> dict:
        """
        Uploads a local file as a committed object: gets an upload ticket, streams the file to the
        signed S3 URL and commits it. Turn the object into a document with version.create and then
        item.create_file (new document) or item.add_version (new version of an existing one).
        Required scopes: docs:object:create
        :param mime_type: overrides the type guessed from the file extension
        :return: {"object_id", "mime_type", "size"}
        """
        mime_type, size = file_info(file_path, mime_type)

        object_upload = await self.get_object_upload(project_id, mime_type, size)
        object_id = object_upload.get("object_id")

        try:
            upload_response = await self._transport.client.put(
                object_upload.get("signed_url"),
                content=iter_file(file_path),
                headers={"Content-Length": str(size)}
            )
        except httpx.HTTPError as e:
            raise SgnlRequestError(f"File upload of object {object_id} failed: {e}") from e

        if not upload_response.is_success:
            raise SgnlRequestError(
                f"File upload of object {object_id} failed with status "
                f"{upload_response.status_code}: {upload_response.text}",
                status_code=upload_response.status_code
            )

        await self.commit_uploading(object_id)
        return {"object_id": object_id, "mime_type": mime_type, "size": size}
