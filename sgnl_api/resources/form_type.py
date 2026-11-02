from ..transport import Transport


class FormType:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict = None) -> list[dict]:
        """
        Retrieves a list of form types matching the specified filter criteria.
        Required scopes: forms:form_type:list
        :param filter: FormTypeFind payload, e.g. {"formTypeGroupIds": [...], "deleted": False}
        """
        return await self._transport.request(method='POST', path='/forms/types', json=filter or {})
