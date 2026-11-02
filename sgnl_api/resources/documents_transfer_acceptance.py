from uuid import UUID

from ..transport import Transport
from ..utils import drop_none


class DocumentsTransferAcceptance:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def send(
            self,
            *,
            documents_transfer_id: UUID,
            recipient: dict,
            author_id: UUID,
            share_expiry_date: str = None
    ) -> None:
        """
        Sends a prepared document transfer to a recipient.
        Required scopes: docs:docs_transfer:update
        :param recipient: DocumentsTransferRecipient, e.g. {"type": "User"|"Role"|"Email", "identifier": "..."}
        :param share_expiry_date: optional ISO date string (YYYY-MM-DD)
        """
        return await self._transport.request(
            method='POST',
            path='/documents-transfer-acceptances/send',
            json=drop_none(
                documentsTransferId=documents_transfer_id,
                recipient=recipient,
                authorId=author_id,
                shareExpiryDate=share_expiry_date
            )
        )
