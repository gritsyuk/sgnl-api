from uuid import UUID

from ..transport import Transport


class IssueAttachment:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict) -> list[dict]:
        """
        Returns a list of attachments for the specified issue.
        Required scopes: docs:issue:list
        :param filter: IssueAttachmentFind payload, e.g. {"issueId": ...}
        """
        return await self._transport.request(method='POST', path='/issues/attachments', json=filter)

    async def download_object(self, issue_attachment_id: UUID, file_name: str = None) -> dict:
        """
        Creates a download ticket for an attachment object.
        Required scopes: docs:issue:read
        """
        payload = {'issueAttachmentId': issue_attachment_id}
        if file_name:
            payload['fileName'] = file_name
        return await self._transport.request(method='POST', path='/issues/attachments/object/download', json=payload)
