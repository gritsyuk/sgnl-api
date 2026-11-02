from ..transport import Transport


class FormTypeGroup:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict = None) -> list[dict]:
        """
        Retrieves a list of form type groups matching the specified filter criteria.
        Required scopes: forms:form_type_group:list
        :param filter: FormTypeGroupFind payload, e.g. {"name": "...", "deleted": False}
        """
        return await self._transport.request(method='POST', path='/forms/types/groups', json=filter or {})
