# API Documentation - Recruitment Platform

## Authentication

### **POST /auth/register**
**Описание:** Регистрация нового пользователя

**Входные данные:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "role": "candidate"  // "candidate" | "hr" | "admin"
}
```

**Что происходит:**
- Проверка уникальности email
- Хеширование пароля (bcrypt)
- Создание пользователя в БД
- Автоматическая установка `is_active=true`

**Выходные данные:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false,
  "role": "candidate",
  "is_blocked": false
}
```

***

### **POST /auth/login**
**Описание:** Вход в систему с отслеживанием неудачных попыток

**Входные данные (Form Data):**
```
username: user@example.com
password: password123
```

**Что происходит:**
- Проверка блокировки в Redis (лимит 5 попыток)
- Проверка пароля
- Проверка `is_blocked` в БД
- При успехе: очистка счётчика неудачных попыток
- Генерация JWT токена
- Сохранение токена в Redis (TTL 24 часа)
- При неудаче: увеличение счётчика в Redis

**Выходные данные:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Ошибки:**
- `429` - Слишком много попыток (заблокирован на 15 минут)
- `401` - Неверный email или пароль
- `403` - Аккаунт заблокирован администратором

***

### **POST /auth/logout**
**Описание:** Выход из системы (инвалидация токена)

**Входные данные (Headers):**
```
Authorization: Bearer <token>
```

**Что происходит:**
- Извлечение токена из заголовка
- Удаление токена из Redis
- Добавление токена в blacklist (TTL 24 часа)

**Выходные данные:**
```json
{
  "message": "Successfully logged out"
}
```

***

## Users

### **GET /users/me**
**Описание:** Получить профиль текущего пользователя

**Входные данные (Headers):**
```
Authorization: Bearer <token>
```

**Что происходит:**
- Проверка токена
- Проверка blacklist
- Получение данных пользователя из БД

