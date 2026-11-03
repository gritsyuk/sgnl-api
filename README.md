# <img src="./img/logo.svg"> SIGNAL API

![PyPI - Version](https://img.shields.io/pypi/v/sgnl-api) [![Telegram chat](https://img.shields.io/badge/Просто_о_BIM-join-blue?logo=telegram)](https://t.me/prostobim)

Официальная документация API: [swagger](https://api.sgnl.pro/openapi/swagger/index.html), [OpenAPI-схема](https://api.sgnl.pro/openapi/v1/schema.yml).

## Два пакета в одном репозитории

| Пакет | Что это | Установка | Каталог |
|---|---|---|---|
| `sgnl-api` | Асинхронная Python-обёртка над всем SIGNAL Integration API | `pip install -U sgnl-api` | `sgnl_api/` |
| `sgnl-mcp` | MCP-сервер: даёт LLM-агенту контролируемый доступ к SIGNAL — чтение без ограничений, запись только с подтверждением, удаление недоступно | `uv tool install sgnl-mcp` или Docker | [`mcp/`](mcp/README.md) |

`sgnl-mcp` построен поверх `sgnl-api` и зависит от него; `sgnl-api` ничего не знает про MCP и не тянет его зависимости. Пакеты выпускаются на PyPI независимо. Настройка MCP-сервера, подключение к Claude и запуск в Docker — в [mcp/README.md](mcp/README.md).

# sgnl-api — обёртка над API

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

    async with await DocsApi.create(
        client_id=CLIENT_ID,
        client_secret=SECRET_ID,
        scopes=["project:list"],  # ровно те scope, что включены в интеграции
    ) as docs:
        projects = await docs.project.get_list()
        for project in projects:
            print(project)


if __name__ == "__main__":
    asyncio.run(main())
```

Клиент можно использовать и без `async with` — тогда после завершения работы стоит вызвать `await docs.aclose()`, чтобы закрыть пул соединений.

## Scopes
`scopes` — обязательный параметр: список прав, с которыми запрашивается токен. Он должен совпадать с галочками в интеграции SIGNAL («Редактировать интеграцию»):

- если в списке есть scope, которого нет в интеграции, SIGNAL не выдаёт токен и не говорит, какого именно не хватает. Клиент выясняет это сам (несколько пробных запросов токена на половинах списка) и бросает `SgnlScopeError` с текстом `not enabled for the integration: docs:issue:list` и полем `missing_scopes`; scope без лицензии попадают в `unlicensed_scopes`;
- лишние галочки в интеграции не мешают: запрашивать можно любое подмножество;
- какой scope нужен методу, написано в его описании (`Required scopes: project:list`) и в [спецификации API](https://api.sgnl.pro/openapi/v1/schema.yml).

```python
# только чтение проектов и папок
scopes = ["project:list", "project:read", "docs:folder:list", "docs:item:list"]
```

Запрашивайте только то, что нужно скрипту: токен без `*:create`, `*:update` и `*:delete` ничего не изменит в SIGNAL, даже если в коде ошибка.

Почему SIGNAL не выдал токен, видно по классу исключения: `SgnlScopeError` — запрошен scope, которого нет в интеграции; `SgnlCredentialError` — неверный `client_id` или `client_secret` (после «Обновить ключ доступа» старый secret не работает); `SgnlLicenseError` — у компании нет лицензии на модуль одного из scope.

## Обработка ошибок
При ошибке API методы бросают исключение, а не возвращают `dict` с ключом `error` — проверять каждый ответ вручную не нужно.

```python
from sgnl_api import DocsApi, SgnlApiError, SgnlNotFoundError

try:
    project = await docs.project.info(project_id)
except SgnlNotFoundError:
    ...
except SgnlApiError as e:
    print(e.status_code, e.message)
```

Иерархия исключений: `SgnlApiError` (базовое) → `SgnlRequestError` (сетевые ошибки/таймауты), `SgnlAuthenticationError` (401 и отказ в токене; подклассы `SgnlScopeError`, `SgnlCredentialError`, `SgnlLicenseError`), `SgnlBadRequestError` (400), `SgnlForbiddenError` (403), `SgnlNotFoundError` (404), `SgnlQuotaExceededError` (450), `SgnlRateLimitError` (429), `SgnlServerError` (5xx).

## Лимиты запросов (429)
API ограничивает частоту запросов (около 10 запросов в секунду на `client_id`, 50 с пополнением 4 в секунду на компанию). При ответе 429 клиент сам ждёт интервал из заголовка `Retry-After` (не больше 30 с за раз) и повторяет запрос — по умолчанию до 3 раз. Если лимит не отпустил, бросается `SgnlRateLimitError` с полем `retry_after`.

```python
api = await DocsApi.create(client_id=..., client_secret=..., scopes=[...], max_retries=5)  # 0 — отключить повторы
```

Если токен отозван раньше срока, на ответ 401 клиент один раз получает новый токен и повторяет запрос.

## Загрузка файла
Документ из локального файла создаётся в три шага. Файл передаётся в хранилище потоком, поэтому большие файлы (API допускает до 5 ГиБ) не загружаются в память целиком.

```python
uploaded = await docs.file.upload(project_id, "drawings/A-101.pdf")      # {"object_id", "mime_type", "size"}
version_id = await docs.version.create(object_id=uploaded["object_id"], project_id=project_id, name="A-101.pdf")
item_id = await docs.item.create_file("A-101.pdf", folder_id, version_id)  # новый документ
# или новая версия существующего документа:
await docs.item.add_version(item_id, version_id)
```

## Свой HTTP-клиент
В `DocsApi.create` можно передать свой `httpx.AsyncClient` — например, с транспортом, который фильтрует или ограничивает запросы (так устроен `sgnl-mcp`). Такой клиент `aclose()` не закрывает: его закрывает владелец.

```python
async with httpx.AsyncClient(transport=my_transport, timeout=30) as http:
    docs = await DocsApi.create(client_id=..., client_secret=..., scopes=[...], http_client=http)
```

## Проверка покрытия API
Скрипт сравнивает [спецификацию](https://api.sgnl.pro/openapi/v1/schema.yml) с методами обёртки и показывает новые, удалённые и изменённые эндпоинты:
```bash
uv run scripts/check_api_coverage.py                       # скачать спецификацию с api.sgnl.pro
uv run scripts/check_api_coverage.py openapi/schema.yml    # или сохранённую копию из репозитория
```
Код возврата 1 означает, что обёртка вызывает эндпоинт, которого больше нет, или не передаёт обязательное поле. Копия спецификации в `openapi/schema.yml` используется и тестами `sgnl-mcp`: при обновлении API её нужно заменить.

## Разработка
Репозиторий — uv workspace из двух пакетов (`sgnl-api` в корне и `sgnl-mcp` в `mcp/`):
```bash
uv sync --all-packages                     # оба пакета и dev-зависимости
uv run pytest                              # тесты SDK
uv run --package sgnl-mcp pytest mcp/tests # тесты MCP-сервера
uv build --all-packages                    # sdist и wheel обоих пакетов в dist/
docker build -f mcp/Dockerfile -t sgnl-mcp . # образ MCP-сервера
```

## Методы
Обертка покрывает весь официальный API ([swagger](https://api.sgnl.pro/openapi/swagger/index.html)). Методы сгруппированы по ресурсам ровно как в спецификации (по тегам).

### item
| Метод                   | Описание                                                         | Возвращает         |
|-------------------------|-------------------------------------------------------------------|--------------------|
| `item.get_list`         | Список файлов в директории                                        | `list[dict]`       |
| `item.count`            | Количество файлов в директории                                    | `int`              |
| `item.search`           | Поиск вложенных элементов в директории                            | `list[dict]`       |
| `item.create_file`      | Создает новый файл с версией                                      | `UUID`             |
| `item.create_link`      | Создает элемент-ссылку на URL                                      | `UUID`             |
| `item.get_link`         | Получает ссылку для загрузки файла                                | `dict`             |
| `item.get_item_version` | Возвращает версию элемента по UUID                                | `dict`             |
| `item.add_version`      | Добавляет новую версию к существующему файлу                      | `None`             |
| `item.update`           | Обновляет элемент (имя/ссылку)                                    | `None`             |
| `item.update_version`   | Обновляет комментарий версии элемента                             | `None`             |
| `item.delete`           | Перемещает элемент в корзину                                      | `None`             |
| `item.move` | Перемещает элемент в другую папку | `None` |

### folder
| Метод                   | Описание                                                         | Возвращает         |
|-------------------------|-------------------------------------------------------------------|--------------------|
| `folder.get_list`       | Список дочерних папок                                              | `list[dict]`       |
| `folder.create`         | Создает новую папку                                                 | `UUID`             |
| `folder.update`         | Обновляет имя и/или цвет папки                                    | `None`             |
| `folder.rename`         | Переименовывает папку                                              | `None`             |
| `folder.delete`         | Перемещает папку в корзину                                        | `None`             |
| `folder.get_project_tree`| Дерево папок проекта с правами пользователя                      | `dict`             |

### project / project_user / project_user_custom_role
| Метод                   | Описание                                                         | Возвращает         |
|-------------------------|-------------------------------------------------------------------|--------------------|
| `project.root_folder`   | Информация о корневой папке проекта                                | `dict`             |
| `project.root_folder_id`| UUID корневой папки проекта                                        | `UUID`             |
| `project.get_storage_id`| UUID хранилища, назначенного проекту                               | `UUID`             |
| `project.get_list`      | Список проектов                                                     | `list[dict]`       |
| `project.info`          | Информация о проекте                                                | `dict`             |
| `project.users`         | Список пользователей проекта                                       | `list[dict]`       |
| `project.roles`         | Список ролей проекта                                                | `list[dict]`       |
| `project.users_permissions` | Права пользователя в проекте                                   | `list[str]`        |
| `project.update` | Обновляет основную информацию проекта | `None` |
| `project_user.add`      | Добавляет пользователей в проекты                                  | `None`             |
| `project_user.delete`   | Удаляет пользователей из проектов                                  | `None`             |
| `project_user_custom_role.set` | Назначает кастомные роли пользователю в проекте              | `None`             |

### company / company_user / company_user_custom_role
| Метод                   | Описание                                                         | Возвращает         |
|-------------------------|-------------------------------------------------------------------|--------------------|
| `company.users_list`    | Список пользователей компании                                      | `list[dict]`       |
| `company.roles_list`    | Список ролей компании                                               | `list[dict]`       |
| `company_user.get_id_by_telegram_id` | UUID пользователя по Telegram id                       | `UUID`             |
| `company_user.add`      | Приглашает/добавляет пользователей в компанию                      | `list[dict]`       |
| `company_user.delete`   | Удаляет пользователей из компании                                  | `None`             |
| `company_user_custom_role.set` | Назначает кастомные роли пользователю в компании              | `None`             |

### version
| Метод                   | Описание                                                         | Возвращает         |
|-------------------------|-------------------------------------------------------------------|--------------------|
| `version.get_list`      | Список версий файла                                                 | `list[dict]`       |
| `version.count`         | Количество версий файла                                            | `int`              |
| `version.find_batch`    | Версии для пакета элементов                                        | `list[dict]`       |
| `version.create`        | Создает новую версию объекта                                       | `UUID`             |

### file (Object)
| Метод                   | Описание                                                         | Возвращает         |
|-------------------------|-------------------------------------------------------------------|--------------------|
| `file.get_object_upload`| Получает тикет на загрузку объекта                                | `dict`             |
| `file.commit_uploading` | Завершает загрузку объекта                                        | `None`             |
| `file.upload`           | Загружает файл потоком (тикет, передача в хранилище, commit)      | `dict` (`object_id`, `mime_type`, `size`) |

### attribute / attribute_type / attribute_value
| Метод                            | Описание                                              | Возвращает   |
|-----------------------------------|--------------------------------------------------------|--------------|
| `attribute.get_list`              | Список атрибутов по фильтру                             | `list[dict]` |
| `attribute_type.get_list`         | Список типов атрибутов по фильтру                       | `list[dict]` |
| `attribute_type.create` | Создает тип атрибута | `UUID` |
| `attribute_type.update` | Обновляет типы атрибутов (до 50) | `None` |
| `attribute_type_list_items.create` | Добавляет значения в атрибут-список | `None` |
| `attribute_type_list_items.update` | Обновляет значения атрибута-списка | `None` |
| `attribute_value.list_issues`     | Значения атрибутов замечаний                             | `list[dict]` |
| `attribute_value.list_items`      | Значения атрибутов элементов                             | `list[dict]` |
| `attribute_value.list_folders`    | Значения атрибутов папок                                 | `list[dict]` |
| `attribute_value.set`             | Устанавливает значения атрибутов                         | `None`       |

### issue и связанные (issue_type, issue_accesses, issue_comment, issue_attachment, issue_events, issue_project_settings)
| Метод                                    | Описание                                          | Возвращает   |
|--------------------------------------------|------------------------------------------------------|--------------|
| `issue.get_list`                          | Список замечаний по фильтру                          | `list[dict]` |
| `issue.create` | Создает замечание | `UUID` |
| `issue.update`                            | Пакетное обновление замечаний (до 25 шт.)             | `None`       |
| `issue.count`                             | Количество замечаний по фильтру                       | `int`        |
| `issue.item_issues_count`                 | Количество замечаний по элементам                     | `list[dict]` |
| `issue_type.get_list`                     | Список типов замечаний                                | `list[dict]` |
| `issue_accesses.get_list`                 | Правила доступа к замечаниям                          | `list[dict]` |
| `issue_comment.get_list`                  | Список комментариев замечания                         | `list[dict]` |
| `issue_comment.create`                    | Создает комментарий                                    | `UUID`       |
| `issue_comment.count`                     | Количество комментариев                                | `int`        |
| `issue_attachment.get_list`               | Список вложений замечания                              | `list[dict]` |
| `issue_attachment.download_object`        | Тикет на загрузку вложения                             | `dict`       |
| `issue_events.get_list`                   | История событий замечания                             | `list[dict]` |
| `issue_events.count`                      | Количество событий                                     | `int`        |
| `issue_project_settings.get`              | Настройки замечаний проекта                            | `dict`       |

### review и связанные (review_group, review_item, review_type, review_process)
| Метод                                                   | Описание                                     | Возвращает   |
|------------------------------------------------------------|--------------------------------------------------|--------------|
| `review.get_list`                                         | Список согласований проекта                       | `list[dict]` |
| `review.update`                                            | Обновляет основную информацию согласования         | `None`       |
| `review.count`                                             | Количество согласований                            | `int`        |
| `review.get_versions`                                      | Версии согласований по id                          | `list[dict]` |
| `review.find_item_version_ids_by_review_version_ids`       | Версии элементов по версиям согласования           | `dict`       |
| `review.create` | Создает согласование | `UUID` |
| `review.set_comment` | Устанавливает/очищает комментарий последней версии | `None` |
| `review.set_type` | Меняет тип согласования | `None` |
| `review_type.get_names` | Названия типов согласования проекта | `list[dict]` |
| `review_process.start` | Запускает процесс согласования | `None` |
| `review_group.get_list`                                    | Список групп согласований                          | `list[dict]` |
| `review_item.get_statuses`                                 | Статусы согласования для версий элементов          | `list[dict]` |
| `review_item.add` | Добавляет версию элемента в согласование | `None` |
| `review_item.remove` | Удаляет версию элемента из согласования | `None` |

### share / storage
| Метод              | Описание                                    | Возвращает   |
|---------------------|--------------------------------------------|--------------|
| `share.get_list`   | Список ссылок общего доступа по фильтру      | `list[dict]` |
| `share.create`     | Создает ссылку общего доступа                | `UUID`       |
| `share.update`     | Обновляет ссылку общего доступа              | `None`       |
| `share.delete`     | Помечает ссылку удаленной/восстановленной    | `None`       |
| `share.count`      | Количество ссылок по фильтру                 | `int`        |
| `storage.get_list` | Список хранилищ документов                   | `list[dict]` |

### подписание (cades_signature, embedded_signature, mchd) и card_public_link
| Метод                                | Описание                                        | Возвращает   |
|----------------------------------------|------------------------------------------------------|--------------|
| `cades_signature.get_list`            | Список подписей CAdES версии                          | `list[dict]` |
| `cades_signature.create`              | Создает подпись CAdES                                  | `None`       |
| `embedded_signature.get_list`         | Список встроенных подписей элемента                    | `list[dict]` |
| `embedded_signature.create`           | Создает встроенную подпись                             | `None`       |
| `mchd.company_documents`              | UUID доверенностей компании                            | `list[UUID]` |
| `mchd.attached_documents`             | Доверенности, привязанные к подписи                    | `list[dict]` |
| `mchd.download`                       | Тикет на загрузку доверенности                         | `dict`       |
| `card_public_link.regenerate`         | Перегенерирует публичную ссылку карточки дашборда       | `dict`       |

### documents_transfer / documents_transfer_item / documents_transfer_type / documents_transfer_acceptance / acceptance_certificate
| Метод                                          | Описание                                       | Возвращает   |
|---------------------------------------------------|-----------------------------------------------------|--------------|
| `documents_transfer.get_list`                     | Список передач документов по фильтру                 | `list[dict]` |
| `documents_transfer.get`                          | Данные передачи документов по id                     | `dict`       |
| `documents_transfer.count`                        | Количество передач по фильтру                        | `int`        |
| `documents_transfer.accesses`                     | Правила доступа для типов передач                    | `list[dict]` |
| `documents_transfer.create` | Создает передачу документов | `UUID` |
| `documents_transfer_item.get_list`                | Список элементов передачи                            | `list[dict]` |
| `documents_transfer_item.count`                   | Количество элементов передачи                        | `int`        |
| `documents_transfer_item.download`                | Тикет на загрузку элемента передачи                  | `dict`       |
| `documents_transfer_item.add` | Добавляет версии элементов в передачу | `None` |
| `documents_transfer_type.get_list`                | Список типов передач документов                      | `list[dict]` |
| `acceptance_certificate.download`                 | Тикет на загрузку акта приема-передачи               | `dict`       |
| `acceptance_certificate.attach` | Прикрепляет акт приема-передачи к передаче | `UUID` |
| `documents_transfer_acceptance.send` | Отправляет подготовленную передачу получателю | `None` |

### permissions / application_user
| Метод                          | Описание                                        | Возвращает   |
|----------------------------------|------------------------------------------------------|--------------|
| `permissions.upsert_batch`      | Устанавливает права пользователей/ролей на папку       | `None`       |
| `permissions.get_tree`          | Дерево папок проекта с правами                         | `dict`       |
| `permissions.delete` | Удаляет конкретное право | `None` |
| `application_user.upsert`       | Назначает роли пользователям в приложениях              | `None`       |
| `application_user.delete`       | Отзывает доступ пользователей в приложениях             | `None`       |

### forge / tangl / folder_items_naming_pattern
| Метод                                        | Описание                                    | Возвращает   |
|-------------------------------------------------|--------------------------------------------------|--------------|
| `forge.convert`                                | Запускает конвертацию модели через Forge           | `None`       |
| `forge.get_viewers_data`                       | Токен и URN для Forge Viewer                       | `dict`       |
| `tangl.convert`                                | Запускает конвертацию модели через Tangl           | `None`       |
| `folder_items_naming_pattern.find`             | Шаблоны именования файлов папки                    | `dict`       |

### формы (project_form, project_form_type, project_form_field_type, form_type, form_type_group, form_field_type)
| Метод | Описание | Возвращает |
|---|---|---|
| `project_form.get_list` | Список форм проекта (фильтр + сортировка) | `dict` |
| `project_form.count` | Количество форм по фильтру | `int` |
| `project_form.get` | Форма по id | `dict` |
| `project_form.get_summary` | Сводка по формам | `list[dict]` |
| `project_form.create_batch` | Создает формы пачкой (до 200) | `list[UUID]` |
| `project_form.update` | Обновляет поля формы | `None` |
| `project_form.complete` | Завершает форму | `None` |
| `project_form.find_form_source` | Формы-источники для поля | `dict` |
| `project_form.get_values_for_template_item` | Значения для шаблона | `dict` |
| `project_form.get_download_url_by_template_item` | Ссылка на скачивание по шаблону | `dict` |
| `project_form_type.get_list` | Типы форм проекта | `list[dict]` |
| `project_form_field_type.get_list` | Типы полей формы проекта | `dict` |
| `form_type.get_list` | Типы форм | `list[dict]` |
| `form_type_group.get_list` | Группы типов форм | `list[dict]` |
| `form_field_type.get_list` | Типы полей форм | `list[dict]` |

### дашборды (board, card, card_group)
| Метод | Описание | Возвращает |
|---|---|---|
| `board.get_list` | Дашборды проекта | `list[dict]` |
| `card_group.get_list` | Группы карточек дашборда (тег `Group` в API) | `list[dict]` |
| `card.get_list` | Карточки дашборда | `list[dict]` |
| `card.get` | Карточка с содержимым | `dict` |

### бронирования и слоты (booking, slot)
| Метод | Описание | Возвращает |
|---|---|---|
| `booking.get_list` | Бронирования компании (курсорная пагинация) | `list[dict]` |
| `booking.create_batch` | Создает бронирования пачкой (до 200) | `list[dict]` |
| `booking.delete_batch` | Удаляет бронирования | `None` |
| `slot.get_list` | Слоты компании (курсорная пагинация) | `list[dict]` |
| `slot.create_batch` | Создает слоты пачкой (до 200) | `list[dict]` |
| `slot.delete_batch` | Удаляет слоты | `None` |

### user_log
| Метод              | Описание                              | Возвращает   |
|---------------------|--------------------------------------|--------------|
| `user_log.get_list`| Журнал действий пользователей          | `list[dict]` |

Для методов, принимающих `filter`/`find`/`values`/`items` как `dict`, структура соответствует одноимённой схеме в [спецификации API](https://api.sgnl.pro/openapi/swagger/index.html) — ключи передаются в camelCase, как в JSON-теле запроса (например `{"projectId": "...", "issueIds": [...]}`).

