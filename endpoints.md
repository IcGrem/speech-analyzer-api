## Speech Analyzer API — эндпоинты (`/api/v1`)

Базовый префикс: **`/api/v1`**

Подключенные роутеры (см. `app/api/v1/router.py`):
- `/health`
- `/users`
- `/organizations`
- `/employees`
- `/dialogs`
- `/scheduler`

> Примечание: `analysis.py` сейчас **не подключён** (строка `include_router` закомментирована), поэтому эндпоинты `/analysis` недоступны, пока не раскомментировать.

---

## `health.py` (prefix: `/health`)

### GET `/api/v1/health/`
- **Назначение**: проверка здоровья приложения
- **Request**: без auth, без body (использует DB dependency)
- **Response**: `HealthResponse`

```json
{
  "status": "ok",
  "timestamp": "2025-12-22T12:34:56.789Z",
  "database": "ok",
  "version": "0.1.0"
}
```

---

## `users.py` (prefix: `/users`)

### POST `/api/v1/users/login`
- **Назначение**: авторизация пользователя
- **Request**: `application/x-www-form-urlencoded` (`OAuth2PasswordRequestForm`)
- **Response**: `UserResponseWithToken`
- **Side-effect**: ставит cookie `Authorization=Bearer <jwt>` (см. `users.py`)

Пример request:

```text
username=admin&password=secret
```

Пример response:

```json
{
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "username": "admin",
    "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "first_name": "Иван",
    "last_name": "Иванов",
    "middle_name": "Иванович",
    "email": "user@example.com",
    "phone": "+79990000000",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z"
  },
  "access_token": "Bearer <jwt>",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

### POST `/api/v1/users/logout`
- **Назначение**: выход из системы
- **Request**: без body
- **Response**: `dict`

```json
{
  "message": "Выход из системы прошел успешно"
}
```

### GET `/api/v1/users/me`
- **Назначение**: текущий пользователь
- **Request**: auth scopes `admin|operator`
- **Response**: `UserResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "username": "operator",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": null,
  "email": "user@example.com",
  "phone": "+79990000000",
  "role": "operator",
  "is_active": true,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### GET `/api/v1/users/get-users`
- **Назначение**: список всех пользователей
- **Request**: auth scopes `admin`
- **Response**: `List[UserResponse]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "username": "admin",
    "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "first_name": null,
    "last_name": null,
    "middle_name": null,
    "email": null,
    "phone": null,
    "role": "admin",
    "is_active": true,
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z"
  }
]
```

### POST `/api/v1/users/create-user`
- **Назначение**: создать пользователя
- **Request**: auth scopes `admin`, body: `UserCreate`
- **Response**: `UserResponse`

Пример request (важно: поле называется `hashed_password`, но фактически ожидается пароль в открытом виде — затем он хэшируется на бэке):

```json
{
  "username": "new_user",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": null,
  "email": "user@example.com",
  "phone": "+79990000000",
  "role": "operator",
  "hashed_password": "plain_password_here"
}
```

Пример response:

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "username": "new_user",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": null,
  "email": "user@example.com",
  "phone": "+79990000000",
  "role": "operator",
  "is_active": true,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### PUT `/api/v1/users/update-user/{user_id}`
- **Назначение**: обновить пользователя
- **Request**: auth scopes `admin`, path: `user_id: UUID`, body: `UserUpdate`
- **Response**: `UserResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "username": "updated_user",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": null,
  "email": "user@example.com",
  "phone": null,
  "role": "operator",
  "is_active": true,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:40:00.000Z"
}
```

### DELETE `/api/v1/users/delete-user/{user_id}`
- **Назначение**: удалить пользователя
- **Request**: auth scopes `admin`, path: `user_id: UUID`
- **Response**: `UserResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "username": "deleted_user",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "first_name": null,
  "last_name": null,
  "middle_name": null,
  "email": null,
  "phone": null,
  "role": "operator",
  "is_active": false,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### GET `/api/v1/users/get-user-by-id/{user_id}`
- **Назначение**: пользователь по ID
- **Request**: auth scopes `admin|operator`, path: `user_id: UUID`
- **Response**: `UserResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "username": "user1",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": null,
  "email": "user@example.com",
  "phone": "+79990000000",
  "role": "operator",
  "is_active": true,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### GET `/api/v1/users/search-users?name=...`