**Выходные данные:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false,
  "role": "candidate",
  "is_blocked": false
}
```

***

### **PATCH /users/me**
**Описание:** Обновить свой профиль

**Входные данные:**
```json
{
  "email": "newemail@example.com",
  "password": "newpassword123"
}
```

**Что происходит:**
- Проверка авторизации
- Обновление только переданных полей
- Хеширование нового пароля (если передан)

**Выходные данные:**
```json
{
  "id": 1,
  "email": "newemail@example.com",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false,
  "role": "candidate",
  "is_blocked": false
}
```

***

## Candidates

### **POST /candidates/resume**
**Описание:** Загрузка резюме (docx или pdf)

**Входные данные (Form Data):**
```
file: resume.docx (или .pdf)
```

**Что происходит:**
- Проверка расширения файла (.docx или .pdf)
- Сохранение файла в `/uploads`
- Парсинг текста из файла (python-docx / PyPDF2)
- Обновление полей `resume_path` и `resume_text` пользователя

**Выходные данные:**
```json
{
  "message": "Resume uploaded successfully",
  "file_path": "/uploads/user_1_resume.docx",
  "extracted_text_length": 1542
}
```

***

### **POST /candidates/applications**
**Описание:** Подать заявку на вакансию

**Входные данные:**
```json
{
  "vacancy_id": 1
}
```

**Что происходит:**
- Проверка существования вакансии
- Проверка активности вакансии (`is_active=true`)
- Проверка на дубликаты (один кандидат = одна заявка)
- Проверка наличия резюме
- Расчёт match_score (сравнение `resume_text` и `required_skills`)
- Создание заявки
- Создание персонализированного уведомления

**Выходные данные:**
```json
{
  "id": 1,
  "vacancy_id": 1,
  "candidate_id": 3,
  "status": "new",
  "match_score": 75.5,
  "created_at": "2025-11-05T12:00:00Z",
  "updated_at": "2025-11-05T12:00:00Z"
}
```

***

### **GET /candidates/applications**
**Описание:** Получить все свои заявки

**Входные данные (Headers):**
```
Authorization: Bearer <token>
```

**Что происходит:**
- Получение всех заявок текущего кандидата из БД
- Сортировка по дате создания

**Выходные данные:**
```json
[
  {
    "id": 1,
    "vacancy_id": 1,
    "candidate_id": 3,
    "status": "new",
    "match_score": 75.5,
    "created_at": "2025-11-05T12:00:00Z",
    "updated_at": "2025-11-05T12:00:00Z"
  }
]
```

***

### **GET /candidates/notifications**
**Описание:** Получить все уведомления

**Входные данные (Headers):**
```
Authorization: Bearer <token>
```

**Что происходит:**
- Получение всех уведомлений текущего пользователя
- Сортировка по дате (новые первыми)

**Выходные данные:**
```json
[
  {
    "id": 1,
    "message": "Отлично! Вы подходите на вакансию 'Python Developer' на 75%",
    "is_read": false,
    "created_at": "2025-11-05T12:00:00Z"
  }
]
```

***

### **PATCH /candidates/notifications/{notification_id}/read**
**Описание:** Отметить уведомление как прочитанное

**Входные данные:**
```
URL: /candidates/notifications/1/read
```

**Что происходит:**
- Проверка принадлежности уведомления пользователю
- Установка `is_read=true`

**Выходные данные:**
```
204 No Content
```

***

## HR Manager

### **POST /hr/vacancies**
**Описание:** Создать новую вакансию

**Входные данные:**
```json
{
  "title": "Python Backend Developer",
  "description": "We are looking for Python developer",
  "required_skills": ["Python", "FastAPI", "PostgreSQL"]
}
```

**Что происходит:**
- Проверка роли (только HR)
- Создание вакансии с `hr_id=current_user.id`
- Установка `is_active=true`

**Выходные данные:**
```json
{
  "id": 1,
  "title": "Python Backend Developer",
  "description": "We are looking for Python developer",
  "required_skills": ["Python", "FastAPI", "PostgreSQL"],
  "hr_id": 2,
  "is_active": true,
  "created_at": "2025-11-05T12:00:00Z",
  "updated_at": "2025-11-05T12:00:00Z"
}
```

***

### **GET /hr/vacancies**
**Описание:** Получить все свои вакансии

**Входные данные (Headers):**
```
Authorization: Bearer <token>
```

**Что происходит:**
- Получение всех вакансий текущего HR (`hr_id=current_user.id`)

**Выходные данные:**
```json
[
  {
    "id": 1,
    "title": "Python Backend Developer",
    "description": "...",
    "required_skills": ["Python", "FastAPI"],
    "hr_id": 2,
    "is_active": true,
    "created_at": "2025-11-05T12:00:00Z",
    "updated_at": "2025-11-05T12:00:00Z"
  }
]
```

***

### **GET /hr/vacancies/{vacancy_id}**
**Описание:** Получить конкретную вакансию

**Входные данные:**
```
URL: /hr/vacancies/1
```

**Что происходит:**
- Проверка принадлежности вакансии HR
- Получение данных вакансии

**Выходные данные:**
```json
{
  "id": 1,
  "title": "Python Backend Developer",
  "description": "...",
  "required_skills": ["Python", "FastAPI"],
  "hr_id": 2,
  "is_active": true,
  "created_at": "2025-11-05T12:00:00Z",
  "updated_at": "2025-11-05T12:00:00Z"
}
```

***

### **PATCH /hr/vacancies/{vacancy_id}**
**Описание:** Обновить вакансию

**Входные данные:**
```json
{
  "title": "Senior Python Developer",
  "is_active": false
}
```

**Что происходит:**
- Проверка принадлежности вакансии HR
- Обновление только переданных полей

**Выходные данные:**
```json
{
  "id": 1,
  "title": "Senior Python Developer",
  "description": "...",
  "required_skills": ["Python", "FastAPI"],
  "hr_id": 2,
  "is_active": false,
  "created_at": "2025-11-05T12:00:00Z",
  "updated_at": "2025-11-05T12:10:00Z"
}
```

***

### **DELETE /hr/vacancies/{vacancy_id}**
**Описание:** Удалить вакансию

**Входные данные:**
```
URL: /hr/vacancies/1
```

**Что происходит:**
- Проверка принадлежности вакансии HR
- Удаление вакансии из БД
- Каскадное удаление всех связанных заявок

**Выходные данные:**
```
204 No Content
```

***

### **GET /hr/vacancies/{vacancy_id}/applications**
**Описание:** Получить заявки на вакансию с фильтром

**Входные данные:**
```
URL: /hr/vacancies/1/applications?min_score=70
```

**Что происходит:**
- Проверка принадлежности вакансии HR
- Получение заявок с `match_score >= min_score`
- JOIN с таблицей User для получения данных кандидатов
- Сортировка по убыванию match_score

**Выходные данные:**
```json
{
  "vacancy_id": 1,
  "vacancy_title": "Python Backend Developer",
  "total_applications": 3,
  "applications": [
    {
      "id": 1,
      "candidate_email": "candidate@example.com",
      "candidate_id": 3,
      "status": "new",
      "match_score": 85.0,
      "created_at": "2025-11-05T12:00:00Z",
      "updated_at": "2025-11-05T12:00:00Z",
      "resume_path": "/uploads/user_3_resume.pdf"
    }
  ]
}
```

***

### **GET /hr/vacancies/{vacancy_id}/analytics**
**Описание:** Получить полную аналитику по вакансии

**Входные данные:**
```
URL: /hr/vacancies/1/analytics
```

**Что происходит:**
- Проверка принадлежности вакансии HR
- Подсчёт общего количества откликов
- Расчёт среднего match_score
- Подсчёт распределения по статусам
- Расчёт времени до первого отклика

**Выходные данные:**
```json
{
  "vacancy_id": 1,
  "vacancy_title": "Python Backend Developer",
  "vacancy_created_at": "2025-11-05T10:00:00Z",
  "is_active": true,
  "statistics": {
    "total_applications": 5,
    "average_match_score": 72.5,
    "status_distribution": {
      "new": 3,
      "under_review": 1,
      "rejected": 0,
      "accepted": 1
    },
    "time_to_first_response": {
      "days": 0,
      "hours": 2,
      "minutes": 15,
      "total_seconds": 8100
    }
  }
}
```

***

## Admin

### **GET /admin/users**
**Описание:** Получить список пользователей с фильтрами

**Входные данные:**
```
URL: /admin/users?is_blocked=false&role=candidate
```

**Query параметры:**
- `is_blocked` (optional): `true` | `false`
- `role` (optional): `"candidate"` | `"hr"` | `"admin"`

**Что происходит:**
- Проверка роли (только superuser)
- Применение фильтров
- Получение пользователей из БД

**Выходные данные:**
```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "is_active": true,
    "is_superuser": false,
    "is_verified": false,
    "role": "candidate",
    "is_blocked": false
  }
]
```

***

### **POST /admin/users/{user_id}/block**
**Описание:** Заблокировать пользователя

**Входные данные:**
```
URL: /admin/users/3/block
```

**Что происходит:**
- Проверка существования пользователя
- Проверка (нельзя заблокировать себя)
- Установка `is_blocked=true`

**Выходные данные:**
```json
{
  "message": "User candidate@example.com has been blocked"
}
```

***

### **POST /admin/users/{user_id}/unblock**
**Описание:** Разблокировать пользователя

**Входные данные:**
```
URL: /admin/users/3/unblock
```

**Что происходит:**
- Проверка существования пользователя
- Установка `is_blocked=false`

**Выходные данные:**
```json
{
  "message": "User candidate@example.com has been unblocked"
}
```

***

### **GET /admin/stats**
**Описание:** Получить общую статистику системы

**Входные данные (Headers):**
```
Authorization: Bearer <token>
```

**Что происходит:**
- Подсчёт пользователей (всего, по ролям, заблокированных)
- Подсчёт вакансий (всего, активных)
- Подсчёт заявок

**Выходные данные:**
```json
{
  "users": {
    "total": 10,
    "candidates": 7,
    "hr_managers": 2,
    "admins": 1,
    "blocked": 1
  },
  "vacancies": {
    "total": 5,
    "active": 4
  },
  "applications": {
    "total": 15
  }
}
```

***

### **GET /admin/logs**
**Описание:** Получить последние N строк из лога

**Входные данные:**
```
URL: /admin/logs?lines=100
```

**Query параметры:**
- `lines` (optional, default=100, min=1, max=1000)

**Что происходит:**
- Чтение файла `/logs/app.log`
- Извлечение последних N строк

**Выходные данные:**
```json
{
  "total_lines": 5432,
  "returned_lines": 100,
  "logs": [
    "2025-11-05 12:00:00 | INFO | POST /auth/login | Status: 200 | User: 3 | Time: 0.123s",
    "2025-11-05 12:01:00 | INFO | GET /candidates/applications | Status: 200 | User: 3 | Time: 0.045s"
  ]
}
```

***

### **GET /admin/suspicious**
**Описание:** Получить пользователей с подозрительной активностью

**Входные данные:**
```
URL: /admin/suspicious?min_attempts=3
```

**Query параметры:**
- `min_attempts` (optional, default=3)

**Что происходит:**
- Сканирование Redis ключей `failed_login:*`
- Фильтрация по минимальному количеству попыток
- Сортировка по убыванию количества попыток

**Выходные данные:**
```json
{
  "total": 2,
  "users": [
    {
      "email": "suspicious@example.com",
      "failed_attempts": 5,
      "is_locked": true,
      "ttl_seconds": 720
    },
    {
      "email": "another@example.com",
      "failed_attempts": 3,
      "is_locked": false,
      "ttl_seconds": 540
    }
  ]
}
```

***

## Общая информация

### Коды ответов
- `200 OK` - Успешный запрос
- `201 Created` - Ресурс создан
- `204 No Content` - Успешно, нет тела ответа
- `400 Bad Request` - Некорректные данные
- `401 Unauthorized` - Не авторизован
- `403 Forbidden` - Нет доступа
- `404 Not Found` - Ресурс не найден
- `429 Too Many Requests` - Превышен лимит запросов

### Авторизация
Все защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <token>
```

### Роли и доступ
- **candidate**: `/candidates/*`
- **hr**: `/hr/*`
- **admin** (superuser): `/admin/*`