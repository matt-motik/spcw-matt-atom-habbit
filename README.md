# SkyPro Курсовая работа по DRF. Трекер полезных привычек

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1+-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.18+-red.svg)](https://www.django-rest-framework.org/)
[![Ruff](https://img.shields.io/badge/Ruff-0.17+-purple.svg)](https://docs.astral.sh/ruff/)

Бэкенд SPA-приложения для трекинга полезных привычек по книге Джеймса Клира «Атомные привычки». Хорошая привычка описывается одним предложением: «я буду [ДЕЙСТВИЕ] в [ВРЕМЯ] [МЕСТО]». За полезную привычку пользователь вознаграждает себя приятной привычкой или любой другой наградой, а бот в Telegram напоминает, когда пора её выполнить.

## 🚀 Возможности программы

- **Кастомный пользователь** `CustomUser` с авторизацией по email и полем `tg_chat_id` для напоминаний
- **JWT-авторизация** (`djangorestframework-simplejwt`): все эндпоинты закрыты, открыты только регистрация и получение токенов
- **Модель привычки** `Habit`: место, время, действие, признак приятной привычки, связанная привычка, периодичность, вознаграждение, время на выполнение, признак публичности
- **CRUD своих привычек** на `ModelViewSet`: создатель назначается автоматически, чужие привычки недоступны
- **Список публичных привычек** всех пользователей только для чтения
- **Пагинация** `LimitOffsetPagination`: по 5 привычек, ответ с `count`, `next`, `previous`, `results`
- **Валидаторы** правил из книги (`habits/validators.py`), в том числе при частичном изменении привычки
- **Напоминания в Telegram**: периодическая задача Celery раз в минуту отправляет напоминания через Bot API с учётом периодичности
- **CORS** (`django-cors-headers`): разрешённые домены фронтенда задаются в `.env`
- **Документация API** (`drf-spectacular`): Swagger и Redoc, все эндпоинты описаны вручную с параметрами, ответами и ошибками
- **Тесты** на все эндпоинты, валидаторы и задачи (`APITestCase`), Telegram подменяется моком, отчёт покрытия в `coverage.txt`
- **Админ-панель** для пользователей, привычек и периодических задач

## 📋 Содержание

- [Технологии](#технологии)
- [Установка](#установка)
- [Конфигурация](#конфигурация)
- [Использование](#использование)
- [Разработка](#разработка)
  - [Структура проекта](#структура-проекта)
  - [Линтеры и форматирование](#линтеры)
- [To do](#to-do)
- [Команда проекта](#команда-проекта)

<div id="технологии"></div>

## Технологии

| Компонент | Технология |
|-----------|------------|
| **Язык** | Python 3.14 |
| **Фреймворк** | Django 6.1 |
| **API** | Django REST framework 3.18 |
| **Авторизация** | Simple JWT |
| **CORS** | django-cors-headers |
| **Документация API** | drf-spectacular (OpenAPI 3, Swagger, Redoc) |
| **Очередь задач** | Celery, django-celery-beat |
| **Брокер** | Redis |
| **Уведомления** | Telegram Bot API, requests |
| **База данных** | PostgreSQL |
| **Управление зависимостями** | uv |
| **Линтинг** | Ruff |
| **Типизация** | MyPy |
| **Pre-commit** | pre-commit |

<div id="установка"></div>

## Установка

```bash
git clone https://github.com/matt-motik/spcw-matt-atom-habbit.git
cd spcw-matt-atom-habbit
uv sync --all-groups
```

Установите и запустите Redis (брокер для Celery):

```bash
# Arch, Manjaro
sudo pacman -S redis && sudo systemctl start redis

# Ubuntu, Debian
sudo apt install redis-server

# Astra Linux
sudo apt install redis-server && sudo systemctl start redis-server

# ALT Linux
sudo apt-get install redis && sudo systemctl start redis

# РЕД ОС, ROSA Linux
sudo dnf install redis && sudo systemctl start redis
```

Создайте базу данных PostgreSQL:

```bash
psql -U postgres -h localhost -c "CREATE DATABASE spcw_atom_habits;"
```

Затем:

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

<div id="конфигурация"></div>

## ⚙️ Конфигурация

### Переменные окружения

Скопируйте `.env.template` в `.env` и заполните:

```bash
cp .env.template .env
```

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| **SECRET_KEY** | Секретный ключ Django | - |
| **DEBUG** | Режим отладки | False |
| **ALLOWED_HOSTS** | Разрешённые хосты | localhost,127.0.0.1 |
| **DB_NAME** | Имя базы данных PostgreSQL | - |
| **DB_USER** | Пользователь PostgreSQL | - |
| **DB_PASSWORD** | Пароль PostgreSQL | - |
| **DB_HOST** | Хост PostgreSQL | - |
| **DB_PORT** | Порт PostgreSQL | - |
| **CORS_ALLOWED_ORIGINS** | Домены фронтенда, которым разрешены запросы к API, через запятую | - |
| **CSRF_TRUSTED_ORIGINS** | Доверенные домены для CSRF, через запятую | - |
| **TELEGRAM_BOT_TOKEN** | Токен бота от [@BotFather](https://t.me/BotFather) | - |
| **TELEGRAM_API_URL** | Адрес Telegram Bot API | https://api.telegram.org |
| **CELERY_BROKER_URL** | Адрес брокера Redis для Celery | redis://localhost:6379/0 |
| **CELERY_RESULT_BACKEND** | Адрес Redis для хранения результатов задач | redis://localhost:6379/0 |

### 🤖 Бот в Telegram

1. Создайте бота у [@BotFather](https://t.me/BotFather) командой `/newbot` и сохраните токен в `TELEGRAM_BOT_TOKEN`.
2. Каждый пользователь пишет боту `/start`: без этого бот не может писать первым.
3. Свой chat ID пользователь узнаёт у [@userinfobot](https://t.me/userinfobot) или в ответе `https://api.telegram.org/bot<TOKEN>/getUpdates` (поле `message.chat.id`) и указывает его в `tg_chat_id` при регистрации или в профиле.

<div id="использование"></div>

## 💻 Использование

### Запуск программы

```bash
uv run python manage.py runserver
```

API доступно по адресу http://127.0.0.1:8000/

Для напоминаний в отдельных терминалах запустите worker и beat:

```bash
uv run celery -A config worker -l INFO
uv run celery -A config beat -l INFO
```

### 📘 Документация API

| URL | Описание |
|-----|----------|
| `/api/docs/` | Swagger UI: описание и проверка запросов |
| `/api/redoc/` | Redoc: описание API |
| `/api/schema/` | Схема OpenAPI 3 (`?format=json` — в JSON) |

Документация открыта без авторизации. Чтобы выполнять запросы из Swagger, получите токен в `POST /users/token/`, нажмите **Authorize** и вставьте `access`.

### 🔐 Авторизация

Все эндпоинты, кроме регистрации и получения токенов, требуют заголовок:

```
Authorization: Bearer <access>
```

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/users/register/` | Регистрация (без авторизации) |
| POST | `/users/token/` | Получение пары `access` / `refresh` по email и паролю (без авторизации) |
| POST | `/users/token/refresh/` | Обновление `access` по `refresh` (без авторизации) |
| GET / PUT / PATCH | `/users/me/` | Свой профиль, здесь же задаётся `tg_chat_id` |

### 🌐 Эндпоинты API

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/habits/` | Список своих привычек с пагинацией |
| POST | `/habits/` | Создание привычки |
| GET | `/habits/<id>/` | Просмотр своей привычки |
| PUT / PATCH | `/habits/<id>/` | Изменение своей привычки |
| DELETE | `/habits/<id>/` | Удаление своей привычки |
| GET | `/habits/public/` | Список публичных привычек всех пользователей, только чтение |

Пример создания полезной привычки со связанной приятной:

```json
{
  "action": "гулять вокруг квартала",
  "time": "20:00",
  "place": "на улице",
  "related_habit": 1,
  "periodicity": 1,
  "duration": 120,
  "is_public": true
}
```

| Поле | Описание |
|------|----------|
| `action` | Действие глаголом несовершенного вида, чтобы читалось после «я буду»: «делать 10 приседаний» |
| `time` | Время выполнения, `ЧЧ:ММ`, по часовому поясу проекта (Europe/Moscow) |
| `place` | Место вместе с предлогом: «дома», «в парке», «на кухне» |
| `is_pleasant` | Приятная привычка — вознаграждение за полезную |
| `related_habit` | ID своей приятной привычки |
| `reward` | Вознаграждение, если нет связанной привычки |
| `periodicity` | Раз в сколько дней выполнять, от 1 до 7, по умолчанию 1 |
| `duration` | Время на выполнение в секундах, не больше 120 |
| `is_public` | Привычку видят все пользователи в `/habits/public/` |
| `owner`, `created_at`, `last_reminder` | Только чтение: создатель, дата создания, дата последнего напоминания |

### 📄 Пагинация

Списки `/habits/` и `/habits/public/` выводятся по 5 привычек. Параметры: `?limit=10` — сколько привычек вернуть (не больше 50), `?offset=5` — сколько пропустить.

```json
{
  "count": 12,
  "next": "http://127.0.0.1:8000/habits/?limit=5&offset=5",
  "previous": null,
  "results": []
}
```

### ✅ Валидация

| Правило | Ошибка |
|---------|--------|
| Нельзя одновременно указать `reward` и `related_habit` | `non_field_errors` |
| Время на выполнение — не больше 120 секунд | `duration` |
| Связанной может быть только приятная привычка | `related_habit` |
| Связанной может быть только своя привычка и не она сама | `related_habit` |
| У приятной привычки нет `reward` и `related_habit` | `non_field_errors` |
| Выполнять привычку хотя бы раз в 7 дней: `periodicity` от 1 до 7 | `periodicity` |
| С приятной привычки, к которой привязаны полезные, нельзя снять признак `is_pleasant` | `is_pleasant` |

При `PATCH` недостающие поля берутся из сохранённой привычки: например, к привычке со связанной привычкой нельзя добавить `reward`.

### 👥 Права доступа

| Действие | Создатель | Другой пользователь |
|----------|-----------|--------------------|
| Создание привычки | ✅ | ✅ |
| Список `/habits/` | свои | свои |
| Просмотр, изменение, удаление | ✅ | ❌ `404` |
| Список `/habits/public/` | ✅ | ✅ только чтение |

Право `IsOwner` описано в `habits/permissions.py`.

### ⏱️ Напоминания в Telegram

Celery настроен в `config/celery.py`, все настройки берутся из `settings.py` с префиксом `CELERY_`. Таймзона Celery совпадает с таймзоной проекта: `CELERY_TIMEZONE = TIME_ZONE = "Europe/Moscow"`.

| Задача | Запуск | Что делает |
|--------|--------|------------|
| `habits.tasks.send_habit_reminders` | celery-beat, каждую минуту | Отправляет в Telegram напоминания о полезных привычках, время которых наступило |

- Напоминание приходит, если время привычки сегодня уже наступило, с прошлого напоминания прошло не меньше `periodicity` дней и у создателя указан `tg_chat_id`. Приятные привычки отдельно не напоминаются, они указываются в напоминании о полезной.
- Если worker пропустил нужную минуту, напоминание придёт при следующем запуске в тот же день. Дата отправки сохраняется в `last_reminder`.
- Если Telegram вернул ошибку, задача не падает: ошибка пишется в лог без токена, а напоминание повторится при следующем запуске.
- Расписание задаётся в `CELERY_BEAT_SCHEDULE`. Beat работает с `DatabaseScheduler`: при запуске расписание сохраняется в базу, задачи видны и редактируются в админке в разделе **Periodic tasks**.

Пример напоминания:

```text
Напоминание: я буду гулять вокруг квартала в 20:00 на улице.
На выполнение — 120 сек.
После этого можно: принимать ванну с пеной.
```

## 👤 Админ-панель

Админка доступна по адресу: /admin

Зарегистрированные модели: CustomUser, Habit. Периодические задачи celery-beat — в разделе **Periodic tasks**.

<div id="разработка"></div>

## Разработка

<div id="структура-проекта"></div>

### Структура проекта
<!-- СЕКЦИЯ_AUTO_STRUCTURE: СТАРТ -->
<details>
<summary>📁 Структура проекта (развёрнуть)</summary>

*Этот раздел генерируется автоматически.*

```text
spcw-matt-atom-habbit/
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── schema.py
│   ├── settings.py
│   ├── tests.py
│   ├── urls.py
│   └── wsgi.py
├── docs/
│   └── api/
├── habits/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_habit_last_reminder_alter_habit_action_and_more.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── paginators.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── services.py
│   ├── tasks.py
│   ├── tests.py
│   ├── urls.py
│   ├── validators.py
│   └── views.py
├── users/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── managers.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── coverage.txt
├── manage.py
├── pyproject.toml
├── README.md
├── readme_gen.py
└── uv.lock
```

</details>
<!-- СЕКЦИЯ_AUTO_STRUCTURE: КОНЕЦ -->

<div id="линтеры"></div>

### 🔍 Линтеры и форматирование

Проект использует `ruff` для линтинга и форматирования, `mypy` для проверки типов.

### Проверка кода

```bash
# Линтинг
uv run ruff check habits/ users/ config/

# Автоисправление ошибок
uv run ruff check --fix habits/ users/ config/

# Форматирование
uv run ruff format habits/ users/ config/

# Проверка типов
uv run mypy habits/ users/ config/
```

### 🧪 Тесты

Для тестовой базы пользователю PostgreSQL нужно право на создание БД: `ALTER USER "<DB_USER>" CREATEDB;`

```bash
# Запуск тестов
uv run python manage.py test

# Тесты с подсчётом покрытия
uv run coverage run manage.py test
uv run coverage report

# Тесты, отчёт покрытия в coverage.txt и обновление README
uv run python readme_gen.py
```

<!-- СЕКЦИЯ_AUTO_TEST: СТАРТ -->
<details>
<summary>📊 Результаты тестов и покрытие (развёрнуть)</summary>

### 📊 Результаты тестов

```
Ran 54 tests in 15.620s
OK
```

### 📈 Покрытие

```text
Name                    Stmts   Miss  Cover
-------------------------------------------
config/__init__.py          2      0   100%
config/celery.py            6      0   100%
config/schema.py           10      0   100%
config/settings.py         37      0   100%
config/tests.py            15      0   100%
config/urls.py              4      0   100%
habits/__init__.py          0      0   100%
habits/admin.py             7      0   100%
habits/apps.py              5      0   100%
habits/models.py           22      0   100%
habits/paginators.py        4      0   100%
habits/permissions.py       8      0   100%
habits/serializers.py       9      0   100%
habits/services.py         35      0   100%
habits/tasks.py            13      0   100%
habits/tests.py           227      0   100%
habits/urls.py              7      0   100%
habits/validators.py       48      1    98%
habits/views.py            27      0   100%
users/__init__.py           0      0   100%
users/admin.py              6      0   100%
users/apps.py               5      0   100%
users/managers.py          21      0   100%
users/models.py            16      0   100%
users/serializers.py       35      2    94%
users/tests.py             82      0   100%
users/urls.py               4      0   100%
users/views.py             23      0   100%
-------------------------------------------
TOTAL                     678      3    99%
```

> 📄 Отчёт покрытия также сохранён в [`coverage.txt`](coverage.txt)


</details>
<!-- СЕКЦИЯ_AUTO_TEST: КОНЕЦ -->

### Pre-commit hooks

```bash
# Установить hooks (выполняется автоматически перед каждым коммитом)
uv run pre-commit install

# Проверить все файлы вручную
uv run pre-commit run --all-files
```

<!-- СЕКЦИЯ_AUTO_API: СТАРТ -->
<details>
<summary>📚 Документация API (развёрнуть)</summary>

*Этот раздел генерируется автоматически из docstring.*

| Модуль | Функция/Класс | Краткое описание |
|--------|---------------|------------------|
| [**`config/schema.py`**](docs/api/config/schema.md) | | |
| | [🔧 id_parameter](docs/api/config/schema.md#id_parameter) | Описание ID объекта в пути запроса. |
| [**`habits/admin.py`**](docs/api/habits/admin.md) | | |
| | [📦 HabitAdmin](docs/api/habits/admin.md#HabitAdmin) | Настройки админки для привычек. |
| [**`habits/apps.py`**](docs/api/habits/apps.md) | | |
| | [📦 HabitsConfig](docs/api/habits/apps.md#HabitsConfig) | Конфигурация приложения привычек. |
| [**`habits/models.py`**](docs/api/habits/models.md) | | |
| | [📦 Habit](docs/api/habits/models.md#Habit) | Привычка: я буду [действие] в [время] [место]. Место пишется с предлогом: «дома», «в парке». |
| | [📦 Habit.Meta](docs/api/habits/models.md#Habit-Meta) | Мета-параметры модели Habit. |
| [**`habits/paginators.py`**](docs/api/habits/paginators.md) | | |
| | [📦 HabitPaginator](docs/api/habits/paginators.md#HabitPaginator) | Списки привычек: по 5 на страницу, не больше 50 за запрос. |
| [**`habits/permissions.py`**](docs/api/habits/permissions.md) | | |
| | [📦 IsOwner](docs/api/habits/permissions.md#IsOwner) | Пользователь является создателем привычки. |
| | [⚙️ IsOwner.has_object_permission](docs/api/habits/permissions.md#IsOwner-has_object_permission) | Проверяет, что привычка принадлежит текущему пользователю. |
| [**`habits/serializers.py`**](docs/api/habits/serializers.md) | | |
| | [📦 HabitSerializer](docs/api/habits/serializers.md#HabitSerializer) | Сериализатор привычки. Создатель подставляется автоматически. |
| | [📦 HabitSerializer.Meta](docs/api/habits/serializers.md#HabitSerializer-Meta) | Мета-параметры сериализатора привычки. |
| [**`habits/services.py`**](docs/api/habits/services.md) | | |
| | [🔧 send_telegram_message](docs/api/habits/services.md#send_telegram_message) | Отправляет сообщение через Telegram Bot API. Возвращает True, если Telegram его принял. |
| | [🔧 is_reminder_due](docs/api/habits/services.md#is_reminder_due) | Возвращает True, если с прошлого напоминания прошло не меньше дней, чем периодичность привычки. |
| | [🔧 get_habits_to_remind](docs/api/habits/services.md#get_habits_to_remind) | Полезные привычки, время которых уже наступило сегодня и по которым пора напомнить. |
| | [🔧 build_reminder](docs/api/habits/services.md#build_reminder) | Текст напоминания: что, когда и где сделать и чем себя вознаградить. |
| [**`habits/tasks.py`**](docs/api/habits/tasks.md) | | |
| | [🔧 send_habit_reminders](docs/api/habits/tasks.md#send_habit_reminders) | Отправляет в Telegram напоминания о привычках, время которых наступило. Возвращает число отправленных. |
| [**`habits/validators.py`**](docs/api/habits/validators.md) | | |
| | [🔧 validate_duration](docs/api/habits/validators.md#validate_duration) | Время на выполнение — от 1 до 120 секунд. |
| | [🔧 validate_periodicity](docs/api/habits/validators.md#validate_periodicity) | Привычку нужно выполнять хотя бы раз в 7 дней. |
| | [📦 HabitValidator](docs/api/habits/validators.md#HabitValidator) | Базовый валидатор привычки: при частичном изменении недостающие поля берутся из объекта. |
| | [⚙️ HabitValidator.validate](docs/api/habits/validators.md#HabitValidator-validate) | Проверка, которую реализует конкретный валидатор. |
| | [📦 RewardOrRelatedHabitValidator](docs/api/habits/validators.md#RewardOrRelatedHabitValidator) | Нельзя одновременно указать вознаграждение и связанную привычку. |
| | [⚙️ RewardOrRelatedHabitValidator.validate](docs/api/habits/validators.md#RewardOrRelatedHabitValidator-validate) | Проверяет, что заполнено не больше одного из двух полей. |
| | [📦 RelatedHabitValidator](docs/api/habits/validators.md#RelatedHabitValidator) | Связанной может быть только своя приятная привычка, но не она сама. |
| | [⚙️ RelatedHabitValidator.validate](docs/api/habits/validators.md#RelatedHabitValidator-validate) | Проверяет признак приятной привычки, владельца и ссылку на саму себя. |
| | [📦 PleasantHabitValidator](docs/api/habits/validators.md#PleasantHabitValidator) | У приятной привычки нет вознаграждения и связанной привычки. |
| | [⚙️ PleasantHabitValidator.validate](docs/api/habits/validators.md#PleasantHabitValidator-validate) | Проверяет приятную привычку и запрет снимать признак, если она уже к чему-то привязана. |
| [**`habits/views.py`**](docs/api/habits/views.md) | | |
| | [📦 HabitViewSet](docs/api/habits/views.md#HabitViewSet) | CRUD привычек текущего пользователя. |
| | [⚙️ HabitViewSet.get_queryset](docs/api/habits/views.md#HabitViewSet-get_queryset) | Возвращает только привычки текущего пользователя. |
| | [⚙️ HabitViewSet.perform_create](docs/api/habits/views.md#HabitViewSet-perform_create) | Делает текущего пользователя создателем привычки. |
| | [📦 PublicHabitListAPIView](docs/api/habits/views.md#PublicHabitListAPIView) | Список публичных привычек без возможности изменения. |
| [**`manage.py`**](docs/api/manage.md) | | |
| | [🔧 main](docs/api/manage.md#main) | Run administrative tasks. |
| [**`users/admin.py`**](docs/api/users/admin.md) | | |
| | [📦 CustomUserAdmin](docs/api/users/admin.md#CustomUserAdmin) | Настройки админки для пользователей. |
| [**`users/apps.py`**](docs/api/users/apps.md) | | |
| | [📦 UsersConfig](docs/api/users/apps.md#UsersConfig) | Конфигурация приложения пользователей. |
| [**`users/managers.py`**](docs/api/users/managers.md) | | |
| | [📦 CustomUserManager](docs/api/users/managers.md#CustomUserManager) | Менеджер пользователей, использующий email вместо username. |
| | [⚙️ CustomUserManager.create_user](docs/api/users/managers.md#CustomUserManager-create_user) | Создаёт и сохраняет обычного пользователя. |
| | [⚙️ CustomUserManager.create_superuser](docs/api/users/managers.md#CustomUserManager-create_superuser) | Создаёт и сохраняет суперпользователя. |
| [**`users/models.py`**](docs/api/users/models.md) | | |
| | [📦 CustomUser](docs/api/users/models.md#CustomUser) | Кастомная модель пользователя с авторизацией по email. |
| | [📦 CustomUser.Meta](docs/api/users/models.md#CustomUser-Meta) | Мета-параметры модели CustomUser. |
| [**`users/serializers.py`**](docs/api/users/serializers.md) | | |
| | [📦 UserProfileSerializer](docs/api/users/serializers.md#UserProfileSerializer) | Сериализатор профиля текущего пользователя. |
| | [📦 UserProfileSerializer.Meta](docs/api/users/serializers.md#UserProfileSerializer-Meta) | Мета-параметры сериализатора профиля. |
| | [📦 UserRegisterSerializer](docs/api/users/serializers.md#UserRegisterSerializer) | Сериализатор регистрации пользователя. |
| | [📦 UserRegisterSerializer.Meta](docs/api/users/serializers.md#UserRegisterSerializer-Meta) | Мета-параметры сериализатора регистрации. |
| | [⚙️ UserRegisterSerializer.validate_email](docs/api/users/serializers.md#UserRegisterSerializer-validate_email) | Проверяет, что пользователь с таким email ещё не зарегистрирован. |
| | [⚙️ UserRegisterSerializer.validate](docs/api/users/serializers.md#UserRegisterSerializer-validate) | Проверяет пароль стандартными валидаторами Django. |
| | [⚙️ UserRegisterSerializer.create](docs/api/users/serializers.md#UserRegisterSerializer-create) | Создаёт пользователя с хешированным паролем. |
| [**`users/views.py`**](docs/api/users/views.md) | | |
| | [📦 UserRegisterAPIView](docs/api/users/views.md#UserRegisterAPIView) | Регистрация нового пользователя. Доступна без авторизации. |
| | [📦 UserTokenObtainPairView](docs/api/users/views.md#UserTokenObtainPairView) | Получение пары JWT-токенов. Доступно без авторизации. |
| | [📦 UserTokenRefreshView](docs/api/users/views.md#UserTokenRefreshView) | Обновление access-токена по refresh. Доступно без авторизации. |
| | [📦 UserProfileAPIView](docs/api/users/views.md#UserProfileAPIView) | Просмотр и изменение профиля текущего пользователя. |
| | [⚙️ UserProfileAPIView.get_object](docs/api/users/views.md#UserProfileAPIView-get_object) | Возвращает текущего пользователя. |

> 📘 **Полная документация** доступна в папке [`docs/api`](docs/api).

</details>
<!-- СЕКЦИЯ_AUTO_API: КОНЕЦ -->

<div id="to-do"></div>

## To do

- [x] Структура проекта, `pyproject.toml`, `.gitignore`, uv, линтеры, pre-commit
- [x] Настройки через `.env`, шаблон `.env.template`
- [x] PostgreSQL, CORS, JWT, drf-spectacular, Celery и celery-beat
- [x] Приложение users, модель `CustomUser` с email как `USERNAME_FIELD` и полем `tg_chat_id`
- [x] Регистрация, получение и обновление токенов, свой профиль
- [x] Приложение habits, модель `Habit`
- [x] Валидаторы привычки, в том числе при частичном изменении
- [x] CRUD своих привычек, `IsOwner`
- [x] Список публичных привычек
- [x] Пагинация по 5 привычек (`limit` / `offset`)
- [x] Ручные описания эндпоинтов, параметров и ошибок в документации
- [x] Отправка сообщений через Telegram Bot API
- [x] Периодическая задача напоминаний с учётом периодичности
- [x] Тесты эндпоинтов, валидаторов и задач, покрытие 80%+
- [x] README и документация

<div id="команда-проекта"></div>

## Команда проекта

- Matvey Bakirov — [mabakirov@gmail.com](mailto:mabakirov@gmail.com) — Back-End Engineer
