# TG Sieve Filter

Сервис слушает Telegram-группу с заявками на почтовые фильтры, распознаёт сообщения вида `NEW ... to imap://...`, строит Sieve-правило и при безопасных условиях обновляет активный `postfilter` в Mailcow. Telegram-слой уже подготовлен под `aiogram 3` через `routers + handlers`, чтобы дальше было проще наращивать личные команды и служебные сценарии.

## Что умеет

- aiogram 3 polling с `routers/handlers`
- безопасный флаг пропуска старых pending updates на первом старте
- разбор заявок на один адрес, несколько адресов или весь домен
- offline-разбор Telegram transcript export для регрессионных тестов
- нормализация `imap://user@host/folder/path`
- опциональная IMAP-проверка существования папки
- защита от дублей и конфликтов по домену
- запись в `mailcow.sieve_filters.script_data` для `filter_type=postfilter`
- `dry-run` через `AUTO_APPLY=false`

## Поддерживаемые шаблоны сообщений

- `New inbox@sample-registry.example to imap://info%40global-it.com.ua@mail.global-it.com.ua/OFFSHORE/+Vendors/UNITED_KINGDOM/Sample_Registry`
- `NEW от @samplebank.example в папку imap://post@mail/OFFSHORE/+Banks/SAMPLE_BANK`
- `NEW (a@x.com), (b@x.com) imap://info%40global-it.com.ua@mail.global-it.com.ua/OFFSHORE/+Folder`
- `New user@domain.tld и любые адреса с @domain.tld to imap://...`

Если в тексте есть явный запрос на весь домен, сервис строит доменное правило. Если домен уже используется в другом правиле, заявка помечается как конфликтная и в Mailcow не пишется.

## Mailcow storage

По умолчанию используется `FILTER_STORAGE_BACKEND=mailcow_db`.

Сервис читает и обновляет запись в таблице `sieve_filters` по связке:

- `username=MAILCOW_FILTER_USERNAME`
- `filter_type=MAILCOW_FILTER_TYPE`
- `script_name=MAILCOW_FILTER_NAME`

Если активной записи ещё нет, сервис создаёт новую с `script_name` и `script_desc` из `.env`.
Для актуальной схемы Mailcow `MAILCOW_FILTER_NAME` обычно должен быть `active`.

`/api/v1/edit/user-acl` для этой задачи не подходит: это ACL endpoint, а не редактирование содержимого Sieve-фильтров.

## Запуск локально

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
Copy-Item .env.example .env
```

Настройте `.env`, затем:

```powershell
python -m app.bot
```

## Тесты

```powershell
python -m pytest backend\tests
```

Если у вас есть большой экспорт чата, его можно положить как fixture и гонять парсер по реальным формулировкам. Базовый обезличенный пример уже есть в [`backend/tests/fixtures/chat_sample.txt`](</E:/Devel/tg-sieve-filter/backend/tests/fixtures/chat_sample.txt:1>).

Telegram Desktop JSON export (`result.json`) тоже поддержан. Локальные regression tests для него находятся в [`backend/tests/test_export_json.py`](</E:/Devel/tg-sieve-filter/backend/tests/test_export_json.py:1>), а загрузчик экспорта в [`backend/app/telegram/export_json.py`](</E:/Devel/tg-sieve-filter/backend/app/telegram/export_json.py:1>).

## Docker

Изолированный запуск:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose logs -f tgz-filter
```

Контейнер стартует listener командой `python -m app.bot` и хранит локальный state в volume `./data`.

## Deploy Near Mailcow

Если бот запускается на том же хосте, где работает Mailcow, удобнее использовать [`docker-compose.deploy.yml`](</E:/Devel/tg-sieve-filter/docker-compose.deploy.yml:1>) и отдельный [` .env.deploy.example`](</E:/Devel/tg-sieve-filter/.env.deploy.example:1>) как основу для production `.env`.

Идея такая:

