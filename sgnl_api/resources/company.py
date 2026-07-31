from ..transport import Transport


class Company:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def users_list(self, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Required scopes: company:user:list
        :param take: The number of items to return. Default value is 100. Maximum value is 200.
        :param skip: The number of items to skip. Default value is 0.
        :return: Returns a list of users associated with a company.
        """
        return await self._transport.request(
            method='GET',
            path='/company/users',
            params={
                'Take': take,
                'Skip': skip
            }
        )

    async def roles_list(self, take: int = 100, skip: int = 0) -> list[dict]:
        """
        Required scopes: company:role:list
        :param take: The number of items to return. Default value is 100. Maximum value is 200.
        :param skip: The number of items to skip. Default value is 0.
        :return: Returns a list of roles associated with a company.
        """
        return await self._transport.request(
            method='GET',
            path='/company/roles',
            params={
                'Take': take,
                'Skip': skip
            }
        )
