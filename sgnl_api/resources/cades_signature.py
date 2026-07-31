from uuid import UUID

from ..transport import Transport


class CadesSignature:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, version_id: UUID, search_mchd_ids: bool = None) -> list[dict]:
        """
        Returns a list of the version's cades signatures.
        Required scopes: docs:signing:list
        """
        params = {'versionId': version_id}
        if search_mchd_ids is not None:
            params['searchMchdIds'] = search_mchd_ids
        return await self._transport.request(method='GET', path='/cades/signatures', params=params)

    async def create(self, certificate_id: UUID, version_id: UUID, signature: str) -> None:
        """
        Creates a new Cades signature.
        Required scopes: docs:signing:create
        """
        return await self._transport.request(
            method='PUT',
            path='/cades/signatures',
            json={'certificateId': certificate_id, 'versionId': version_id, 'signature': signature}
        )
