from uuid import UUID

from ..transport import Transport


class Booking:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict) -> list[dict]:
        """
        Retrieves bookings of the integration company, ordered by modified and identifier.
        Uses cursor paging: pass the cursor from the last item of the previous page.
        Required scopes: settings:booking:list
        :param filter: BookingFind payload, e.g. {"paging": {"take": 100}, "projectIds": [...]}
        """
        return await self._transport.request(method='POST', path='/bookings', json=filter)

    async def create_batch(self, project_id: UUID, bookings: list[dict]) -> list[dict]:
        """
        Creates a batch of bookings in the integration company.
        Required scopes: settings:booking:create
        :param bookings: e.g. [{"slotId": ..., "sourceId": ..., "sourceType": "Forms"}] (max 200)
        """
        return await self._transport.request(
            method='POST', path='/bookings/create-batch', json={'projectId': project_id, 'bookings': bookings}
        )

    async def delete_batch(self, booking_ids: list[UUID]) -> None:
        """
        Deletes the specified bookings in the integration company.
        Required scopes: settings:booking:delete
        :param booking_ids: max 200 items
        """
        return await self._transport.request(method='DELETE', path='/bookings', json={'bookingIds': booking_ids})
