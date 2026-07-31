from uuid import UUID

from ..transport import Transport


class CardPublicLink:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def regenerate(self, pub_link: UUID) -> dict:
        """
        Regenerating the public link for the dashboard card.
        Required scopes: dash:card_public_link:update
        """
        return await self._transport.request(
            method='PATCH', path='/card-public-links/regenerate', params={'pubLink': pub_link}
        )
