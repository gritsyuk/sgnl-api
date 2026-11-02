from uuid import UUID

from ..transport import Transport


class Card:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Returns the cards of a dashboard, optionally narrowed to specific groups.
        Deleted cards, and cards of a deleted group or dashboard, are never returned.
        Required scopes: dash:card:list
        :param filter: CardFind payload, e.g. {"boardId": ..., "groupIds": [...]}
        """
        return await self._transport.request(
            method='POST', path='/boards/cards', params={'Take': take, 'Skip': skip}, json=filter
        )

    async def get(self, card_id: UUID) -> dict:
        """
        Returns a single card with its content. Deleted cards, and cards of a deleted group
        or dashboard, are not available and the request fails.
        Required scopes: dash:card:read
        """
        return await self._transport.request(method='GET', path=f'/boards/cards/{card_id}')