- контейнер не публикует наружу никакие порты;
- контейнер подключается только к внешней Docker network Mailcow;
- root внутри контейнера не используется;
- файловая система контейнера работает в `read_only`, кроме volume `./data`;
- Linux capabilities сброшены через `cap_drop: [ALL]`.

Пример запуска:

```bash
cp .env.deploy.example .env
docker login ghcr.io
docker compose -f docker-compose.deploy.yml up -d
```

### Как узнать имя Mailcow network

На сервере с Mailcow:

```bash
docker network ls | grep mailcow
```

И подставьте найденное имя в:

```env
MAILCOW_DOCKER_NETWORK=mailcowdockerized_mailcow-network
```

### Что лучше для безопасности

Самый безопасный вариант — не использовать для бота "сильного" DB-пользователя Mailcow.
Лучше создать отдельного MariaDB/MySQL пользователя только с нужными правами на таблицу `sieve_filters`.

Минимально разумные права для текущей логики:

- `SELECT`
- `INSERT`
- `UPDATE`

Если у вас есть возможность выдать права только на таблицу `mailcow.sieve_filters`, это лучше, чем давать доступ ко всей базе.

### Как посмотреть реальную структуру `sieve_filters` в своей Mailcow

На хосте Mailcow можно зайти в MariaDB контейнер и выполнить:

```bash
docker exec -it mysql-mailcow mysql -u root -p mailcow
```

А внутри MariaDB:

```sql
SHOW CREATE TABLE sieve_filters\G
DESCRIBE sieve_filters;

SELECT id, username, filter_type, script_name, script_desc
FROM sieve_filters
ORDER BY id DESC
LIMIT 20;

SELECT id, username, filter_type, script_name, script_desc, LENGTH(script_data) AS script_size
FROM sieve_filters
WHERE username = 'info@nexus.ua'
  AND filter_type = 'postfilter'
ORDER BY id DESC;
```

Если имя MariaDB контейнера у вас другое, сначала можно проверить:

```bash
docker ps --format '{{.Names}}' | grep mailcow
```

## GitHub Actions

В репозитории уже подготовлены два workflow:

- `.github/workflows/ci.yml`:
  запускает тесты и проверяет `docker build` на `push` и `pull_request`
- `.github/workflows/publish-image.yml`:
  публикует Docker image в `GHCR` на каждый `push` в `main`

После первого успешного publish образ будет доступен по именам:

- `ghcr.io/globalitcomua-dev/tg-sieve-filter:latest`
- `ghcr.io/globalitcomua-dev/tg-sieve-filter:sha-<commit>`

### Что настроить в GitHub один раз

1. Откройте `Settings -> Actions -> General`.
2. Убедитесь, что Actions разрешены для репозитория.
3. Убедитесь, что у `GITHUB_TOKEN` есть право писать packages.
4. После первого publish зайдите в `Packages` и проверьте видимость образа:
   для этого проекта лучше оставить image `private`.

### Как использовать образ на сервере

На сервере нужно один раз залогиниться в `ghcr.io`, используя GitHub token с правом `read:packages`:

```bash
docker login ghcr.io
docker pull ghcr.io/globalitcomua-dev/tg-sieve-filter:latest
docker compose up -d
```

### Что пока не автоматизировано

Автодеплой на staging/production пока специально не включён, потому что для него нужны ваши серверные данные:

- SSH host
- SSH user
- SSH key
- путь к `docker compose`
- production/staging `.env`

Когда будете готовы, следующим шагом можно добавить отдельный `deploy.yml` с ручным `workflow_dispatch`.

## Поведение при первом старте

Если `TELEGRAM_DROP_PENDING_UPDATES_ON_START=true`, бот на старте сбрасывает накопившиеся pending updates и начинает слушать только новые события после запуска.

Это полезно для production:

- исторические сообщения, которые были в группе до добавления бота, Telegram не присылает как новые updates;
- но накопившиеся pending updates бот может получить при первом запуске;
- с включённым флагом такие старые pending updates будут отброшены.
