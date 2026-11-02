from uuid import UUID

from ..transport import Transport
from ..utils import drop_none


class AcceptanceCertificate:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def download(self, acceptance_certificate_id: UUID, file_name: str = None) -> dict:
        """
        Issues a time-limited download ticket for an acceptance certificate file.
        Required scopes: docs:docs_transfer:read
        """
        params = {'acceptanceCertificateId': acceptance_certificate_id}
        if file_name:
            params['fileName'] = file_name
        return await self._transport.request(method='GET', path='/acceptance-certificates/download', params=params)

    async def attach(
            self,
            *,
            documents_transfer_id: UUID,
            company_sender: str,
            company_recipient: str,
            project_name: str,
            author_id: UUID,
            contract_number: str = None,
            object_id: UUID = None
    ) -> UUID:
        """
        Attaches an acceptance certificate to a document transfer. Returns the certificate id.
        Required scopes: docs:docs_transfer:update
        :param object_id: Uploaded object with the certificate file (see file.get_object_upload)
        """
        return await self._transport.request(
            method='POST',
            path='/acceptance-certificates/attach',
            json=drop_none(
                documentsTransferId=documents_transfer_id,
                companySender=company_sender,
                companyRecipient=company_recipient,
                contractNumber=contract_number,
                projectName=project_name,
                authorId=author_id,
                objectId=object_id
            )
        )
