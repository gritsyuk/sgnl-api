from uuid import UUID

from ..transport import Transport
from ..utils import drop_none


class ProjectForm:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(
            self,
            find: dict,
            order: str = None,
            is_order_asc: bool = None,
            take: int = 100,
            skip: int = 0
    ) -> dict:
        """
        Retrieves a paginated list of project forms matching the specified filter and order criteria.
        Required scopes: forms:project_form:list
        :param find: ProjectFormFind payload, e.g. {"projectId": ..., "formTypeId": ...}
        :param order: ProjectFormOrder value: "Number", "Type", "Added" or "Modified"
        """
        return await self._transport.request(
            method='POST',
            path='/projects/forms',
            params={'Take': take, 'Skip': skip},
            json=drop_none(find=find, order=order, isOrderAsc=is_order_asc)
        )

    async def count(self, filter: dict) -> int:
        """
        Retrieves the total number of project forms matching the specified filter criteria.
        Required scopes: forms:project_form:list
        :param filter: ProjectFormFind payload, e.g. {"projectId": ..., "formTypeId": ...}
        """
        return await self._transport.request(method='POST', path='/projects/forms/count', json=filter)

    async def get(self, project_form_id: UUID) -> dict:
        """
        Retrieves a project form by its identifier.
        Required scopes: forms:project_form:read
        """
        return await self._transport.request(
            method='POST', path='/projects/forms/get', json={'projectFormId': project_form_id}
        )

    async def get_summary(self, project_ids: list[UUID], project_form_ids: list[UUID]) -> list[dict]:
        """
        Retrieves summaries of the specified project forms.
        Required scopes: forms:project_form:read
        """
        return await self._transport.request(
            method='POST',
            path='/projects/forms/get-summary',
            json={'projectIds': project_ids, 'projectFormIds': project_form_ids}
        )

    async def create_batch(
            self,
            project_form_type_id: UUID,
            forms: list[dict],
            complete_forms_if_possible: bool = None,
            ensure_forms_are_not_duplicated: bool = None
    ) -> list[UUID]:
        """
        Creates a batch of project forms. Returns the ids of created forms.
        Required scopes: forms:project_form:create
        :param forms: list of ProjectFormCreate payloads, e.g. [{"fields": [...]}] (max 200)
        """
        return await self._transport.request(
            method='POST',
            path='/projects/forms/create-batch',
            json=drop_none(
                projectFormTypeId=project_form_type_id,
                forms=forms,
                completeFormsIfPossible=complete_forms_if_possible,
                ensureFormsAreNotDuplicated=ensure_forms_are_not_duplicated
            )
        )

    async def update(self, project_form_id: UUID, project_form_fields: list[dict]) -> None:
        """
        Updates an existing project form.
        Required scopes: forms:project_form:update
        :param project_form_fields: list of ProjectFormFieldUpdate payloads,
            e.g. [{"formFieldTypeId": ..., "projectFormFieldValue": {...}}]
        """
        return await self._transport.request(
            method='PATCH',
            path='/projects/forms/update',
            json={'projectFormId': project_form_id, 'projectFormFields': project_form_fields}
        )

    async def complete(self, project_form_id: UUID) -> None:
        """
        Completes an existing project form.
        Required scopes: forms:project_form:update
        """
        return await self._transport.request(
            method='PATCH', path='/projects/forms/complete', json={'projectFormId': project_form_id}
        )

    async def find_form_source(self, filter: dict) -> dict:
        """
        Finds form source project forms for the specified field type and criteria.
        Required scopes: forms:project_form:list
        :param filter: FormSourceProjectFormFind payload, e.g. {"projectId": ..., "formFieldTypeId": ...}
        """
        return await self._transport.request(method='POST', path='/projects/forms/find-form-source', json=filter)

    async def get_values_for_template_item(self, project_form_id: UUID) -> dict:
        """
        Retrieves template values for a project form.
        Required scopes: forms:project_form:read
        """
        return await self._transport.request(
            method='POST',
            path='/projects/forms/get-values-for-template-item',
            json={'projectFormId': project_form_id}
        )

    async def get_download_url_by_template_item(self, project_form_id: UUID, template_item_id: UUID) -> dict:
        """
        Retrieves a download URL for a project form template item.
        Required scopes: forms:project_form:read
        """
        return await self._transport.request(
            method='POST',
            path='/projects/forms/get-download-url-by-template-item',
            json={'projectFormId': project_form_id, 'templateItemId': template_item_id}
        )
