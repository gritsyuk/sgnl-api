from uuid import UUID

from ..transport import Transport


class EmbeddedSignature:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, item_id: UUID) -> list[dict]:
        """
        Returns a list of the item's embedded signatures.
        Required scopes: docs:signing:list
        """
        return await self._transport.request(method='GET', path='/embedded/signatures', params={'itemId': item_id})

    async def create(self, item_id: UUID, version_id: UUID, certificate_id: UUID, signature: str) -> None:
        """
        Creates a new embedded signature.
        Required scopes: docs:signing:create
        """
        return await self._transport.request(
            method='PUT',
            path='/embedded/signatures',
            json={
                'itemId': item_id,
                'versionId': version_id,
                'certificateId': certificate_id,
                'signature': signature
            }
        )
