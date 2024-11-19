# <img src="./img/logo.svg"> DOCS API
![PyPI - Version](https://img.shields.io/pypi/v/sgnl-api) [![Telegram chat](https://img.shields.io/badge/Просто_о_BIM-join-blue?logo=telegram)](https://t.me/prostobim)
## Обертка над API Signal 
Официальная документация [https://api.sgnl.pro/openapi/swagger/index.html](https://api.sgnl.pro/openapi/swagger/index.html)
## Установка
```bash
pip install -U sgnl-api
```

## Пример
```python
import asyncio
import os
from sgnl_api import DocsApi
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_ID = os.getenv("SECRET_ID")


async def main():

    docs = await DocsApi.create(
        client_id=CLIENT_ID,
        client_secret=SECRET_ID
    )
    projects = await docs.project.get_list()
    for project in projects:
        print(project)


if __name__ == "__main__":
    asyncio.run(main())
```