- **Назначение**: поиск пользователей по имени
- **Request**: auth scopes `admin|operator`, query: `name: str`
- **Response**: `List[UserResponse]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "username": "ivan",
    "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "first_name": "Иван",
    "last_name": "Иванов",
    "middle_name": null,
    "email": "user@example.com",
    "phone": "+79990000000",
    "role": "operator",
    "is_active": true,
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z"
  }
]
```

---

## `organizations.py` (prefix: `/organizations`)

### GET `/api/v1/organizations/get-organizations`
- **Назначение**: список организаций
- **Request**: auth scopes `admin|operator`
- **Response**: `List[OrganizationResponse]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "ООО Ромашка",
    "description": "Описание",
    "address": "Москва",
    "phone": "+79990000000",
    "email": "org@example.com",
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z"
  }
]
```

### POST `/api/v1/organizations/create-organization`
- **Назначение**: создать организацию
- **Request**: auth scopes `admin`, body: `OrganizationCreate`
- **Response**: `OrganizationResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "ООО Ромашка",
  "description": "Описание",
  "address": "Москва",
  "phone": "+79990000000",
  "email": "org@example.com",
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### PUT `/api/v1/organizations/update-organization/{organization_id}`
- **Назначение**: обновить организацию
- **Request**: auth scopes `admin`, path: `organization_id: UUID`, body: `OrganizationUpdate`
- **Response**: `OrganizationResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "ООО Ромашка 2",
  "description": "Новое описание",
  "address": "Москва",
  "phone": "+79990000000",
  "email": "org@example.com",
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:40:00.000Z"
}
```

### DELETE `/api/v1/organizations/delete-organization/{organization_id}`
- **Назначение**: удалить организацию
- **Request**: auth scopes `admin`, path: `organization_id: UUID`
- **Response**: `OrganizationResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "ООО Ромашка",
  "description": "Описание",
  "address": "Москва",
  "phone": "+79990000000",
  "email": "org@example.com",
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### GET `/api/v1/organizations/get-organization-by-id/{organization_id}`
- **Назначение**: организация по ID
- **Request**: auth scopes `admin|operator`, path: `organization_id: UUID`
- **Response**: `OrganizationResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "ООО Ромашка",
  "description": "Описание",
  "address": "Москва",
  "phone": "+79990000000",
  "email": "org@example.com",
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### GET `/api/v1/organizations/search-organizations?name=...`
- **Назначение**: поиск организаций по названию
- **Request**: auth scopes `admin|operator`, query: `name: str`
- **Response**: `List[OrganizationResponse]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "ООО Ромашка",
    "description": "Описание",
    "address": "Москва",
    "phone": "+79990000000",
    "email": "org@example.com",
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z"
  }
]
```

---

## `employees.py` (prefix: `/employees`)

### GET `/api/v1/employees/get-employees`
- **Назначение**: сотрудники организации текущего пользователя
- **Request**: auth scopes `admin|operator`
- **Response**: `List[EmployeeResponse]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "employee_id": 123,
    "first_name": "Иван",
    "last_name": "Иванов",
    "middle_name": null,
    "position": "Оператор",
    "phone": "+79990000000",
    "email": "emp@example.com",
    "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "is_active": true,
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z",
    "organization": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "ООО Ромашка",
      "description": null,
      "address": null,
      "phone": null,
      "email": null,
      "created_at": "2025-12-22T12:34:56.789Z",
      "updated_at": "2025-12-22T12:34:56.789Z"
    }
  }
]
```

### GET `/api/v1/employees/get-employees-list`
- **Назначение**: краткий список сотрудников
- **Request**: auth scopes `admin|operator`
- **Response**: `List[EmployeeList]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "employee_id": 123,
    "first_name": "Иван",
    "last_name": "Иванов",
    "position": "Оператор",
    "is_active": true,
    "organization": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "ООО Ромашка",
      "description": null,
      "address": null,
      "phone": null,
      "email": null,
      "created_at": "2025-12-22T12:34:56.789Z",
      "updated_at": "2025-12-22T12:34:56.789Z"
    }
  }
]
```

### POST `/api/v1/employees/create-employee`
- **Назначение**: создать сотрудника
- **Request**: auth scopes `admin`, body: `EmployeeCreate`
- **Response**: `EmployeeResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "employee_id": 123,
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": null,
  "position": "Оператор",
  "phone": "+79990000000",
  "email": "emp@example.com",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_active": true,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z",
  "organization": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "ООО Ромашка",
    "description": null,
    "address": null,
    "phone": null,
    "email": null,
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z"
  }
}
```

### PUT `/api/v1/employees/update-employee/{employee_id}`
- **Назначение**: обновить сотрудника
- **Request**: auth scopes `admin`, path: `employee_id: UUID`, body: `EmployeeUpdate`
- **Response**: `EmployeeResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "employee_id": 123,
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": null,
  "position": "Старший оператор",
  "phone": "+79990000000",
  "email": "emp@example.com",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_active": true,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:40:00.000Z",
  "organization": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "ООО Ромашка",
    "description": null,
    "address": null,
    "phone": null,
    "email": null,
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z"
  }
}
```

### DELETE `/api/v1/employees/delete-employee/{employee_id}`
- **Назначение**: удалить сотрудника
- **Request**: auth scopes `admin`, path: `employee_id: UUID`
- **Response**: `EmployeeResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "employee_id": 123,
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": null,
  "position": "Оператор",
  "phone": "+79990000000",
  "email": "emp@example.com",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_active": false,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z",
  "organization": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "ООО Ромашка",
    "description": null,
    "address": null,
    "phone": null,
    "email": null,
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z"
  }
}
```

### GET `/api/v1/employees/get-employee-by-id/{employee_id}`
- **Назначение**: сотрудник по ID
- **Request**: auth scopes `admin|operator`, path: `employee_id: UUID`
- **Response**: `EmployeeResponse` (формат как выше)

### GET `/api/v1/employees/search-employees?name=...`
- **Назначение**: поиск сотрудников по имени
- **Request**: auth scopes `admin|operator`, query: `name: str`
- **Response**: `List[EmployeeResponse]` (формат как выше)

### GET `/api/v1/employees/get-employees-by-organization/{organization_id}`
- **Назначение**: сотрудники организации
- **Request**: auth scopes `admin|operator`, path: `organization_id: UUID`
- **Response**: `List[EmployeeResponse]` (формат как выше)

---

## `dialogs.py` (prefix: `/dialogs`)

### POST `/api/v1/dialogs/get-audiodata-from-voca`
- **Назначение**: конкурентная загрузка аудио из Voca за период
- **Request**: auth scopes `admin|operator`, body: `AudioDownloadRequest`
- **Response**: `AudioDownloadResponse`

Пример request:

```json
{
  "start_date": "2025-12-22 00:00",
  "end_date": "2025-12-22 01:00"
}
```

Пример response:

```json
{
  "success": true,
  "message": "Успешно загружено 10 аудиофайлов...",
  "downloaded_count": 10,
  "total_found": 10,
  "period": "2025-12-22 00:00 - 2025-12-22 01:00",
  "download_time": 1.23
}
```

### GET `/api/v1/dialogs/get-dialogs/{organization_id}`
- **Назначение**: список диалогов (пагинация/фильтры/сортировка)
- **Request**: auth scopes `admin|operator`
- **Response**: `PaginatedResponse` (`data: List[Dict[str, Any]]`)

```json
{
  "total_count": 120,
  "total_page": 12,
  "page": 1,
  "size": 10,
  "data": [
    {
      "date": "2025-12-22T10:00:00Z",
      "employee_name": "Иванов Иван",
      "dialog_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "conversation_type": "m2c",
      "overall_score": 0.85,
      "dictionaries": "Словарь1,Словарь2"
    }
  ]
}
```

### POST `/api/v1/dialogs/create-dialog`
- **Назначение**: создать диалог
- **Request**: auth scopes `admin|operator`, body: `DialogCreate`
- **Response**: `DialogResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "employee_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "conversation_type": "m2c",
  "conversation": {
    "replicas": [
      { "speaker": "manager", "text": "Здравствуйте" },
      { "speaker": "customer", "text": "Алло" }
    ]
  },
  "filename": "call_001.wav",
  "recording_start_date": "2025-12-22T10:00:00Z",
  "recording_end_date": "2025-12-22T10:05:00Z",
  "audio_data_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "audio_data_for_analysis_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "dictionaries": "Словарь1",
  "greeting_farewell_score": 1.0,
  "completeness_score": 0.8,
  "tone_score": 0.9,
  "openness_helpfulness_score": 0.7,
  "listening_score": 0.6,
  "empathy_score": 0.5,
  "speech_quality_score": 0.9,
  "response_time_score": 0.7,
  "overall_score": 0.85,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### GET `/api/v1/dialogs/get-dialog/{dialog_id}`
