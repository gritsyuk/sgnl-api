from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class DocumentsTransferItem:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns a list of items included in the specified document transfer (with pagination).
        Required scopes: docs:docs_transfer:list
        :param filter: DocumentsTransferItemFind payload, e.g. {"documentsTransferId": ...}
        """
        return await self._transport.request(
            method='POST', path='/documents-transfer-items', params={'Take': take, 'Skip': skip}, json=filter
        )

    @extract_key_from_response(key='data')
    async def count(self, filter: dict) -> int:
        """
        Returns the total number of items included in the specified document transfer.
        Required scopes: docs:docs_transfer:list
        """
        return await self._transport.request(method='POST', path='/documents-transfer-items/count', json=filter)

    async def download(self, documents_transfer_item_id: UUID, file_name: str = None) -> dict:
        """
        Issues a time-limited download ticket for a specific document transfer item.
        Required scopes: docs:docs_transfer:read
        """
        params = {'documentsTransferItemId': documents_transfer_item_id}
        if file_name:
            params['fileName'] = file_name
        return await self._transport.request(method='GET', path='/documents-transfer-items/download', params=params)

    async def add(self, documents_transfer_id: UUID, item_version_ids: list[UUID]) -> None:
        """
        Adds item versions to an existing document transfer.
        Required scopes: docs:docs_transfer:update
        :param item_version_ids: max 200 items
        """
        return await self._transport.request(
            method='POST',
            path='/documents-transfer-items/add',
            json={'documentsTransferId': documents_transfer_id, 'itemVersionIds': item_version_ids}
        )
