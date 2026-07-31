from uuid import UUID

from ..decorators import extract_key_from_response
from ..transport import Transport


class Share:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns shares matching the given filter.
        Required scopes: docs:share:list
        :param filter: ShareFind payload, e.g. {"projectId": ...}
        """
        return await self._transport.request(
            method='POST', path='/shares', params={'Take': take, 'Skip': skip}, json=filter
        )

    @extract_key_from_response(key='data')
    async def create(
            self,
            shared_item_id: UUID,
            shared_item_type: str,
            share_type: str,
            expiry_date: str = None,
            is_snapshot: bool = None
    ) -> UUID:
        """
        Creates a new share for the specified item.
        Required scopes: docs:share:create
        :param shared_item_type: "Item" or "Folder"
        :param share_type: "ViewAndDownload", "ViewOnly" or "SimpleView"
        :param expiry_date: optional ISO date string (YYYY-MM-DD)
        """
        payload = {'sharedItemId': shared_item_id, 'sharedItemType': shared_item_type, 'shareType': share_type}
        if expiry_date is not None:
            payload['expiryDate'] = expiry_date
        if is_snapshot is not None:
            payload['isSnapshot'] = is_snapshot
        return await self._transport.request(method='PUT', path='/shares', json=payload)

    async def update(self, share: dict) -> None:
        """
        Updates an existing share.
        Required scopes: docs:share:update
        :param share: ShareUpdate payload, requires "id"
        """
        return await self._transport.request(method='PATCH', path='/shares', json=share)

    async def delete(self, id: UUID, deleted: bool = True) -> None:
        """
        Updates the deletion state of an existing share.
        Required scopes: docs:share:delete
        """
        return await self._transport.request(method='DELETE', path='/shares', json={'id': id, 'deleted': deleted})

    @extract_key_from_response(key='data')
    async def count(self, filter: dict) -> int:
        """
        Returns the total number of shares matching the given filter.
        Required scopes: docs:share:list
        """
        return await self._transport.request(method='POST', path='/shares/count', json=filter)
