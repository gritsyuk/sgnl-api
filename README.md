# <img src="./img/logo.svg"> SIGNAL API

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
## Методы
| Методы                      | Описание                                |
|-----------------------------|-----------------------------------------|
| `Item.get_list`             | Список файлов в директории              |
| `Item.count`                | Количество файлов в директории          |
| `Item.download_link`        | Получить ссылку на скачивание           |
| `Item.create`               | Создать файл                            |
| `Item.create_link`          | Создать ссылку                          |
| `Item.new_version`          | Создать новую версию                    |
| `Folder.get_list`           | Список подкаталогов в каталоге          |
| `Folder.create`             | Создать каталог                         |          
| `Folder.update`             | Переименовать каталог                   |
| `Project.root_folder`       | Данные корневой папки проекта           |
| `Project.root_folder_id`    | UUID корневой папки                     |
| `Project.get_list`          | Список проектов                         |
| `Project.info`              | Информация о проекте                    |
| `Project.users`             | Список пользователей проекта            |
| `Project.roles`             | Список ролей проекта                    |
| `Project.users_permissions` | Права доступа у пользователя на проекте |
| `Company.users_list`        | Список пользователей компании           |
| `Company.roles_list`        | Список ролей компании                   |
| `Version.list`              | Список версий файла                     |
| `Version.count`             | Количество версий у файла               |
| `Version.new`               | Новая версия                            |
| `File.get_object_upload`    | Получение ссылки загрузки и id объекта  |
| `File.commit_uploading`     | Записать сведения в S3                  |
| `File.upload`               | Загрузка объекта полный цикл            |
