from uuid import UUID

from ..transport import Transport


class Slot:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict) -> list[dict]:
        """
        Retrieves slots of the integration company, ordered by start and identifier.
        Uses cursor paging: pass the cursor from the last item of the previous page.
        Required scopes: settings:slot:list
        :param filter: SlotFind payload, e.g. {"paging": {"take": 100}, "booked": False}
        """
        return await self._transport.request(method='POST', path='/slots', json=filter)

    async def create_batch(self, slots: list[dict]) -> list[dict]:
        """
        Creates a batch of slots in the integration company.
        Required scopes: settings:slot:create
        :param slots: e.g. [{"userId": ..., "start": "...", "end": "...", "projectIds": [...]}] (max 200)
        """
        return await self._transport.request(method='POST', path='/slots/create-batch', json={'slots': slots})

    async def delete_batch(self, slot_ids: list[UUID]) -> None:
        """
        Deletes the specified slots in the integration company.
        Required scopes: settings:slot:delete
        :param slot_ids: max 200 items
        """
        return await self._transport.request(method='DELETE', path='/slots', json={'slotIds': slot_ids})
