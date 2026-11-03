# sgnl-mcp — MCP-сервер для SIGNAL

Подключает SIGNAL к ИИ-ассистенту: Claude Desktop, Claude Code, Codex и другим клиентам с поддержкой MCP. Ассистенту можно писать обычным языком: «покажи проекты», «найди в проекте Школа документы АР в PDF», «какие замечания по этому документу ещё открыты».

Что ассистент может делать, зависит от профиля:

| Профиль | Что доступно |
|---|---|
| `read` (по умолчанию) | Только чтение: проекты, папки, документы и их версии, ссылки на скачивание, замечания, передачи, рассмотрения, подписи |
| `write` | Чтение и изменения: загрузка документов и новых версий, правка замечаний, создание передач и рассмотрений. Каждое изменение выполняется только после вашего согласия |
| `workflow` | Всё из `write`, а также отправка передач и запуск рассмотрений. Каждое такое действие подтверждается в отдельном диалоге |

Удалять, перемещать и переименовывать документы и папки, а также менять права доступа ассистент не может ни в одном профиле.

## Содержание

- [Что понадобится](#что-понадобится)
- [Способ 1. Через uvx](#способ-1-через-uvx)
- [Способ 2. Через Docker](#способ-2-через-docker)
- [Проверка](#проверка)
- [Профили write и workflow](#профили-write-и-workflow)
- [Обновление](#обновление)
- [Если что-то не работает](#если-что-то-не-работает)
- [Для администратора SIGNAL](#для-администратора-signal)
- [Все настройки](#все-настройки)
- [Что умеет ассистент](#что-умеет-ассистент)

## Что понадобится

1. **Ключ SIGNAL**: `client_id` и `client_secret` интеграции. Их выдаёт администратор SIGNAL вашей компании; что ему нужно сделать, описано в разделе [Для администратора SIGNAL](#для-администратора-signal). Scope и другие технические детали вам знать не нужно.
2. **Клиент с поддержкой MCP**: Claude Desktop, Claude Code или Codex (CLI, расширение для IDE или десктопное приложение). ChatGPT в браузере и облачный Codex к этому серверу не подключаются: им нужен сервер в интернете, а этот работает на вашем компьютере.
3. **Один из двух способов запуска:**

| | uvx | Docker |
|---|---|---|
| Что установить | `uv`, небольшую утилиту | Docker Desktop |
| Подходит, если | Docker не установлен или не нужен | Docker уже установлен, нужна дополнительная изоляция |
| Доступ к файлам компьютера | как у вашей учётной записи; для загрузки только папка из настроек | только к одной папке, которую вы подключите |
| Где хранить ключ | в настройках клиента | в отдельном файле |

Оба способа запускают один и тот же сервер, и работает он одинаково. Можно установить оба и переключаться между ними.

Ниже `0.2.1` — текущая версия. Номер последней версии можно посмотреть на [PyPI](https://pypi.org/project/sgnl-mcp/).

## Способ 1. Через uvx

### Шаг 1. Установите uv

**Windows**, в PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS и Linux**, в терминале:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Закройте терминал, откройте его снова и узнайте полный путь к `uvx`. Он понадобится в настройках клиента.

```powershell
where.exe uvx      # Windows, обычно C:\Users\<имя>\.local\bin\uvx.exe
```

```bash
which uvx          # macOS и Linux, обычно /Users/<имя>/.local/bin/uvx
```

Python отдельно ставить не нужно: если его нет, `uv` скачает его сам.

### Шаг 2. Проверьте ключ

**Windows (PowerShell):**

```powershell
$env:SGNL_CLIENT_ID="ваш client_id"
$env:SGNL_CLIENT_SECRET="ваш client_secret"
uvx sgnl-mcp@0.2.1
```

**macOS и Linux:**

```bash
SGNL_CLIENT_ID="ваш client_id" SGNL_CLIENT_SECRET="ваш client_secret" uvx sgnl-mcp@0.2.1
```

Первый запуск длится 10–20 секунд: скачиваются пакеты. Возможны три результата:

- **Курсор мигает, сообщений нет.** Всё в порядке: сервер подключился к SIGNAL и ждёт клиента. Остановите его через Ctrl+C.
- **`started with limited rights`.** Сервер работает, но части операций ключу не хватает прав. В сообщении указано, что передать администратору. Пользоваться можно и так.
- **`cannot start` или `invalid configuration`.** Ключ неверный или не задан, см. раздел [Если что-то не работает](#если-что-то-не-работает).

### Шаг 3. Подключите к клиенту

**Claude Desktop.** Откройте файл настроек:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Добавьте в него блок `sgnl`. Если в файле уже есть `"mcpServers"`, добавьте только сам блок `"sgnl": {…}` рядом с остальными серверами.

```json
{
  "mcpServers": {
    "sgnl": {
      "command": "C:\\Users\\Admin\\.local\\bin\\uvx.exe",
      "args": ["sgnl-mcp@0.2.1"],
      "env": {
        "SGNL_CLIENT_ID": "ваш client_id",
        "SGNL_CLIENT_SECRET": "ваш client_secret",
        "SGNL_MCP_PROFILE": "read"
      }
    }
  }
}
```

В `command` укажите путь из шага 1. В Windows обратные слеши удваиваются (`\\`), на macOS путь пишется как есть: `/Users/me/.local/bin/uvx`. Затем полностью закройте Claude Desktop (на Windows через значок в трее → Quit) и запустите снова.

**Claude Code:**

```bash
claude mcp add sgnl -e SGNL_CLIENT_ID=ваш_client_id -e SGNL_CLIENT_SECRET=ваш_client_secret -- uvx sgnl-mcp@0.2.1
```

**Codex.** Файл `~/.codex/config.toml`, на Windows это `%USERPROFILE%\.codex\config.toml`:

```toml
[mcp_servers.sgnl]
command = "uvx"
args = ["sgnl-mcp@0.2.1"]
env = { SGNL_CLIENT_ID = "ваш client_id", SGNL_CLIENT_SECRET = "ваш client_secret" }
startup_timeout_sec = 30
```

Журнал действий ассистента хранится в папке `.sgnl-mcp` в домашнем каталоге, файл `audit.jsonl`.

## Способ 2. Через Docker

### Шаг 1. Установите Docker Desktop и скачайте образ

Скачайте Docker Desktop с [docker.com](https://www.docker.com/products/docker-desktop/), установите и запустите. Затем выполните:

```bash
docker pull ghcr.io/gritsyuk/sgnl-mcp:0.2.1
```

Образ подходит для Windows, Linux и Mac с процессорами Intel и Apple.

### Шаг 2. Сохраните ключ в файл

Создайте текстовый файл, например `C:\Users\Admin\sgnl-mcp.env` (Windows) или `~/sgnl-mcp.env` (macOS, Linux):

```
SGNL_CLIENT_ID=ваш client_id
SGNL_CLIENT_SECRET=ваш client_secret
SGNL_MCP_PROFILE=read
```

Кавычки и пробелы вокруг `=` не нужны.

### Шаг 3. Проверьте ключ

**Windows (cmd или PowerShell):**

```powershell
docker run -i --rm --init --env-file C:\Users\Admin\sgnl-mcp.env ghcr.io/gritsyuk/sgnl-mcp:0.2.1
```

**macOS и Linux:**

```bash
docker run -i --rm --init --env-file ~/sgnl-mcp.env ghcr.io/gritsyuk/sgnl-mcp:0.2.1
```

Результаты те же, что для uvx: если курсор мигает без сообщений, всё в порядке. Остановите сервер через Ctrl+C.

### Шаг 4. Подключите к клиенту

**Claude Desktop** (где лежит файл настроек, см. [способ 1](#шаг-3-подключите-к-клиенту)):

```json
{
  "mcpServers": {
    "sgnl": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--init",
        "--read-only", "--tmpfs", "/tmp",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--env-file", "C:\\Users\\Admin\\sgnl-mcp.env",
        "-v", "sgnl-mcp-data:/data",
        "ghcr.io/gritsyuk/sgnl-mcp:0.2.1"
      ]
    }
  }
}
```

На macOS и Linux в `--env-file` укажите полный путь без `~`, например `/Users/me/sgnl-mcp.env`. После изменения полностью перезапустите Claude Desktop.

**Claude Code:**

```bash
claude mcp add sgnl -- docker run -i --rm --init --read-only --tmpfs /tmp --cap-drop ALL \
  --security-opt no-new-privileges --env-file ~/sgnl-mcp.env -v sgnl-mcp-data:/data \
  ghcr.io/gritsyuk/sgnl-mcp:0.2.1
```

**Codex** (`~/.codex/config.toml`):

```toml
[mcp_servers.sgnl]
command = "docker"
args = [
  "run", "-i", "--rm", "--init", "--read-only", "--tmpfs", "/tmp",
  "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
  "--env-file", "C:\\Users\\Admin\\sgnl-mcp.env",
  "-v", "sgnl-mcp-data:/data",
  "ghcr.io/gritsyuk/sgnl-mcp:0.2.1",
]
startup_timeout_sec = 30
```

Что значат параметры запуска:

| Параметр | Зачем |
|---|---|
| `-i --rm --init` | клиент общается с сервером через контейнер и удаляет контейнер после закрытия |
| `--read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges` | контейнер ничего не может изменить в себе и не получает лишних прав |
| `--env-file …` | откуда взять ключ |
| `-v sgnl-mcp-data:/data` | где хранить журнал действий ассистента между запусками |

Журнал действий хранится в томе Docker `sgnl-mcp-data`, файл `audit.jsonl`.

## Проверка

Напишите ассистенту: «Подключён ли SIGNAL? Покажи список проектов».

- Ассистент вызовет `get_access_status` и `list_projects` и покажет проекты, доступные вашему ключу.
- Если ключу чего-то не хватает, ассистент скажет об этом и приведёт готовый текст для администратора.

Claude Desktop запускает сервер дважды: для обычного чата и для режимов Cowork и Code. Поэтому в Docker Desktop видно два контейнера, а в Диспетчере задач два процесса. Это нормально.

## Профили write и workflow

Для изменений в SIGNAL нужны ещё три настройки. Для uvx они добавляются в `env`, для Docker в env-файл.

```
SGNL_MCP_PROFILE=write
SGNL_MCP_ACTOR_USER_ID=<ID пользователя SIGNAL, от имени которого вносятся изменения>
SGNL_MCP_UPLOAD_ROOT=<папка с файлами, которые ассистенту можно загружать>
```

- `SGNL_MCP_ACTOR_USER_ID`: ID пользователя SIGNAL. Обычно это служебная учётная запись, например «AI-агент»; её ID даёт администратор SIGNAL.
- `SGNL_MCP_UPLOAD_ROOT`: файлы вне этой папки ассистент загрузить не может.
- **Docker:** `SGNL_MCP_UPLOAD_ROOT` не задавайте, а подключите папку параметром перед именем образа, только для чтения:
  ```json
  "-v", "C:\\SIGNAL\\outgoing:/uploads:ro",
  ```

Как проходит изменение:
1. Ассистент показывает, что именно изменится: «было → станет», путь папки, состав передачи.
2. Изменение выполняется только после вашего согласия в чате.
3. Отправку передачи и запуск рассмотрения (профиль `workflow`) вы дополнительно подтверждаете в отдельном диалоге клиента.

В настройках клиента не включайте «разрешить всегда» для инструментов записи: пусть клиент спрашивает перед каждым изменением.

## Обновление

Замените номер версии в настройках клиента, например `0.2.1` → `0.3.0`, и перезапустите клиент.

- **uvx:** новая версия скачается сама при первом запуске.
- **Docker:** сначала скачайте образ: `docker pull ghcr.io/gritsyuk/sgnl-mcp:0.3.0`.

Указывайте конкретную версию, а не `latest`: тогда сервер не обновится без вашего ведома.

## Если что-то не работает

Журнал запуска сервера в Claude Desktop:
- Windows: `%APPDATA%\Claude\logs\mcp-server-sgnl.log`
- macOS: `~/Library/Logs/Claude/mcp-server-sgnl.log`

| Сообщение | Что сделать |
|---|---|
| `invalid configuration … SGNL_CLIENT_ID is not set` | Ключ не передан. Проверьте блок `env` (uvx) или содержимое env-файла (Docker) |
| `cannot start … CredentialError` или `invalid client id or client secret` | Неверный ключ. Если администратор нажимал «Обновить ключ доступа», старый `client_secret` больше не работает: запросите новый |
| `cannot start … no license` или в интеграции нет нужных прав | Перешлите текст ошибки администратору SIGNAL |
| `started with limited rights` | Сервер работает, но не всё доступно. Перешлите текст из сообщения администратору SIGNAL |
| `spawn uvx ENOENT` или «не удаётся найти файл» | Клиент не нашёл `uvx`. Укажите в `command` полный путь из шага 1 |
| `--env-file: open …: The system cannot find the file specified` | Неверный путь к env-файлу в настройках |
| `Unable to find image` и долгий первый запуск | Docker скачивает образ, подождите. Чтобы не ждать, заранее выполните `docker pull` |
| `Cannot connect to the Docker daemon` | Docker Desktop не запущен |
| Сервер не отвечает в Codex | Увеличьте `startup_timeout_sec` до 60 |

Если ассистент отвечает, что ключу не хватает прав (`SCOPE_MISSING`), перешлите его сообщение администратору SIGNAL: в нём уже указано, какие права нужно добавить. После этого перезапустите клиент.

## Для администратора SIGNAL

Чтобы выдать сотруднику ключ, создайте интеграцию в SIGNAL («Редактировать интеграцию»):

1. **Название**: например, `MCP_READ` или `MCP_<сотрудник>`.
2. **scopes**: отметьте права профиля из таблицы ниже.
3. **Проект**: только проекты, с которыми сотрудник должен работать через ассистента.
4. **Действительно до**: для ключей с правами на запись лучше ставить короткий срок.

Передайте сотруднику `client_id` и `client_secret`. «Обновить ключ доступа» выпускает новый `client_secret`, старый перестаёт работать.

| Профиль | Права (scopes) интеграции |
|---|---|
| `read` | `project:list`, `project:read`, `docs:folder:read`, `docs:item:list`, `docs:item:read`, `docs:version:list`, `docs:docs_transfer:list`, `docs:docs_transfer:read`, `docs:issue:list`, `docs:review:list`, `docs:signing:list`, `docs:attribute:list` |
| `write`, `workflow` | всё из `read`, а также `company:user:list`, `docs:object:create`, `docs:version:create`, `docs:version:update`, `docs:item:create`, `docs:docs_transfer:create`, `docs:docs_transfer:update`, `docs:issue:update`, `docs:review:create`, `docs:review:update` |

Обратите внимание на похожие названия: нужен `docs:issue:list`, а не `docs:issue:read`.

Если каких-то прав из списка нет, сервер всё равно работает, но соответствующие операции недоступны. Сотрудник получит сообщение с перечнем недостающих прав. Права на удаление (`*:delete`), управление доступом (`docs:permissions:*`) и пользователями сервер не использует: выдавать их не нужно.

Для профилей `write` и `workflow` заведите служебного пользователя (например, «AI-агент») и сообщите сотруднику его ID. От его имени будут вноситься изменения.

## Все настройки

| Переменная | Обязательна | По умолчанию | Назначение |
|---|---|---|---|
| `SGNL_CLIENT_ID` | да | — | `client_id` интеграции SIGNAL |
| `SGNL_CLIENT_SECRET` | да | — | `client_secret` интеграции SIGNAL |
| `SGNL_MCP_PROFILE` | нет | `read` | `read`, `write` или `workflow` |
| `SGNL_MCP_ACTOR_USER_ID` | для `write`/`workflow` | — | ID пользователя SIGNAL, от имени которого вносятся изменения |
| `SGNL_MCP_UPLOAD_ROOT` | для `write`/`workflow` | в Docker: `/uploads` | Папка, из которой можно загружать файлы |
| `SGNL_MCP_ALLOWED_EXTENSIONS` | нет | `.pdf,.dwg,.dxf,…` | Разрешённые типы загружаемых файлов, через запятую |
| `SGNL_MCP_AUTO_CONFIRM` | нет | — | Инструменты записи, которые выполняются без предпросмотра. Используйте только в доверенных сценариях |
| `SGNL_MCP_RATE_PER_SEC` | нет | `3` | Сколько запросов в секунду сервер отправляет в SIGNAL (не больше 10) |
| `SGNL_MCP_BURST` | нет | `6` | Запас запросов для коротких всплесков |
| `SGNL_MCP_MAX_CONCURRENCY` | нет | `4` | Сколько запросов к SIGNAL выполняется одновременно |
| `SGNL_MCP_TOOL_TIMEOUT` | нет | `30` | Сколько секунд ждать ответа на одну операцию |
| `SGNL_MCP_UPLOAD_TIMEOUT` | нет | `600` | Сколько секунд ждать загрузки файла |
| `SGNL_MCP_CONFIRMATION_TTL_SEC` | нет | `300` | Сколько секунд действует предпросмотр изменения |
| `SGNL_MCP_AUDIT_PATH` | нет | `~/.sgnl-mcp/audit.jsonl`, в Docker `/data/audit.jsonl` | Журнал действий ассистента |
| `SGNL_MCP_STATE_PATH` | нет | `~/.sgnl-mcp/state.sqlite`, в Docker `/data/state.sqlite` | Журнал выполненных операций, защищает от повторного выполнения |

## Что умеет ассистент

| Инструмент | Профиль | Что делает |
|---|---|---|
| `get_access_status` | read | Что доступно ключу и чего не хватает |
| `list_projects` | read | Список проектов |
| `get_project` | read | Данные проекта |
| `get_project_folder_tree` | read | Дерево папок с правами пользователя |
| `search_documents` | read | Поиск документов по имени, расширению, автору, датам |
| `list_folder_documents` | read | Документы одной папки |
| `list_document_versions` | read | История версий документа |
| `get_document_version` | read | Какой документ и какой файл связаны с версией |
| `get_document_download_url` | read | Временная ссылка на скачивание версии |
| `get_document_context` | read | Всё о документе за один запрос: версии, атрибуты, замечания, рассмотрения, подписи |
| `list_document_transfers` | read | Передачи проекта |
| `get_document_transfer` | read | Данные передачи |
| `list_transfer_documents` | read | Документы в передаче |
| `list_document_transfer_types` | read | Типы передач |
| `list_issues` | read | Замечания |
| `list_reviews` | read | Рассмотрения |
| `get_review_details` | read | Версии рассмотрения и документы в них |
| `get_document_review_status` | read | Статус рассмотрения документов |
| `list_review_types` | read | Типы рассмотрений |
| `upload_document` | write | Новый документ из файла |
| `add_document_version` | write | Новая версия документа |
| `update_document_version_comment` | write | Комментарий к версии |
| `create_document_transfer` | write | Новая передача (черновик) |
| `add_documents_to_transfer` | write | Добавить документы в передачу |
| `update_issues` | write | Изменить до 25 замечаний |
| `create_review` | write | Новое рассмотрение (черновик) |
| `add_documents_to_review` | write | Добавить до 20 документов в рассмотрение |
| `prepare_send_document_transfer` | workflow | Проверить передачу перед отправкой |
| `send_document_transfer` | workflow | Отправить передачу |
| `prepare_start_review` | workflow | Проверить рассмотрение перед запуском |
| `start_review` | workflow | Запустить рассмотрение |

Чего ассистент не делает: не создаёт замечания; не удаляет, не перемещает и не переименовывает документы и папки; не меняет права и пользователей. Найти передачи по конкретному документу нельзя: такой возможности нет в API SIGNAL.

Нагрузка на SIGNAL ограничена: по умолчанию не больше 3 запросов в секунду, справочники запоминаются на 5 минут.
