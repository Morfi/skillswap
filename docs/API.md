# REST API

Базовый URL: `http://localhost:8080/api` (через nginx) или `http://localhost:8000/api` (напрямую).
Интерактивная документация (Swagger UI): **http://localhost:8080/api/docs**.

Все эндпоинты, кроме `/auth/register`, `/auth/login`, `/health`, требуют заголовок
`Authorization: Bearer <JWT>`.

## Авторизация

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| POST | `/auth/register` | Регистрация `{email, username, password, city?}` → `{access_token, user}` | все |
| POST | `/auth/login` | Вход `{email, password}` → `{access_token, user}` | все |
| GET | `/auth/me` | Текущий пользователь | user, admin |
| PUT | `/auth/me` | Обновить профиль `{username, city, bio}` | user, admin |

## Навыки — CRUD №1

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| **C** POST | `/skills` | Создать навык | user, admin |
| **R** GET | `/skills` | Каталог. Фильтры: `kind`, `category`, `level`, `format`, `city`, `search`, `mine=true` | user, admin |
| **R** GET | `/skills/{id}` | Один навык | user, admin |
| **U** PUT | `/skills/{id}` | Изменить навык | владелец, admin |
| **D** DELETE | `/skills/{id}` | Удалить навык | владелец, admin |
| GET | `/skills/categories` | Список категорий | все |
| GET | `/skills/matches` | Подбор партнёров для текущего пользователя | user, admin |

Тело навыка:

```json
{
  "kind": "offer",
  "title": "Гитара для начинающих",
  "category": "music",
  "level": "expert",
  "format": "both",
  "description": "Аккорды, бой, перебор",
  "is_active": true
}
```

## Заявки на обмен — CRUD №2

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| **C** POST | `/exchanges` | Создать заявку `{requested_skill_id, offered_skill_id?, message}` | user, admin |
| **R** GET | `/exchanges` | Мои заявки. `direction=all\|incoming\|outgoing`, `status=…`, `all_users=true` (admin) | участники, admin |
| **R** GET | `/exchanges/{id}` | Одна заявка | участники, admin |
| **U** PUT | `/exchanges/{id}` | Изменить `{offered_skill_id, message}` (только `pending`) | отправитель |
| **U** PATCH | `/exchanges/{id}/status` | Смена статуса `{status}` | см. ниже |
| **U** POST | `/exchanges/{id}/rate` | Оценка партнёра `{rating: 1..5}` (только `completed`) | участники |
| **D** DELETE | `/exchanges/{id}` | Удалить (`pending`/`declined`/`cancelled`) | отправитель, admin |

Допустимые переходы статуса:

| Из | В | Кто |
|---|---|---|
| pending | accepted, declined | получатель |
| pending | cancelled | отправитель |
| accepted | completed, cancelled | любой участник |

## Пользователи и администрирование

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| GET | `/users/{id}` | Публичный профиль с рейтингом | user, admin |
| GET | `/users/{id}/skills` | Активные навыки пользователя | user, admin |
| GET | `/admin/users` | Все пользователи | admin |
| PATCH | `/admin/users/{id}/role` | `{role: "user" \| "admin"}` | admin |
| PATCH | `/admin/users/{id}/block` | `{is_blocked: true \| false}` | admin |
| DELETE | `/admin/users/{id}` | Удалить пользователя | admin |
| GET | `/admin/stats` | Статистика платформы | admin |

## Коды ответов

| Код | Когда |
|---|---|
| 200 / 201 / 204 | Успех |
| 400 | Нарушено бизнес-правило (недопустимый переход статуса, свой навык и т. п.) |
| 401 | Нет токена, токен неверный или истёк |
| 403 | Недостаточно прав (не владелец, не admin, пользователь заблокирован) |
| 404 | Объект не найден или недоступен |
| 409 | Конфликт (email занят, повторная заявка, повторная оценка) |
| 422 | Ошибка валидации входных данных |
