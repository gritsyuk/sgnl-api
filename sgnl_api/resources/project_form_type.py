from uuid import UUID

from ..transport import Transport
from ..utils import drop_none


class ProjectFormType:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, project_id: UUID, deleted: bool = None, ids: list[UUID] = None) -> list[dict]:
        """
        Retrieves a list of project form types matching the specified filter criteria.
        Required scopes: forms:project_form_type:list
        """
        return await self._transport.request(
            method='POST',
            path='/projects/forms/types',
            json=drop_none(projectId=project_id, deleted=deleted, ids=ids)
        )
