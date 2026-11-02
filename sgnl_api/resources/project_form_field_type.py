from uuid import UUID

from ..transport import Transport
from ..utils import drop_none


class ProjectFormFieldType:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, project_form_type_id: UUID, form_field_type_ids: list[UUID] = None) -> dict:
        """
        Retrieves project form field types and related display sources matching the specified filter criteria.
        Required scopes: forms:project_form_field_type:list
        """
        return await self._transport.request(
            method='POST',
            path='/projects/forms/fields/types',
            json=drop_none(projectFormTypeId=project_form_type_id, formFieldTypeIds=form_field_type_ids)
        )
