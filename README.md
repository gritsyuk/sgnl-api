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
| Метод                   | Описание                                                         | Возвращает         |
|-------------------------|-----------------------------------------------------------------|--------------------|
| `item.get_list`         | Список файлов в директории                                       | `list[dict]`       |
| `item.count`            | Количество файлов в директории                                   | `int`              |
| `item.create_file`      | Создает новый файл с версией                                     | `UUID`             |
| `item.create_link`      | Создает новую ссылку                                             | `UUID`             |
| `item.get_link`         | Получает ссылку для загрузки файла                               | `dict`             |
| `item.add_version`      | Добавляет новую версию к существующему файлу                     | `None`             |
| `folder.get_list`       | Список дочерних папок                                            | `list[dict]`       |
| `folder.create`         | Создает новую папку                                              | `UUID`             |
| `folder.rename`         | Переименовывает папку                                            | `None`             |
| `project.root_folder`   | Информация о корневой папке проекта                              | `dict`             |
| `project.root_folder_id`| UUID корневой папки проекта                                      | `UUID`             |
| `project.get_list`      | Список проектов                                                  | `list[dict]`       |
| `project.info`          | Информация о проекте                                             | `dict`             |
| `project.users`         | Список пользователей проекта                                     | `list[dict]`       |
| `project.roles`         | Список ролей проекта                                             | `list[dict]`       |
| `project.users_permissions` | Список прав пользователя в проекте                          | `list[str]`        |
| `company.users_list`    | Список пользователей компании                                    | `list[dict]`       |
| `company.roles_list`    | Список ролей компании                                            | `list[dict]`       |
| `version.get_list`      | Список версий файла                                              | `list[dict]`       |
| `version.count`         | Количество версий файла                                          | `int`              |
| `version.create`        | Создает новую версию объекта                                     | `UUID`             |
| `file.get_object_upload`| Получает тикет на загрузку объекта                               | `dict`             |
| `file.commit_uploading` | Завершает загрузку объекта                                       | `None`             |
| `file.upload`           | Загружает файл                                                   | `dict` или `None`  |