- **Назначение**: диалог по ID (включая `employee`)
- **Request**: auth scopes `admin|operator`
- **Response**: `DialogWithEmployee`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "employee_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "conversation_type": "m2c",
  "conversation": { "replicas": [] },
  "filename": "call_001.wav",
  "recording_start_date": "2025-12-22T10:00:00Z",
  "recording_end_date": "2025-12-22T10:05:00Z",
  "audio_data_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "audio_data_for_analysis_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "dictionaries": "Словарь1",
  "greeting_farewell_score": 1.0,
  "completeness_score": 0.8,
  "tone_score": 0.9,
  "openness_helpfulness_score": 0.7,
  "listening_score": 0.6,
  "empathy_score": 0.5,
  "speech_quality_score": 0.9,
  "response_time_score": 0.7,
  "overall_score": 0.85,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z",
  "employee": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "employee_id": 123,
    "first_name": "Иван",
    "last_name": "Иванов",
    "middle_name": null,
    "position": "Оператор",
    "phone": null,
    "email": null,
    "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "is_active": true,
    "created_at": "2025-12-22T12:34:56.789Z",
    "updated_at": "2025-12-22T12:34:56.789Z",
    "organization": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "ООО Ромашка",
      "description": null,
      "address": null,
      "phone": null,
      "email": null,
      "created_at": "2025-12-22T12:34:56.789Z",
      "updated_at": "2025-12-22T12:34:56.789Z"
    }
  }
}
```

### PUT `/api/v1/dialogs/update-dialog/{dialog_id}`
- **Назначение**: обновить диалог
- **Request**: auth scopes `admin|operator`
- **Response**: `DialogResponse` (формат как `create-dialog`)

### DELETE `/api/v1/dialogs/delete-dialog/{dialog_id}`
- **Назначение**: удалить диалог
- **Request**: auth scopes `admin`
- **Response**: `DialogResponse` (объект удалённого диалога)

### GET `/api/v1/dialogs/get-dialogs-by-employee/{employee_id}`
- **Назначение**: диалоги сотрудника
- **Request**: auth scopes `admin|operator`
- **Response**: `List[DialogList]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "employee_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "conversation_type": "m2c",
    "filename": "call_001.wav",
    "recording_start_date": "2025-12-22T10:00:00Z",
    "recording_end_date": "2025-12-22T10:05:00Z",
    "audio_data_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "audio_data_for_analysis_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "dictionaries": "Словарь1",
    "created_at": "2025-12-22T12:34:56.789Z",
    "overall_score": 0.85
  }
]
```

### GET `/api/v1/dialogs/get-dialogs-by-date-range`
- **Назначение**: диалоги по диапазону дат
- **Request**: auth scopes `admin|operator`, query: `start_date`, `end_date`
- **Response**: `List[DialogList]` (формат как выше)

### GET `/api/v1/dialogs/get-employee-metrics/{organization_id}`
- **Назначение**: метрики сотрудников (Chart.js)
- **Request**: auth scopes `admin|operator`, query: `metric_type`, опционально `employee_ids`, `start_date`, `end_date`
- **Response**: `EmployeeMetricsChartResponse`

```json
{
  "labels": ["21-12-2025", "22-12-2025"],
  "datasets": [
    { "label": "Иванов Иван", "data": [0.75, 0.82], "backgroundColor": "#6366f1" }
  ]
}
```

### GET `/api/v1/dialogs/get-organization-daily-metrics/{organization_id}`
- **Назначение**: дневные метрики организации (Chart.js)
- **Request**: auth scopes `admin|operator`, query: `metric_types` (через `,`)
- **Response**: `OrganizationDailyMetricsChartResponse`

```json
{
  "labels": ["21-12-2025", "22-12-2025"],
  "datasets": [
    { "label": "Итоговая оценка", "data": [0.71, 0.79], "backgroundColor": "#FF1313FF" }
  ]
}
```

### GET `/api/v1/dialogs/get-organization-average-metrics/{organization_id}`
- **Назначение**: средние метрики + график
- **Request**: auth scopes `admin|operator`, query: `start_date`, `end_date`
- **Response**: `OrganizationAverageMetricsResponse`

```json
{
  "average_scores": {
    "overall_score": { "title": "Итоговая оценка", "score": 0.78 },
    "tone_score": { "title": "Тон общения", "score": 0.81 }
  },
  "graphic": {
    "labels": ["21-12-2025", "22-12-2025"],
    "datasets": [
      { "label": "Итоговая оценка", "data": [0.71, 0.79], "backgroundColor": "#FF1313FF" }
    ]
  }
}
```

### GET `/api/v1/dialogs/get-dialog-counts-by-dictionaries/{organization_id}`
- **Назначение**: количество диалогов по словарям в разрезе сотрудников (Chart.js)
- **Request**: auth scopes `admin|operator`
- **Response**: `DialogCountsByDictionariesChartResponse`

```json
{
  "labels": [
    { "description": "Скрипт приветствия", "color": "#4b5563" },
    { "description": "Запрещённые фразы", "color": "#ef4444" }
  ],
  "datasets": [
    { "label": "Иванов Иван", "data": [5, 2], "backgroundColor": "#6366f1" }
  ]
}
```

### GET `/api/v1/dialogs/get-dialogs-by-dictionaries`
- **Назначение**: агрегация по словарям
- **Request**: auth scopes `admin|operator`
- **Response**: `List[DialogsByDictionariesResponse]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "dict_1",
    "description": "Скрипт приветствия",
    "color": "#4b5563",
    "dialogs_count": 12
  }
]
```

### GET `/api/v1/dialogs/get-all-dictionaries-with-words`
- **Назначение**: все словари со словами
- **Request**: auth scopes `admin|operator`
- **Response**: `List[DictionaryWithWordsResponse]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "dict_1",
    "description": "Скрипт приветствия",
    "color": "#4b5563",
    "words": ["здравствуйте", "добрый день"]
  }
]
```

### GET `/api/v1/dialogs/audio-data/stats`
- **Назначение**: статистика по аудиозаписям
- **Request**: auth scopes `admin|operator`
- **Response**: `AudioDataStats`

```json
{
  "total_count": 1000,
  "processed_count": 800,
  "unprocessed_count": 200,
  "processed_percentage": 80.0
}
```

### POST `/api/v1/dialogs/audio-data/process-previous-day`
- **Назначение**: обработать аудиоданные за предыдущие сутки
- **Request**: auth scopes `admin|operator`, query: `target_date?: datetime`
- **Response**: `dict`

```json
{
  "success": true,
  "message": "Обработано 5 сотрудников",
  "processed_count": 5,
  "results": {
    "123": {
      "full_audio_path": "full_speech_data/123_2025-12-21/merged.wav"
    }
  }
}
```

### GET `/api/v1/dialogs/get-dialog-highlighted/{dialog_id}`
- **Назначение**: диалог с подсветкой слов
- **Request**: auth scopes `admin|operator`
- **Response**: `DialogHighlightedResponse`

```json
{
  "dialog_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "original_text": "Оригинальный текст...",
  "highlighted_text": "Текст со <span>подсветкой</span>...",
  "conversation_type": "m2c",
  "filename": "call_001.wav",
  "recording_start_date": "2025-12-22T10:00:00Z",
  "recording_end_date": "2025-12-22T10:05:00Z",
  "was_updated_in_db": true
}
```

### POST `/api/v1/dialogs/highlight-all-dialogs`
- **Назначение**: подсветить все диалоги организации
- **Request**: auth scopes `admin|operator`, query: `organization_id?: UUID`
- **Response**: `dict`

```json
{
  "success": true,
  "message": "Подсвечено 100 диалогов, обновлено в БД: 40",
  "highlighted_count": 100,
  "updated_in_db_count": 40,
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

### POST `/api/v1/dialogs/highlight-dialogs-by-dictionary`
- **Назначение**: подсветка по словарю (или всем)
- **Request**: auth scopes `admin|operator`, query: `dictionary_id?: UUID`, `organization_id?: UUID`, `use_expression_search: bool`
- **Response**: `dict`

```json
{
  "success": true,
  "message": "Подсвечено 50 диалогов по словарю, обновлено в БД: 10",
  "highlighted_count": 50,
  "updated_in_db_count": 10,
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "use_expression_search": false
}
```

### POST `/api/v1/dialogs/populate-dialog-dictionary/{dialog_id}`
- **Назначение**: заполнить `dialog_dictionary` для диалога
- **Request**: auth scopes `admin|operator`
- **Response**: `DialogDictionaryPopulateResponse`

```json
{
  "success": true,
  "message": "OK",
  "added_count": 3,
  "total_found": 5,
  "found_phrases_count": 12
}
```

### POST `/api/v1/dialogs/populate-all-dialogs-dictionaries`
- **Назначение**: заполнить `dialog_dictionary` для всех диалогов
- **Request**: auth scopes `admin|operator`, query: `organization_id?: UUID`
- **Response**: `DialogDictionaryPopulateAllResponse`

```json
{
  "success": true,
  "message": "OK",
  "processed_count": 100,
  "total_added": 350,
  "errors": null
}
```

### DELETE `/api/v1/dialogs/clear-dialog-dictionaries`
- **Назначение**: очистить связи диалог↔словарь (одного диалога или всех)
- **Request**: auth scopes `admin`, query: `dialog_id?: UUID`
- **Response**: `DialogDictionaryClearResponse`

```json
{
  "success": true,
  "message": "OK",
  "deleted_count": 350
}
```

### POST `/api/v1/dialogs/populate-all-dialogs-by_dictionary`
- **Назначение**: заполнить `dialog_dictionary` по конкретному словарю (или по всем)
- **Request**: auth scopes `admin|operator`, query: `dictionary_id?: UUID`, `organization_id?: UUID`, `use_expression_search: bool`
- **Response**: `DialogDictionaryPopulateAllResponse`

```json
{
  "success": true,
  "message": "OK",
  "processed_count": 100,
  "total_added": 350,
  "errors": null
}
```

---

## `scheduler.py` (prefix: `/scheduler`)

> Внимание: из-за prefix `/scheduler` и путей `/scheduler/...` итоговый URL получается **`/api/v1/scheduler/scheduler/...`**.

### GET `/api/v1/scheduler/scheduler/status`
- **Назначение**: статус планировщика
- **Request**: без auth
- **Response**: `SchedulerStatus` (локальная модель)

```json
{
  "is_running": true,
  "message": "Планировщик активен"
}
```

### POST `/api/v1/scheduler/scheduler/start`
- **Назначение**: запуск планировщика
- **Request**: без auth
- **Response**: `SchedulerStatus`

```json
{
  "is_running": true,
  "message": "Планировщик успешно запущен"
}
```

### POST `/api/v1/scheduler/scheduler/stop`
- **Назначение**: остановка планировщика
- **Request**: без auth
- **Response**: `SchedulerStatus`

```json
{
  "is_running": false,
  "message": "Планировщик успешно остановлен"
}
```

### POST `/api/v1/scheduler/scheduler/restart`
- **Назначение**: перезапуск планировщика
- **Request**: без auth
- **Response**: `SchedulerStatus`

```json
{
  "is_running": true,
  "message": "Планировщик успешно перезапущен"
}
```

---

## `analysis.py` (НЕ подключён; prefix был бы `/analysis`)

### POST `/api/v1/analysis/`
- **Назначение**: создать анализ по аудиофайлу
- **Request**: `multipart/form-data`, поле `file`
- **Response**: `AnalysisResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": null,
  "description": null,
  "filename": "audio.wav",
  "file_size": 123456,
  "status": "pending",
  "result": null,
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:34:56.789Z"
}
```

### GET `/api/v1/analysis/`
- **Назначение**: список анализов
- **Request**: query: `skip=0`, `limit=100`
- **Response**: `List[AnalysisList]`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": null,
    "description": null,
    "filename": "audio.wav",
    "status": "done",
    "created_at": "2025-12-22T12:34:56.789Z"
  }
]
```

### GET `/api/v1/analysis/{analysis_id}`
- **Назначение**: анализ по ID
- **Request**: path: `analysis_id: UUID`
- **Response**: `AnalysisResponse`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Звонок 1",
  "description": "Комментарий",
  "filename": "audio.wav",
  "file_size": 123456,
  "status": "done",
  "result": {
    "confidence": 0.93,
    "text": "Распознанный текст",
    "language": "ru",
    "duration": 12.34,
    "word_count": 42
  },
  "created_at": "2025-12-22T12:34:56.789Z",
  "updated_at": "2025-12-22T12:40:00.000Z"
}
```

### DELETE `/api/v1/analysis/{analysis_id}`
- **Назначение**: удалить анализ
- **Request**: path: `analysis_id: UUID`
- **Response**: `dict`

```json
{
  "message": "Анализ успешно удален"
}
```


