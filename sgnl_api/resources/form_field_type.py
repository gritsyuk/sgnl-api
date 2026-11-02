from ..transport import Transport


class FormFieldType:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict = None) -> list[dict]:
        """
        Retrieves a list of form field types matching the specified filter criteria.
        Required scopes: forms:form_field_type:list
        :param filter: FormFieldTypeFind payload, e.g. {"formTypeIds": [...], "deleted": False}
        """
        return await self._transport.request(method='POST', path='/forms/fields/types', json=filter or {})
