from uuid import UUID

from ..transport import Transport


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
