from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class DocumentsTransfer:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns a list of document transfers matching the given filter (with pagination).
        Required scopes: docs:docs_transfer:list
        :param filter: DocumentsTransfersFind payload, e.g. {"projectId": ...}
        """
        return await self._transport.request(
            method='POST', path='/documents-transfers', params={'Take': take, 'Skip': skip}, json=filter
        )

    async def get(self, id: UUID) -> dict:
        """
        Returns all detailed data for a specific document transfer by its identifier.
        Required scopes: docs:docs_transfer:read
        """
        return await self._transport.request(method='GET', path='/documents-transfers', params={'id': id})

    @extract_key_from_response(key='data')
    async def count(self, filter: dict) -> int:
        """
        Returns the total number of document transfers matching the given filter.
        Required scopes: docs:docs_transfer:list
        """
        return await self._transport.request(method='POST', path='/documents-transfers/count', json=filter)

    async def accesses(self, documents_transfer_type_ids: list[UUID]) -> list[dict]:
        """
        Returns a list of access rules for the specified document transfer types.
        Required scopes: docs:docs_transfer:list
        """
        return await self._transport.request(
            method='POST',
            path='/documents-transfers/accesses',
            json={'documentsTransferTypeIds': documents_transfer_type_ids}
        )

    async def create(
            self,
            *,
            documents_transfer_type_id: UUID,
            cipher: str,
            name: str,
            author_id: UUID
    ) -> UUID:
        """
        Creates a new document transfer. Returns its id.
        Required scopes: docs:docs_transfer:create
        """
        return await self._transport.request(
            method='POST',
            path='/documents-transfers/create',
            json={
                'documentsTransferTypeId': documents_transfer_type_id,
                'cipher': cipher,
                'name': name,
                'authorId': author_id
            }
        )
