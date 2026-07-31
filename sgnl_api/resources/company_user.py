from uuid import UUID

from ..transport import Transport


class CompanyUser:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_id_by_telegram_id(self, telegram_id: int) -> UUID:
        """Returns the company user id linked to the given Telegram id."""
        return await self._transport.request(
            method='GET', path='/company-users/by-telegram-id', params={'telegramId': telegram_id}
        )

    async def add(self, users: list[dict]) -> list[dict]:
        """
        Invites or adds a batch of new users to the company.
        Required scopes: hub:company:user:create
        :param users: list of CompanyUserAdd payloads, e.g. [{"email": "...", "firstName": "..."}]
        """
        return await self._transport.request(method='PUT', path='/company-users', json={'users': users})

    async def delete(self, user_ids: list[UUID]) -> None:
        """
        Removes a batch of users from the company.
        Required scopes: hub:company:user:delete
        """
        return await self._transport.request(method='DELETE', path='/company-users', json={'userIds': user_ids})
