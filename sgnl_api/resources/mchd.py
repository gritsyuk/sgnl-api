from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class Mchd:
    def __init__(self, transport: Transport):
        self._transport = transport

    @extract_key_from_response(key='data')
    async def company_documents(self, take: int = 100, skip: int = 0) -> list[UUID]:
        """
        Returns a list of mchd UUIDs for the company.
        Required scopes: docs:signing:list
        """
        return await self._transport.request(
            method='GET', path='/mchd/company', params={'Take': take, 'Skip': skip}
        )

    async def attached_documents(self, cades_signature_id: UUID) -> list[dict]:
        """
        Returns a list of mchd ids attached to the cades signature.
        Required scopes: docs:signing:list
        """
        return await self._transport.request(method='GET', path=f'/mchd/cades/signatures/{cades_signature_id}')

    async def download(self, mchd_id: UUID) -> dict:
        """
        Returns a download ticket of mchd.
        Required scopes: docs:signing:read
        """
        return await self._transport.request(method='GET', path=f'/mchd/{mchd_id}/object/download')
