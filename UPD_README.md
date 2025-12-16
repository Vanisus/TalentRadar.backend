# Обновления проекта

## Верификация пароля при регистрации

### Описание изменений

Добавлена проверка совпадения паролей при регистрации пользователя. Теперь при регистрации пользователь должен ввести пароль дважды (основной пароль и подтверждение), и система проверяет, что оба значения совпадают.

### Что было изменено

**Файл:** `app/schemas/user.py`

В схему `UserCreate` добавлены:
- Новое обязательное поле `password_confirm` для подтверждения пароля
- Валидатор `validate_passwords_match()`, который проверяет совпадение паролей

### Как это работает

1. При регистрации пользователь отправляет запрос на эндпоинт `/auth/register` с данными:
   - `email` - email пользователя
   - `password` - основной пароль
   - `password_confirm` - подтверждение пароля (новое поле)
   - `role` - роль пользователя (опционально, по умолчанию CANDIDATE)
   - `full_name` - полное имя (опционально)

2. Pydantic валидатор `validate_passwords_match()` проверяет, что значения `password` и `password_confirm` совпадают.

3. Если пароли не совпадают, возвращается ошибка валидации со статусом `422 Unprocessable Entity` и сообщением: `"Пароли не совпадают"`.

4. Если пароли совпадают, пользователь создается стандартным образом через fastapi-users, при этом поле `password_confirm` не используется при создании пользователя (оно нужно только для валидации).

### Пример запроса

**Успешная регистрация:**
```json
POST /auth/register
Content-Type: application/json

{
  "email": "candidate@example.com",
  "password": "secure_password123",
  "password_confirm": "secure_password123",
  "full_name": "Иван Иванов"
}
```

**Ответ (успех):**
```json
{
  "id": 1,
  "email": "candidate@example.com",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false,
  "role": "candidate",
  "is_blocked": false,
  "full_name": "Иван Иванов"
}
```

**Ошибка (пароли не совпадают):**
```json
POST /auth/register
Content-Type: application/json

{
  "email": "candidate@example.com",
  "password": "secure_password123",
  "password_confirm": "different_password"
}
```

**Ответ (ошибка):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, Пароли не совпадают",
      "input": {...},
      "ctx": {"error": "Пароли не совпадают"}
    }
  ]
}
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Обновить форму регистрации:**
   - Добавить второе поле для ввода пароля (например, `password_confirm` или "Подтверждение пароля")
   - Оба поля должны быть типа `password` для скрытия ввода

2. **Отправка данных:**
   - При отправке формы регистрации включить оба поля: `password` и `password_confirm`
   - Убедиться, что оба значения совпадают перед отправкой запроса (опциональная проверка на клиенте для лучшего UX)

3. **Обработка ошибок:**
   - Обрабатывать ошибку валидации со статусом `422`, если пароли не совпадают
   - Показывать пользователю сообщение об ошибке: "Пароли не совпадают"

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <form @submit.prevent="handleRegister">
    <input
      v-model="form.email"
      type="email"
      placeholder="Email"
      required
    />
    <input
      v-model="form.password"
      type="password"
      placeholder="Пароль"
      required
    />
    <input
      v-model="form.password_confirm"
      type="password"
      placeholder="Подтверждение пароля"
      required
    />
    <button type="submit" :disabled="isLoading">
      Зарегистрироваться
    </button>
    <div v-if="error" class="error">
      {{ error }}
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const form = ref({
  email: '',
  password: '',
  password_confirm: ''
})

const isLoading = ref(false)
const error = ref('')

const handleRegister = async () => {
  // Опциональная проверка на клиенте
  if (form.value.password !== form.value.password_confirm) {
    error.value = 'Пароли не совпадают'
    return
  }

  isLoading.value = true
  error.value = ''

  try {
    const { data } = await $fetch('/auth/register', {
      method: 'POST',
      body: {
        email: form.value.email,
        password: form.value.password,
        password_confirm: form.value.password_confirm,
        role: 'candidate' // или другое значение
      }
    })

    // Обработка успешной регистрации
    console.log('Пользователь зарегистрирован:', data)
    // Перенаправление на страницу входа или дашборд
  } catch (err: any) {
    // Обработка ошибок
    if (err.statusCode === 422) {
      error.value = 'Пароли не совпадают'
    } else if (err.statusCode === 400) {
      error.value = err.data?.detail || 'Ошибка регистрации'
    } else {
      error.value = 'Произошла ошибка при регистрации'
    }
  } finally {
    isLoading.value = false
  }
}
</script>
```

#### Пример с использованием Yup для валидации (если используется):

```typescript
import * as yup from 'yup'

const registerSchema = yup.object({
  email: yup.string().email('Некорректный email').required('Email обязателен'),
  password: yup.string().min(8, 'Пароль должен быть не менее 8 символов').required('Пароль обязателен'),
  password_confirm: yup.string()
    .oneOf([yup.ref('password')], 'Пароли не совпадают')
    .required('Подтверждение пароля обязательно')
})
```

### Эндпоинты, затронутые изменениями

- `POST /auth/register` - эндпоинт регистрации пользователя (теперь требует поле `password_confirm`)

### Совместимость

- Изменения обратно совместимы с существующим API
- Существующие эндпоинты не затронуты (только схема валидации обновлена)
- Если поле `password_confirm` не указано, вернется ошибка валидации 422

### Дополнительные заметки

- Валидация происходит на уровне Pydantic перед созданием пользователя
- Поле `password_confirm` не сохраняется в базе данных - оно используется только для проверки
- Быстрая проверка совпадения паролей на фронтенде улучшает UX, но серверная валидация обязательна

---

## Валидация ФИО (Фамилия Имя Отчество)

### Описание изменений

Добавлена валидация поля `full_name` для проверки корректности формата ФИО. Поле должно содержать ровно три слова в формате "Фамилия Имя Отчество", написанные русскими буквами. Каждое слово должно начинаться с заглавной буквы.

### Что было изменено

**Файл:** `app/schemas/user.py`

В схемах `UserCreate` и `UserUpdate` добавлен:
- Валидатор `validate_full_name_format()` для поля `full_name`
- Проверка на соответствие формату "Фамилия Имя Отчество"
- Проверка на использование только кириллических букв
- Проверка на заглавную букву в начале каждого слова

### Как это работает

1. Если поле `full_name` предоставлено при регистрации или обновлении пользователя, валидатор проверяет:
   - Содержит ли строка только русские буквы (кириллицу) и пробелы
   - Разделяется ли строка ровно на 3 слова пробелами
   - Начинается ли каждое слово с заглавной буквы

2. Если любая из проверок не проходит, возвращается ошибка валидации со статусом `422 Unprocessable Entity` с соответствующим сообщением об ошибке.

3. Если поле `full_name` не указано (None), валидация пропускается (поле опциональное).

### Примеры запросов

**Успешная регистрация с корректным ФИО:**
```json
POST /auth/register
Content-Type: application/json

{
  "email": "candidate@example.com",
  "password": "secure_password123",
  "password_confirm": "secure_password123",
  "full_name": "Иванов Иван Иванович"
}
```

**Ошибка (неправильный формат - только 2 слова):**
```json
POST /auth/register
Content-Type: application/json

{
  "email": "candidate@example.com",
  "password": "secure_password123",
  "password_confirm": "secure_password123",
  "full_name": "Иванов Иван"
}
```

**Ответ (ошибка):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "full_name"],
      "msg": "Value error, ФИО должно быть в формате: Фамилия Имя Отчество",
      "input": "Иванов Иван",
      "ctx": {"error": "ФИО должно быть в формате: Фамилия Имя Отчество"}
    }
  ]
}
```

**Ошибка (использованы латинские буквы):**
```json
{
  "full_name": "Ivanov Ivan Ivanovich"
}
```

**Ответ (ошибка):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "full_name"],
      "msg": "Value error, ФИО должно содержать только русские буквы",
      "input": "Ivanov Ivan Ivanovich",
      "ctx": {"error": "ФИО должно содержать только русские буквы"}
    }
  ]
}
```

**Ошибка (слово не начинается с заглавной буквы):**
```json
{
  "full_name": "иванов Иван Иванович"
}
```

**Ответ (ошибка):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "full_name"],
      "msg": "Value error, Каждое слово в ФИО должно начинаться с заглавной буквы",
      "input": "иванов Иван Иванович",
      "ctx": {"error": "Каждое слово в ФИО должно начинаться с заглавной буквы"}
    }
  ]
}
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Обновить форму регистрации/редактирования профиля:**
   - Добавить поле для ввода ФИО
   - Добавить placeholder или подсказку: "Фамилия Имя Отчество" (например, "Иванов Иван Иванович")
   - Рекомендуется добавить валидацию на клиенте для улучшения UX

2. **Валидация на клиенте (опционально, но рекомендуется):**
   - Проверять, что введено ровно 3 слова
   - Проверять, что используются только русские буквы
   - Проверять, что каждое слово начинается с заглавной буквы
   - Автоматически преобразовывать первую букву каждого слова в заглавную (опционально)

3. **Обработка ошибок:**
   - Обрабатывать ошибки валидации со статусом `422` для поля `full_name`
   - Показывать пользователю понятные сообщения об ошибках

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <form @submit.prevent="handleRegister">
    <input
      v-model="form.email"
      type="email"
      placeholder="Email"
      required
    />
    <input
      v-model="form.password"
      type="password"
      placeholder="Пароль"
      required
    />
    <input
      v-model="form.password_confirm"
      type="password"
      placeholder="Подтверждение пароля"
      required
    />
    <input
      v-model="form.full_name"
      type="text"
      placeholder="Фамилия Имя Отчество"
      @blur="formatFullName"
    />
    <div v-if="errors.full_name" class="error">
      {{ errors.full_name }}
    </div>
    <button type="submit" :disabled="isLoading">
      Зарегистрироваться
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const form = ref({
  email: '',
  password: '',
  password_confirm: '',
  full_name: ''
})

const errors = ref({
  full_name: ''
})

const isLoading = ref(false)

// Функция для форматирования ФИО (каждое слово с заглавной буквы)
const formatFullName = () => {
  if (!form.value.full_name) return
  
  const parts = form.value.full_name.trim().split(/\s+/)
  form.value.full_name = parts
    .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ')
  
  // Проверка на клиенте
  validateFullName()
}

const validateFullName = () => {
  if (!form.value.full_name) {
    errors.value.full_name = ''
    return true
  }
  
  // Проверка на русские буквы
  const cyrillicPattern = /^[А-ЯЁа-яё\s]+$/
  if (!cyrillicPattern.test(form.value.full_name)) {
    errors.value.full_name = 'ФИО должно содержать только русские буквы'
    return false
  }
  
  // Проверка на количество слов
  const parts = form.value.full_name.trim().split(/\s+/)
  if (parts.length !== 3) {
    errors.value.full_name = 'Введите ФИО в формате: Фамилия Имя Отчество'
    return false
  }
  
  // Проверка на заглавные буквы
  for (const part of parts) {
    if (!part[0].match(/[А-ЯЁ]/)) {
      errors.value.full_name = 'Каждое слово должно начинаться с заглавной буквы'
      return false
    }
  }
  
  errors.value.full_name = ''
  return true
}

const handleRegister = async () => {
  if (!validateFullName()) {
    return
  }

  isLoading.value = true

  try {
    const { data } = await $fetch('/auth/register', {
      method: 'POST',
      body: {
        email: form.value.email,
        password: form.value.password,
        password_confirm: form.value.password_confirm,
        full_name: form.value.full_name || undefined
      }
    })

    console.log('Пользователь зарегистрирован:', data)
  } catch (err: any) {
    if (err.statusCode === 422 && err.data?.detail) {
      // Обработка ошибок валидации
      const fullNameError = err.data.detail.find((e: any) => e.loc?.includes('full_name'))
      if (fullNameError) {
        errors.value.full_name = fullNameError.msg || 'Ошибка валидации ФИО'
      }
    }
  } finally {
    isLoading.value = false
  }
}
</script>
```

#### Пример с использованием Yup для валидации:

```typescript
import * as yup from 'yup'

const registerSchema = yup.object({
  email: yup.string().email('Некорректный email').required('Email обязателен'),
  password: yup.string().min(8, 'Пароль должен быть не менее 8 символов').required('Пароль обязателен'),
  password_confirm: yup.string()
    .oneOf([yup.ref('password')], 'Пароли не совпадают')
    .required('Подтверждение пароля обязательно'),
  full_name: yup.string()
    .matches(/^[А-ЯЁа-яё\s]+$/, 'ФИО должно содержать только русские буквы')
    .test('three-words', 'ФИО должно быть в формате: Фамилия Имя Отчество', (value) => {
      if (!value) return true // опциональное поле
      const parts = value.trim().split(/\s+/)
      return parts.length === 3
    })
    .test('capital-letters', 'Каждое слово должно начинаться с заглавной буквы', (value) => {
      if (!value) return true
      const parts = value.trim().split(/\s+/)
      return parts.every(part => /^[А-ЯЁ]/.test(part))
    })
})
```

### Эндпоинты, затронутые изменениями

- `POST /auth/register` - эндпоинт регистрации пользователя (валидация поля `full_name`)
- `PATCH /users/me` - эндпоинт обновления текущего пользователя (валидация поля `full_name`)
- `PATCH /users/{id}` - эндпоинт обновления пользователя администратором (валидация поля `full_name`)

### Совместимость

- Поле `full_name` остается опциональным - если оно не указано, валидация не выполняется
- Существующие пользователи без ФИО или с некорректным форматом не затронуты при обновлении других полей
- При попытке установить некорректное значение ФИО будет возвращена ошибка валидации 422

### Дополнительные заметки

- Валидация происходит на уровне Pydantic перед сохранением в базу данных
- Проверка чувствительна к регистру: каждое слово должно начинаться с заглавной буквы
- Разрешены только кириллические буквы (А-Я, а-я, Ё, ё) и пробелы
- Множественные пробелы между словами автоматически обрабатываются через `.strip().split()`

---

## Рекомендованные вакансии для кандидатов

### Описание изменений

Добавлена функциональность получения рекомендованных вакансий для кандидатов на основе ключевых слов из их резюме. Система анализирует резюме кандидата и сопоставляет его с требованиями вакансий, рассчитывая процент совпадения (match_score).

### Что было изменено

**Файл:** `app/schemas/vacancy.py`
- Добавлена схема `VacancyWithMatchScore` - расширенная схема вакансии с полем `match_score`

**Файл:** `app/routers/candidates.py`
- Добавлен эндпоинт `GET /candidates/vacancies/recommended` для получения рекомендованных вакансий
- Эндпоинт использует функцию `calculate_match_score` для расчета соответствия резюме требованиям вакансий
- Вакансии сортируются по проценту совпадения (от большего к меньшему)

### Как это работает

1. Кандидат должен сначала загрузить резюме через эндпоинт `POST /candidates/resume`
2. При запросе рекомендованных вакансий система:
   - Проверяет наличие резюме у кандидата
   - Получает все активные вакансии (`is_active=True`)
   - Для каждой вакансии рассчитывает `match_score` на основе сравнения ключевых слов из резюме с требуемыми навыками (`required_skills`)
   - Фильтрует вакансии по минимальному проценту совпадения (опциональный параметр `min_score`)
   - Сортирует вакансии по `match_score` в порядке убывания
   - Возвращает список рекомендованных вакансий с процентом совпадения

3. Алгоритм расчета `match_score`:
   - Берется текст резюме кандидата и список требуемых навыков вакансии
   - Для каждого требуемого навыка проверяется наличие его в тексте резюме (без учета регистра)
   - Рассчитывается процент: (количество найденных навыков / общее количество требуемых навыков) * 100

### Пример запроса

**Успешный запрос:**
```http
GET /candidates/vacancies/recommended?min_score=50.0
Authorization: Bearer <token>
```

**Ответ (успех):**
```json
[
  {
    "id": 1,
    "title": "Python Developer",
    "description": "Разработка веб-приложений на Python",
    "required_skills": ["Python", "Django", "PostgreSQL", "REST API"],
    "hr_id": 2,
    "is_active": true,
    "created_at": "2025-01-10T10:00:00Z",
    "updated_at": "2025-01-10T10:00:00Z",
    "match_score": 75.0
  },
  {
    "id": 3,
    "title": "Backend Developer",
    "description": "Разработка backend на Python и FastAPI",
    "required_skills": ["Python", "FastAPI", "SQL"],
    "hr_id": 2,
    "is_active": true,
    "created_at": "2025-01-11T12:00:00Z",
    "updated_at": "2025-01-11T12:00:00Z",
    "match_score": 66.67
  }
]
```

**Ошибка (нет резюме):**
```json
{
  "detail": "Please upload your resume first to get recommendations"
}
```

### Параметры запроса

- `min_score` (опционально, по умолчанию 0.0) - минимальный процент совпадения (0-100). Вакансии с процентом ниже этого значения не будут включены в результат.

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Добавить раздел "Рекомендованные вакансии":**
   - Отобразить список рекомендованных вакансий с процентом совпадения
   - Показывать проценты совпадения визуально (например, прогресс-бар или звездочки)
   - Сортировать вакансии по проценту совпадения

2. **Визуализация match_score:**
   - Выделять вакансии с высоким процентом совпадения (например, >= 70%)
   - Использовать цветовую индикацию (зеленый для высокого, желтый для среднего, красный для низкого совпадения)

3. **Фильтрация:**
   - Добавить возможность установить минимальный процент совпадения через UI (например, слайдер или селект)

4. **Обработка ошибок:**
   - Если у кандидата нет резюме, показывать сообщение с предложением загрузить резюме

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="recommended-vacancies">
    <h2>Рекомендованные вакансии</h2>
    
    <div v-if="!hasResume" class="alert">
      Для получения рекомендаций загрузите резюме
      <NuxtLink to="/candidates/resume/upload">
        Загрузить резюме
      </NuxtLink>
    </div>

    <div v-else>
      <div class="filters">
        <label>
          Минимальный процент совпадения:
          <input
            v-model.number="minScore"
            type="range"
            min="0"
            max="100"
            step="10"
            @input="loadRecommendations"
          />
          {{ minScore }}%
        </label>
      </div>

      <div v-if="loading">Загрузка...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="vacancies.length === 0" class="empty">
        Нет рекомендованных вакансий с таким процентом совпадения
      </div>
      <div v-else class="vacancies-list">
        <div
          v-for="vacancy in vacancies"
          :key="vacancy.id"
          class="vacancy-card"
          :class="getMatchScoreClass(vacancy.match_score)"
        >
          <h3>{{ vacancy.title }}</h3>
          <p>{{ vacancy.description }}</p>
          <div class="skills">
            <strong>Требуемые навыки:</strong>
            <span v-for="skill in vacancy.required_skills" :key="skill" class="skill-tag">
              {{ skill }}
            </span>
          </div>
          <div class="match-score">
            <div class="match-score-label">
              Совпадение: <strong>{{ vacancy.match_score }}%</strong>
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: `${vacancy.match_score}%` }"
              ></div>
            </div>
          </div>
          <button @click="applyToVacancy(vacancy.id)">
            Подать заявку
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface VacancyWithMatchScore {
  id: number
  title: string
  description: string
  required_skills: string[]
  hr_id: number
  is_active: boolean
  created_at: string
  updated_at: string
  match_score: number
}

const vacancies = ref<VacancyWithMatchScore[]>([])
const loading = ref(false)
const error = ref('')
const minScore = ref(0)
const hasResume = ref(true) // проверять отдельно

const getMatchScoreClass = (score: number): string => {
  if (score >= 70) return 'match-high'
  if (score >= 50) return 'match-medium'
  return 'match-low'
}

const loadRecommendations = async () => {
  loading.value = true
  error.value = ''

  try {
    const data = await $fetch<VacancyWithMatchScore[]>('/candidates/vacancies/recommended', {
      method: 'GET',
      params: {
        min_score: minScore.value
      },
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })

    vacancies.value = data
  } catch (err: any) {
    if (err.statusCode === 400 && err.data?.detail?.includes('resume')) {
      hasResume.value = false
      error.value = 'Сначала загрузите резюме'
    } else {
      error.value = 'Ошибка при загрузке рекомендаций'
    }
  } finally {
    loading.value = false
  }
}

const applyToVacancy = async (vacancyId: number) => {
  // Логика подачи заявки
  // Можно использовать существующий эндпоинт POST /candidates/applications
}

onMounted(() => {
  loadRecommendations()
})
</script>

<style scoped>
.match-high {
  border-left: 4px solid green;
}

.match-medium {
  border-left: 4px solid orange;
}

.match-low {
  border-left: 4px solid red;
}

.progress-bar {
  width: 100%;
  height: 10px;
  background-color: #e0e0e0;
  border-radius: 5px;
  overflow: hidden;
  margin-top: 5px;
}

.progress-fill {
  height: 100%;
  background-color: #4caf50;
  transition: width 0.3s ease;
}

.skill-tag {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px;
  background-color: #f0f0f0;
  border-radius: 4px;
  font-size: 0.9em;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `GET /candidates/vacancies/recommended` - новый эндпоинт для получения рекомендованных вакансий

### Совместимость

- Эндпоинт доступен только для авторизованных кандидатов (требует токен авторизации)
- Для работы эндпоинта необходимо наличие загруженного резюме
- Эндпоинт возвращает только активные вакансии (`is_active=True`)
- Существующие эндпоинты не затронуты

### Дополнительные заметки

- Алгоритм расчета match_score основан на простом поиске подстрок в тексте резюме (без учета регистра)
- Вакансии с одинаковым процентом совпадения сортируются в порядке их получения из базы данных
- Параметр `min_score` позволяет фильтровать вакансии по минимальному проценту совпадения для более релевантных результатов
- Для улучшения рекомендаций в будущем можно добавить более сложные алгоритмы машинного обучения или NLP-обработку

---

## Рекомендации по улучшению резюме для кандидатов

### Описание изменений

Добавлена функциональность получения персонализированных рекомендаций по улучшению резюме на основе анализа популярных навыков в вакансиях и структуры резюме кандидата.

### Что было изменено

**Файл:** `app/services/resume_recommendations.py` (новый)
- Создан сервис `analyze_resume_improvements()` для анализа резюме и генерации рекомендаций
- Анализирует отсутствующие популярные навыки
- Проверяет структуру резюме (наличие контактов, опыта, образования, раздела навыков)
- Генерирует рекомендации с приоритетами

**Файл:** `app/schemas/resume_recommendation.py` (новый)
- Созданы схемы для структурированного ответа с рекомендациями:
  - `MissingSkill` - навык, отсутствующий в резюме
  - `PopularSkill` - популярный навык в вакансиях
  - `ResumeStats` - статистика резюме
  - `GeneralRecommendation` - общая рекомендация
  - `ResumeRecommendation` - основная схема ответа

**Файл:** `app/routers/candidates.py`
- Добавлен эндпоинт `GET /candidates/resume/recommendations` для получения рекомендаций

### Как это работает

1. Кандидат должен сначала загрузить резюме через эндпоинт `POST /candidates/resume`
2. При запросе рекомендаций система:
   - Проверяет наличие резюме у кандидата
   - Получает все активные вакансии
   - Собирает все навыки из всех вакансий и анализирует их популярность
   - Определяет навыки, которых нет в резюме, но они часто встречаются в вакансиях
   - Анализирует структуру резюме (длина, наличие ключевых секций)
   - Генерирует персонализированные рекомендации с приоритетами

3. Рекомендации включают:
   - **Отсутствующие навыки** - популярные навыки, которых нет в резюме, с указанием частоты их упоминания в вакансиях
   - **Популярные навыки** - топ навыков, наиболее часто упоминаемых в вакансиях
   - **Статистика резюме** - метрики резюме (длина, количество слов, наличие секций)
   - **Общие рекомендации** - советы по улучшению структуры и содержания резюме

### Пример запроса

**Успешный запрос:**
```http
GET /candidates/resume/recommendations
Authorization: Bearer <token>
```

**Ответ (успех):**
```json
{
  "missing_skills": [
    {
      "skill": "Docker",
      "frequency": 15,
      "percentage_of_vacancies": 75.0
    },
    {
      "skill": "Kubernetes",
      "frequency": 12,
      "percentage_of_vacancies": 60.0
    },
    {
      "skill": "Git",
      "frequency": 18,
      "percentage_of_vacancies": 90.0
    }
  ],
  "popular_skills": [
    {
      "skill": "Python",
      "frequency": 20
    },
    {
      "skill": "Docker",
      "frequency": 15
    },
    {
      "skill": "Git",
      "frequency": 18
    }
  ],
  "resume_stats": {
    "length": 1200,
    "word_count": 180,
    "has_contact_info": true,
    "has_experience": true,
    "has_education": false,
    "has_skills_section": true
  },
  "general_recommendations": [
    {
      "type": "education",
      "priority": "low",
      "message": "Добавьте информацию об образовании.",
      "details": "Образование может быть важным фактором для некоторых позиций."
    },
    {
      "type": "missing_skills",
      "priority": "high",
      "message": "Рассмотрите возможность добавить популярные навыки: Docker, Kubernetes, Git",
      "details": "Эти навыки встречаются в 90.0% вакансий и могут увеличить ваши шансы на трудоустройство."
    }
  ]
}
```

**Ошибка (нет резюме):**
```json
{
  "detail": "Please upload your resume first to get recommendations"
}
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Добавить раздел "Рекомендации по улучшению резюме":**
   - Отобразить список отсутствующих навыков с процентным показателем
   - Показать статистику резюме
   - Отобразить общие рекомендации с приоритетами (high, medium, low)

2. **Визуализация рекомендаций:**
   - Выделять рекомендации с высоким приоритетом (high)
   - Показывать процент вакансий, требующих отсутствующий навык
   - Использовать цветовую индикацию приоритетов (красный для high, оранжевый для medium, зеленый для low)

3. **Интерактивные элементы:**
   - Возможность отметить рекомендацию как выполненную
   - Сортировка рекомендаций по приоритету
   - Фильтрация по типу рекомендации

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="resume-recommendations">
    <h2>Рекомендации по улучшению резюме</h2>
    
    <div v-if="!hasResume" class="alert">
      Для получения рекомендаций загрузите резюме
      <NuxtLink to="/candidates/resume/upload">
        Загрузить резюме
      </NuxtLink>
    </div>

    <div v-else>
      <div v-if="loading">Загрузка рекомендаций...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="recommendations">
        <!-- Статистика резюме -->
        <div class="stats-section">
          <h3>Статистика резюме</h3>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-label">Длина:</span>
              <span class="stat-value">{{ recommendations.resume_stats.length }} символов</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Слов:</span>
              <span class="stat-value">{{ recommendations.resume_stats.word_count }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Контактная информация:</span>
              <span class="stat-value" :class="{ 'check': recommendations.resume_stats.has_contact_info, 'cross': !recommendations.resume_stats.has_contact_info }">
                {{ recommendations.resume_stats.has_contact_info ? '✓' : '✗' }}
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Опыт работы:</span>
              <span class="stat-value" :class="{ 'check': recommendations.resume_stats.has_experience, 'cross': !recommendations.resume_stats.has_experience }">
                {{ recommendations.resume_stats.has_experience ? '✓' : '✗' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Отсутствующие навыки -->
        <div v-if="recommendations.missing_skills.length > 0" class="section">
          <h3>Популярные навыки, которых нет в вашем резюме</h3>
          <div class="skills-list">
            <div
              v-for="skill in recommendations.missing_skills"
              :key="skill.skill"
              class="skill-item"
            >
              <div class="skill-name">{{ skill.skill }}</div>
              <div class="skill-stats">
                <span class="frequency">В {{ skill.frequency }} вакансиях</span>
                <span class="percentage">{{ skill.percentage_of_vacancies }}% вакансий</span>
              </div>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: `${skill.percentage_of_vacancies}%` }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Общие рекомендации -->
        <div v-if="recommendations.general_recommendations.length > 0" class="section">
          <h3>Рекомендации</h3>
          <div class="recommendations-list">
            <div
              v-for="(rec, index) in sortedRecommendations"
              :key="index"
              class="recommendation-item"
              :class="`priority-${rec.priority}`"
            >
              <div class="recommendation-header">
                <span class="priority-badge" :class="rec.priority">
                  {{ getPriorityLabel(rec.priority) }}
                </span>
                <span class="recommendation-type">{{ getTypeLabel(rec.type) }}</span>
              </div>
              <div class="recommendation-message">{{ rec.message }}</div>
              <div class="recommendation-details">{{ rec.details }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface MissingSkill {
  skill: string
  frequency: number
  percentage_of_vacancies: number
}

interface GeneralRecommendation {
  type: string
  priority: 'high' | 'medium' | 'low'
  message: string
  details: string
}

interface ResumeRecommendation {
  missing_skills: MissingSkill[]
  popular_skills: Array<{ skill: string; frequency: number }>
  resume_stats: {
    length: number
    word_count: number
    has_contact_info: boolean
    has_experience: boolean
    has_education: boolean
    has_skills_section: boolean
  }
  general_recommendations: GeneralRecommendation[]
}

const recommendations = ref<ResumeRecommendation | null>(null)
const loading = ref(false)
const error = ref('')
const hasResume = ref(true)

const sortedRecommendations = computed(() => {
  if (!recommendations.value) return []
  const priorityOrder = { high: 1, medium: 2, low: 3 }
  return [...recommendations.value.general_recommendations].sort(
    (a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]
  )
})

const getPriorityLabel = (priority: string) => {
  const labels = { high: 'Высокий', medium: 'Средний', low: 'Низкий' }
  return labels[priority as keyof typeof labels] || priority
}

const getTypeLabel = (type: string) => {
  const labels = {
    length: 'Длина резюме',
    contact: 'Контактная информация',
    experience: 'Опыт работы',
    education: 'Образование',
    skills_section: 'Раздел навыков',
    missing_skills: 'Отсутствующие навыки'
  }
  return labels[type as keyof typeof labels] || type
}

const loadRecommendations = async () => {
  loading.value = true
  error.value = ''

  try {
    const data = await $fetch<ResumeRecommendation>('/candidates/resume/recommendations', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })

    recommendations.value = data
  } catch (err: any) {
    if (err.statusCode === 400 && err.data?.detail?.includes('resume')) {
      hasResume.value = false
      error.value = 'Сначала загрузите резюме'
    } else {
      error.value = 'Ошибка при загрузке рекомендаций'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRecommendations()
})
</script>

<style scoped>
.priority-high {
  border-left: 4px solid #f44336;
}

.priority-medium {
  border-left: 4px solid #ff9800;
}

.priority-low {
  border-left: 4px solid #4caf50;
}

.priority-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: bold;
}

.priority-badge.high {
  background-color: #f44336;
  color: white;
}

.priority-badge.medium {
  background-color: #ff9800;
  color: white;
}

.priority-badge.low {
  background-color: #4caf50;
  color: white;
}

.check {
  color: #4caf50;
}

.cross {
  color: #f44336;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 5px;
}

.progress-fill {
  height: 100%;
  background-color: #2196f3;
  transition: width 0.3s ease;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-item {
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `GET /candidates/resume/recommendations` - новый эндпоинт для получения рекомендаций по улучшению резюме

### Совместимость

- Эндпоинт доступен только для авторизованных кандидатов (требует токен авторизации)
- Для работы эндпоинта необходимо наличие загруженного резюме
- Эндпоинт анализирует только активные вакансии (`is_active=True`)
- Существующие эндпоинты не затронуты

### Дополнительные заметки

- Алгоритм анализирует популярность навыков на основе частоты их упоминания в вакансиях
- Рекомендации приоритизируются по важности (high, medium, low)
- Отсутствующие навыки сортируются по частоте использования в вакансиях (от наиболее популярных)
- Рекомендации обновляются автоматически при изменении вакансий в системе
- В будущем можно добавить машинное обучение для более точных персонализированных рекомендаций

---

## Правила платформы для кандидатов

### Описание изменений

Добавлена функциональность получения правил использования платформы для кандидатов. Эндпоинт возвращает полный список правил, которые должны соблюдать кандидаты при использовании платформы.

### Что было изменено

**Файл:** `app/schemas/platform_rules.py` (новый)
- Создана схема `PlatformRule` - правило платформы с заголовком и описанием
- Создана схема `PlatformRules` - основной ответ с списком правил и датой обновления

**Файл:** `app/routers/candidates.py`
- Добавлен эндпоинт `GET /candidates/platform-rules` для получения правил платформы

### Как это работает

1. Эндпоинт возвращает статический список правил платформы
2. Правила включают информацию о:
   - Регистрации и профиле
   - Загрузке резюме
   - Подаче заявок на вакансии
   - Поведении на платформе
   - Конфиденциальности
   - Ответственности за информацию
   - Блокировке аккаунта
   - Рекомендациях по улучшению резюме
   - Уведомлениях
   - Контактах и поддержке

3. Каждое правило содержит заголовок и подробное описание

### Пример запроса

**Успешный запрос:**
```http
GET /candidates/platform-rules
Authorization: Bearer <token>
```

**Ответ (успех):**
```json
{
  "rules": [
    {
      "title": "Регистрация и профиль",
      "description": "При регистрации вы должны предоставить достоверную информацию. Укажите корректное ФИО в формате 'Фамилия Имя Отчество' и действительный email адрес. Обновляйте свой профиль при изменении данных."
    },
    {
      "title": "Загрузка резюме",
      "description": "Вы обязаны загрузить актуальное резюме в формате DOCX или PDF. Резюме должно содержать полную информацию о вашем опыте работы, навыках и образовании. Регулярно обновляйте резюме при получении нового опыта."
    },
    {
      "title": "Подача заявок на вакансии",
      "description": "Вы можете подавать заявку на любую открытую вакансию, но только один раз на каждую вакансию. Перед подачей заявки убедитесь, что ваше резюме актуально и соответствует требованиям вакансии."
    },
    {
      "title": "Поведение на платформе",
      "description": "Запрещается публиковать недостоверную информацию, спамить работодателей или использовать платформу для мошеннических целей. Уважайте права других пользователей и соблюдайте этические нормы общения."
    },
    {
      "title": "Конфиденциальность",
      "description": "Ваши личные данные и резюме доступны только работодателям, на вакансии которых вы подали заявку, и администраторам платформы. Мы не передаем ваши данные третьим лицам без вашего согласия."
    },
    {
      "title": "Ответственность за информацию",
      "description": "Вы несете полную ответственность за достоверность предоставленной информации. Предоставление ложных данных может привести к блокировке аккаунта и исключению из платформы."
    },
    {
      "title": "Блокировка аккаунта",
      "description": "Администратор имеет право заблокировать ваш аккаунт в случае нарушения правил платформы, предоставления недостоверной информации или иных действий, наносящих вред платформе или другим пользователям."
    },
    {
      "title": "Рекомендации и улучшение резюме",
      "description": "Используйте рекомендации по улучшению резюме для повышения ваших шансов на трудоустройство. Система анализирует популярные навыки в вакансиях и предлагает способы улучшить ваше резюме."
    },
    {
      "title": "Уведомления",
      "description": "Вы будете получать уведомления о статусе ваших заявок и других важных событиях. Регулярно проверяйте уведомления, чтобы быть в курсе изменений."
    },
    {
      "title": "Контакты и поддержка",
      "description": "При возникновении вопросов или проблем обратитесь к администратору платформы через указанные контактные данные. Мы постараемся помочь вам в кратчайшие сроки."
    }
  ],
  "last_updated": "2025-01-15T10:30:00"
}
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Добавить страницу "Правила платформы":**
   - Отобразить список правил с заголовками и описаниями
   - Показать дату последнего обновления правил
   - Сделать страницу доступной для просмотра кандидатами

2. **Визуальное оформление:**
   - Использовать читабельную типографику
   - Разделить правила визуально (например, карточками или секциями)
   - Добавить нумерацию или иконки для каждого правила

3. **Добавить ссылку на правила:**
   - В футере сайта
   - В меню профиля кандидата
   - При первом входе или регистрации (опционально)

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="platform-rules">
    <h1>Правила платформы</h1>
    
    <div v-if="loading">Загрузка правил...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="rules">
      <div class="last-updated">
        Последнее обновление: {{ formatDate(rules.last_updated) }}
      </div>
      
      <div class="rules-list">
        <div
          v-for="(rule, index) in rules.rules"
          :key="index"
          class="rule-card"
        >
          <div class="rule-number">{{ index + 1 }}</div>
          <div class="rule-content">
            <h2 class="rule-title">{{ rule.title }}</h2>
            <p class="rule-description">{{ rule.description }}</p>
          </div>
        </div>
      </div>
      
      <div class="accept-section">
        <label class="checkbox-label">
          <input
            v-model="rulesAccepted"
            type="checkbox"
          />
          Я ознакомился(ась) с правилами платформы и обязуюсь их соблюдать
        </label>
        <button
          @click="acceptRules"
          :disabled="!rulesAccepted"
          class="accept-button"
        >
          Принять правила
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface PlatformRule {
  title: string
  description: string
}

interface PlatformRules {
  rules: PlatformRule[]
  last_updated: string
}

const rules = ref<PlatformRules | null>(null)
const loading = ref(false)
const error = ref('')
const rulesAccepted = ref(false)

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const loadRules = async () => {
  loading.value = true
  error.value = ''

  try {
    const data = await $fetch<PlatformRules>('/candidates/platform-rules', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })

    rules.value = data
  } catch (err: any) {
    error.value = 'Ошибка при загрузке правил'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const acceptRules = () => {
  // Логика принятия правил (например, сохранение в localStorage или отправка на сервер)
  localStorage.setItem('platform_rules_accepted', 'true')
  // Можно также отправить запрос на сервер для сохранения статуса принятия
  alert('Правила приняты!')
}

onMounted(() => {
  loadRules()
  // Проверяем, были ли правила уже приняты
  const accepted = localStorage.getItem('platform_rules_accepted')
  if (accepted === 'true') {
    rulesAccepted.value = true
  }
})
</script>

<style scoped>
.platform-rules {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.rule-card {
  display: flex;
  gap: 20px;
  padding: 20px;
  margin-bottom: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  border-left: 4px solid #2196f3;
}

.rule-number {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #2196f3;
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: 1.2em;
}

.rule-content {
  flex: 1;
}

.rule-title {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 1.3em;
}

.rule-description {
  margin: 0;
  color: #666;
  line-height: 1.6;
}

.last-updated {
  text-align: right;
  color: #999;
  font-size: 0.9em;
  margin-bottom: 30px;
}

.accept-section {
  margin-top: 40px;
  padding: 20px;
  background-color: #f0f0f0;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.accept-button {
  padding: 12px 24px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.3s;
}

.accept-button:hover:not(:disabled) {
  background-color: #1976d2;
}

.accept-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `GET /candidates/platform-rules` - новый эндпоинт для получения правил платформы

### Совместимость

- Эндпоинт доступен только для авторизованных кандидатов (требует токен авторизации)
- Правила возвращаются в статическом виде (не требуют наличия резюме или других данных)
- Существующие эндпоинты не затронуты

### Дополнительные заметки

- Правила хранятся в коде и могут быть легко обновлены при необходимости
- Дата последнего обновления генерируется динамически при каждом запросе
- В будущем можно перенести правила в базу данных для более гибкого управления через админ-панель
- Правила можно расширить или изменить в зависимости от требований платформы

---

## Мониторинг работоспособности платформы для администратора

### Описание изменений

Добавлена функциональность мониторинга работоспособности платформы для администраторов. Эндпоинт предоставляет детальную информацию о состоянии всех компонентов системы и системных метриках.

### Что было изменено

**Файл:** `app/services/health_monitor.py` (новый)
- Создан сервис для проверки работоспособности компонентов:
  - `check_database_health()` - проверка подключения к PostgreSQL
  - `check_redis_health()` - проверка подключения к Redis
  - `check_filesystem_health()` - проверка доступности и возможности записи в директории uploads и logs
  - `get_system_metrics()` - получение системных метрик (CPU, память, диск) с использованием psutil (опционально)
  - `get_overall_health()` - общая функция для получения статуса всех компонентов

**Файл:** `app/schemas/health.py` (новый)
- Созданы схемы для структурированного ответа:
  - `ComponentHealth` - статус отдельного компонента
  - `SystemMetrics` - системные метрики
  - `HealthStatus` - основная схема ответа с общей информацией

**Файл:** `app/routers/admin.py`
- Добавлен эндпоинт `GET /admin/health` для получения статуса работоспособности

### Как это работает

1. Эндпоинт проверяет работоспособность всех критических компонентов системы:
   - **База данных (PostgreSQL)** - выполняется простой SQL-запрос для проверки подключения
   - **Redis** - проверка подключения через команду ping
   - **Файловая система** - проверка возможности создания и записи файлов в директории uploads и logs

2. Опционально собираются системные метрики (если установлен psutil):
   - Использование CPU (процент)
   - Использование памяти (общий объем, использовано, процент)
   - Использование диска (общий объем, использовано, процент)

3. Каждый компонент получает статус "healthy" или "unhealthy"
4. Общий статус системы определяется как "healthy", если все компоненты работают, иначе "unhealthy"

### Пример запроса

**Успешный запрос:**
```http
GET /admin/health
Authorization: Bearer <token>
```

**Ответ (система работает нормально):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.123456",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection is working"
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection is working"
    },
    "filesystem": {
      "status": "healthy",
      "message": "Filesystem is working properly"
    }
  },
  "system_metrics": {
    "cpu": {
      "percent": 15.5,
      "status": "healthy"
    },
    "memory": {
      "total_gb": 16.0,
      "used_gb": 8.5,
      "percent": 53.1,
      "status": "healthy"
    },
    "disk": {
      "total_gb": 100.0,
      "used_gb": 45.2,
      "percent": 45.2,
      "status": "healthy"
    }
  }
}
```

**Ответ (проблемы с компонентами):**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-01-15T10:30:00.123456",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection is working"
    },
    "redis": {
      "status": "unhealthy",
      "message": "Redis connection failed: Connection refused"
    },
    "filesystem": {
      "status": "healthy",
      "message": "Filesystem is working properly"
    }
  },
  "system_metrics": {
    "cpu": {
      "percent": 15.5,
      "status": "healthy"
    },
    "memory": {
      "total_gb": 16.0,
      "used_gb": 8.5,
      "percent": 53.1,
      "status": "healthy"
    },
    "disk": {
      "total_gb": 100.0,
      "used_gb": 45.2,
      "percent": 45.2,
      "status": "healthy"
    }
  }
}
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Создать дашборд мониторинга:**
   - Отобразить общий статус системы (здоровье/проблемы)
   - Показать статус каждого компонента с визуальной индикацией (зеленый/красный)
   - Отобразить системные метрики с прогресс-барами или графиками

2. **Визуализация:**
   - Использовать цветовую индикацию: зеленый для healthy, красный для unhealthy
   - Для системных метрик использовать цветовые пороги:
     - Зеленый: использование < 85%
     - Оранжевый: использование 85-95%
     - Красный: использование > 95%
   - Показывать прогресс-бары для CPU, памяти и диска

3. **Автообновление:**
   - Настроить автоматическое обновление статуса каждые 30-60 секунд
   - Добавить возможность ручного обновления

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="health-monitor">
    <h1>Мониторинг платформы</h1>
    
    <div v-if="loading">Загрузка статуса...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="health">
      <!-- Общий статус -->
      <div class="overall-status" :class="health.status">
        <h2>Общий статус: {{ health.status === 'healthy' ? 'Работает нормально' : 'Обнаружены проблемы' }}</h2>
        <p>Последнее обновление: {{ formatTimestamp(health.timestamp) }}</p>
      </div>

      <!-- Статус компонентов -->
      <div class="components-section">
        <h3>Статус компонентов</h3>
        <div class="components-grid">
          <div
            v-for="(component, name) in health.components"
            :key="name"
            class="component-card"
            :class="component.status"
          >
            <h4>{{ getComponentName(name) }}</h4>
            <div class="status-indicator" :class="component.status">
              {{ component.status === 'healthy' ? '✓' : '✗' }}
            </div>
            <p>{{ component.message }}</p>
          </div>
        </div>
      </div>

      <!-- Системные метрики -->
      <div v-if="health.system_metrics && !health.system_metrics.error && !health.system_metrics.message" class="metrics-section">
        <h3>Системные метрики</h3>
        <div class="metrics-grid">
          <!-- CPU -->
          <div v-if="health.system_metrics.cpu" class="metric-card">
            <h4>CPU</h4>
            <div class="metric-value">{{ health.system_metrics.cpu.percent }}%</div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :class="health.system_metrics.cpu.status"
                :style="{ width: `${health.system_metrics.cpu.percent}%` }"
              ></div>
            </div>
            <span class="metric-status" :class="health.system_metrics.cpu.status">
              {{ getStatusLabel(health.system_metrics.cpu.status) }}
            </span>
          </div>

          <!-- Память -->
          <div v-if="health.system_metrics.memory" class="metric-card">
            <h4>Память</h4>
            <div class="metric-value">
              {{ health.system_metrics.memory.used_gb }} GB / {{ health.system_metrics.memory.total_gb }} GB
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :class="health.system_metrics.memory.status"
                :style="{ width: `${health.system_metrics.memory.percent}%` }"
              ></div>
            </div>
            <span class="metric-status" :class="health.system_metrics.memory.status">
              {{ getStatusLabel(health.system_metrics.memory.status) }}
            </span>
          </div>

          <!-- Диск -->
          <div v-if="health.system_metrics.disk" class="metric-card">
            <h4>Диск</h4>
            <div class="metric-value">
              {{ health.system_metrics.disk.used_gb }} GB / {{ health.system_metrics.disk.total_gb }} GB
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :class="health.system_metrics.disk.status"
                :style="{ width: `${health.system_metrics.disk.percent}%` }"
              ></div>
            </div>
            <span class="metric-status" :class="health.system_metrics.disk.status">
              {{ getStatusLabel(health.system_metrics.disk.status) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <button @click="loadHealth" class="refresh-button">Обновить</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface ComponentHealth {
  status: 'healthy' | 'unhealthy'
  message: string
}

interface SystemMetrics {
  cpu?: { percent: number; status: string }
  memory?: { total_gb: number; used_gb: number; percent: number; status: string }
  disk?: { total_gb: number; used_gb: number; percent: number; status: string }
  error?: string
  message?: string
}

interface HealthStatus {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  components: Record<string, ComponentHealth>
  system_metrics: SystemMetrics
}

const health = ref<HealthStatus | null>(null)
const loading = ref(false)
const error = ref('')
let refreshInterval: ReturnType<typeof setInterval> | null = null

const getComponentName = (name: string) => {
  const names: Record<string, string> = {
    database: 'База данных',
    redis: 'Redis',
    filesystem: 'Файловая система'
  }
  return names[name] || name
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    healthy: 'Норма',
    warning: 'Предупреждение',
    critical: 'Критично'
  }
  return labels[status] || status
}

const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleString('ru-RU')
}

const loadHealth = async () => {
  loading.value = true
  error.value = ''

  try {
    const data = await $fetch<HealthStatus>('/admin/health', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })

    health.value = data
  } catch (err: any) {
    error.value = 'Ошибка при загрузке статуса системы'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadHealth()
  // Автообновление каждые 30 секунд
  refreshInterval = setInterval(loadHealth, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.health-monitor {
  padding: 20px;
}

.overall-status {
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.overall-status.healthy {
  background-color: #d4edda;
  border: 2px solid #28a745;
}

.overall-status.unhealthy {
  background-color: #f8d7da;
  border: 2px solid #dc3545;
}

.components-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.component-card {
  padding: 20px;
  border-radius: 8px;
  border: 2px solid #ddd;
}

.component-card.healthy {
  border-color: #28a745;
  background-color: #f8fff9;
}

.component-card.unhealthy {
  border-color: #dc3545;
  background-color: #fff8f8;
}

.status-indicator {
  font-size: 2em;
  font-weight: bold;
  margin: 10px 0;
}

.status-indicator.healthy {
  color: #28a745;
}

.status-indicator.unhealthy {
  color: #dc3545;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.metric-card {
  padding: 20px;
  border: 2px solid #ddd;
  border-radius: 8px;
}

.metric-value {
  font-size: 1.5em;
  font-weight: bold;
  margin: 10px 0;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
  margin: 10px 0;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.progress-fill.healthy {
  background-color: #28a745;
}

.progress-fill.warning {
  background-color: #ffc107;
}

.progress-fill.critical {
  background-color: #dc3545;
}

.metric-status {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: bold;
}

.metric-status.healthy {
  background-color: #d4edda;
  color: #155724;
}

.metric-status.warning {
  background-color: #fff3cd;
  color: #856404;
}

.metric-status.critical {
  background-color: #f8d7da;
  color: #721c24;
}

.refresh-button {
  margin-top: 20px;
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.refresh-button:hover {
  background-color: #0056b3;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `GET /admin/health` - новый эндпоинт для получения статуса работоспособности платформы

### Совместимость

- Эндпоинт доступен только для администраторов (требует токен авторизации с ролью ADMIN)
- Системные метрики опциональны и требуют установки библиотеки `psutil` (можно добавить в requirements.txt)
- Существующие эндпоинты не затронуты

### Дополнительные заметки

- Проверка компонентов выполняется асинхронно для быстрого ответа
- Системные метрики получаются синхронно, но это не должно создавать проблем при нормальной работе
- Пороги для определения статуса метрик:
  - CPU: healthy < 90%, warning 90-95%, critical >= 95%
  - Память: healthy < 85%, warning 85-95%, critical >= 95%
  - Диск: healthy < 85%, warning 85-95%, critical >= 95%
- В будущем можно добавить интеграцию с Prometheus или другими системами мониторинга
- Можно расширить мониторинг, добавив проверку других компонентов (например, внешних API)

---

## Расширенная статистика платформы для администратора

### Описание изменений

Расширен эндпоинт статистики платформы для администраторов. Теперь он предоставляет детальную аналитику по всем аспектам работы платформы, включая временные метрики, распределение по статусам и популярные навыки.

### Что было изменено

**Файл:** `app/schemas/statistics.py` (новый)
- Созданы схемы для структурированного ответа:
  - `UserStatistics` - детальная статистика по пользователям
  - `VacancyStatistics` - статистика по вакансиям с временными метриками
  - `ApplicationStatistics` - статистика по заявкам с распределением по статусам
  - `NotificationStatistics` - статистика по уведомлениям
  - `PlatformStatistics` - основная схема ответа со всей статистикой

**Файл:** `app/routers/admin.py`
- Расширен эндпоинт `GET /admin/stats` с дополнительными метриками
- Добавлена временная статистика (сегодня, неделя, месяц)
- Добавлен топ-10 популярных навыков в вакансиях
- Добавлена статистика по статусам заявок
- Добавлена статистика по уведомлениям

### Как это работает

1. Эндпоинт собирает статистику по следующим категориям:
   - **Пользователи**: общее количество, по ролям, заблокированные, с резюме, верифицированные, активные
   - **Вакансии**: общее количество, активные/неактивные, созданные за период (сегодня, неделя, месяц)
   - **Заявки**: общее количество, распределение по статусам, средний match_score, созданные за период
   - **Уведомления**: общее количество, прочитанные/непрочитанные, созданные сегодня
   - **Топ навыков**: 10 самых популярных навыков в вакансиях с частотой упоминания

2. Временные метрики рассчитываются относительно текущего момента:
   - Сегодня: с начала текущего дня
   - Эта неделя: с начала текущей недели (понедельник)
   - Этот месяц: с начала текущего месяца

3. Статистика формируется на момент запроса и всегда актуальна

### Пример запроса

**Успешный запрос:**
```http
GET /admin/stats
Authorization: Bearer <token>
```

**Ответ (успех):**
```json
{
  "timestamp": "2025-01-15T10:30:00.123456+00:00",
  "users": {
    "total": 150,
    "candidates": 120,
    "hr_managers": 25,
    "admins": 5,
    "blocked": 3,
    "with_resume": 95,
    "verified": 80,
    "active": 147
  },
  "vacancies": {
    "total": 45,
    "active": 38,
    "inactive": 7,
    "created_today": 3,
    "created_this_week": 12,
    "created_this_month": 28
  },
  "applications": {
    "total": 320,
    "new": 150,
    "under_review": 80,
    "rejected": 60,
    "accepted": 30,
    "average_match_score": 68.5,
    "created_today": 15,
    "created_this_week": 95,
    "created_this_month": 280
  },
  "notifications": {
    "total": 500,
    "unread": 120,
    "read": 380,
    "created_today": 25
  },
  "top_skills": [
    {
      "skill": "Python",
      "count": 35,
      "percentage": 77.78
    },
    {
      "skill": "Docker",
      "count": 28,
      "percentage": 62.22
    },
    {
      "skill": "PostgreSQL",
      "count": 25,
      "percentage": 55.56
    },
    {
      "skill": "FastAPI",
      "count": 22,
      "percentage": 48.89
    },
    {
      "skill": "Git",
      "count": 20,
      "percentage": 44.44
    },
    {
      "skill": "JavaScript",
      "count": 18,
      "percentage": 40.0
    },
    {
      "skill": "React",
      "count": 15,
      "percentage": 33.33
    },
    {
      "skill": "TypeScript",
      "count": 12,
      "percentage": 26.67
    },
    {
      "skill": "Kubernetes",
      "count": 10,
      "percentage": 22.22
    },
    {
      "skill": "Linux",
      "count": 8,
      "percentage": 17.78
    }
  ]
}
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Создать дашборд статистики:**
   - Отобразить все метрики в удобном виде (карточки, графики, таблицы)
   - Показать временные тренды (сколько новых пользователей/вакансий/заявок за период)
   - Визуализировать распределение по статусам (pie charts, bar charts)

2. **Визуализация данных:**
   - Использовать графики для отображения временных метрик
   - Показать топ навыков в виде гистограммы или таблицы
   - Использовать цветовую индикацию для разных статусов

3. **Интерактивность:**
   - Возможность выбора периода для отображения (опционально, если добавить фильтры на бэкенде)
   - Автообновление статистики

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="platform-statistics">
    <h1>Статистика платформы</h1>
    
    <div v-if="loading">Загрузка статистики...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="stats">
      <div class="timestamp">
        Обновлено: {{ formatTimestamp(stats.timestamp) }}
      </div>

      <!-- Пользователи -->
      <div class="section">
        <h2>Пользователи</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Всего пользователей</h3>
            <div class="stat-value">{{ stats.users.total }}</div>
          </div>
          <div class="stat-card">
            <h3>Кандидаты</h3>
            <div class="stat-value">{{ stats.users.candidates }}</div>
            <div class="stat-detail">С резюме: {{ stats.users.with_resume }}</div>
          </div>
          <div class="stat-card">
            <h3>HR-менеджеры</h3>
            <div class="stat-value">{{ stats.users.hr_managers }}</div>
          </div>
          <div class="stat-card">
            <h3>Заблокировано</h3>
            <div class="stat-value error">{{ stats.users.blocked }}</div>
          </div>
          <div class="stat-card">
            <h3>Активных</h3>
            <div class="stat-value">{{ stats.users.active }}</div>
          </div>
          <div class="stat-card">
            <h3>Верифицированных</h3>
            <div class="stat-value">{{ stats.users.verified }}</div>
          </div>
        </div>
      </div>

      <!-- Вакансии -->
      <div class="section">
        <h2>Вакансии</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Всего вакансий</h3>
            <div class="stat-value">{{ stats.vacancies.total }}</div>
            <div class="stat-detail">Активных: {{ stats.vacancies.active }}</div>
          </div>
          <div class="stat-card">
            <h3>Создано сегодня</h3>
            <div class="stat-value">{{ stats.vacancies.created_today }}</div>
          </div>
          <div class="stat-card">
            <h3>Создано на этой неделе</h3>
            <div class="stat-value">{{ stats.vacancies.created_this_week }}</div>
          </div>
          <div class="stat-card">
            <h3>Создано в этом месяце</h3>
            <div class="stat-value">{{ stats.vacancies.created_this_month }}</div>
          </div>
        </div>
      </div>

      <!-- Заявки -->
      <div class="section">
        <h2>Заявки</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Всего заявок</h3>
            <div class="stat-value">{{ stats.applications.total }}</div>
          </div>
          <div class="stat-card">
            <h3>Новых</h3>
            <div class="stat-value">{{ stats.applications.new }}</div>
          </div>
          <div class="stat-card">
            <h3>На рассмотрении</h3>
            <div class="stat-value">{{ stats.applications.under_review }}</div>
          </div>
          <div class="stat-card">
            <h3>Отклонено</h3>
            <div class="stat-value error">{{ stats.applications.rejected }}</div>
          </div>
          <div class="stat-card">
            <h3>Принято</h3>
            <div class="stat-value success">{{ stats.applications.accepted }}</div>
          </div>
          <div class="stat-card">
            <h3>Средний match_score</h3>
            <div class="stat-value">{{ stats.applications.average_match_score }}%</div>
          </div>
          <div class="stat-card">
            <h3>Создано сегодня</h3>
            <div class="stat-value">{{ stats.applications.created_today }}</div>
          </div>
          <div class="stat-card">
            <h3>Создано на этой неделе</h3>
            <div class="stat-value">{{ stats.applications.created_this_week }}</div>
          </div>
        </div>
      </div>

      <!-- Уведомления -->
      <div class="section">
        <h2>Уведомления</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Всего уведомлений</h3>
            <div class="stat-value">{{ stats.notifications.total }}</div>
          </div>
          <div class="stat-card">
            <h3>Непрочитанных</h3>
            <div class="stat-value warning">{{ stats.notifications.unread }}</div>
          </div>
          <div class="stat-card">
            <h3>Прочитанных</h3>
            <div class="stat-value">{{ stats.notifications.read }}</div>
          </div>
          <div class="stat-card">
            <h3>Создано сегодня</h3>
            <div class="stat-value">{{ stats.notifications.created_today }}</div>
          </div>
        </div>
      </div>

      <!-- Топ навыков -->
      <div class="section">
        <h2>Топ-10 популярных навыков</h2>
        <div class="skills-table">
          <table>
            <thead>
              <tr>
                <th>Место</th>
                <th>Навык</th>
                <th>Количество вакансий</th>
                <th>Процент</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(skill, index) in stats.top_skills" :key="skill.skill">
                <td>{{ index + 1 }}</td>
                <td><strong>{{ skill.skill }}</strong></td>
                <td>{{ skill.count }}</td>
                <td>
                  <div class="percentage-bar">
                    <div
                      class="percentage-fill"
                      :style="{ width: `${skill.percentage}%` }"
                    ></div>
                    <span>{{ skill.percentage }}%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <button @click="loadStatistics" class="refresh-button">Обновить</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { PlatformStatistics } from '~/types'

const stats = ref<PlatformStatistics | null>(null)
const loading = ref(false)
const error = ref('')
let refreshInterval: ReturnType<typeof setInterval> | null = null

const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleString('ru-RU')
}

const loadStatistics = async () => {
  loading.value = true
  error.value = ''

  try {
    const data = await $fetch<PlatformStatistics>('/admin/stats', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })

    stats.value = data
  } catch (err: any) {
    error.value = 'Ошибка при загрузке статистики'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStatistics()
  // Автообновление каждые 5 минут
  refreshInterval = setInterval(loadStatistics, 300000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.platform-statistics {
  padding: 20px;
}

.timestamp {
  text-align: right;
  color: #999;
  font-size: 0.9em;
  margin-bottom: 30px;
}

.section {
  margin-bottom: 40px;
}

.section h2 {
  margin-bottom: 20px;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-card {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  border: 2px solid #e0e0e0;
}

.stat-card h3 {
  margin: 0 0 10px 0;
  font-size: 0.9em;
  color: #666;
  text-transform: uppercase;
}

.stat-value {
  font-size: 2em;
  font-weight: bold;
  color: #333;
  margin: 10px 0;
}

.stat-value.error {
  color: #dc3545;
}

.stat-value.success {
  color: #28a745;
}

.stat-value.warning {
  color: #ffc107;
}

.stat-detail {
  font-size: 0.9em;
  color: #666;
  margin-top: 5px;
}

.skills-table {
  overflow-x: auto;
}

.skills-table table {
  width: 100%;
  border-collapse: collapse;
  background-color: white;
}

.skills-table th,
.skills-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.skills-table th {
  background-color: #f5f5f5;
  font-weight: bold;
  color: #333;
}

.percentage-bar {
  position: relative;
  width: 100%;
  height: 24px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.percentage-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: #2196f3;
  transition: width 0.3s ease;
}

.percentage-bar span {
  position: relative;
  z-index: 1;
  padding: 0 8px;
  line-height: 24px;
  font-weight: bold;
  color: #333;
}

.refresh-button {
  margin-top: 20px;
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.refresh-button:hover {
  background-color: #0056b3;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `GET /admin/stats` - расширенный эндпоинт для получения детальной статистики платформы

### Совместимость

- Эндпоинт доступен только для администраторов (требует токен авторизации с ролью ADMIN)
- Все метрики рассчитываются в реальном времени при каждом запросе
- Существующие интеграции будут работать, но теперь получат больше данных
- Схема ответа изменена с простого словаря на структурированную модель

### Дополнительные заметки

- Статистика формируется синхронно при каждом запросе - для больших объемов данных может потребоваться кэширование
- Топ навыков ограничен 10 позициями для оптимальной производительности
- Временные метрики рассчитываются относительно UTC времени
- В будущем можно добавить кэширование статистики и исторические данные для трендов
- Можно добавить параметры фильтрации по датам для более гибкой аналитики

---

## Шаблоны вакансий для HR-менеджеров

### Описание изменений

Добавлена функциональность создания и управления шаблонами вакансий для HR-менеджеров. Теперь HR может создавать шаблоны вакансий и быстро создавать новые вакансии на основе этих шаблонов, экономя время и обеспечивая единообразие описаний.

### Что было изменено

**Файл:** `app/models/vacancy_template.py` (новый)
- Создана модель `VacancyTemplate` для хранения шаблонов вакансий
- Шаблон содержит: название шаблона, заголовок, описание, требуемые навыки
- Каждый шаблон связан с HR-менеджером, который его создал

**Файл:** `app/schemas/vacancy_template.py` (новый)
- Созданы схемы для работы с шаблонами:
  - `VacancyTemplateCreate` - создание шаблона
  - `VacancyTemplateUpdate` - обновление шаблона
  - `VacancyTemplateRead` - чтение шаблона

**Файл:** `app/schemas/vacancy.py`
- Добавлена схема `VacancyFromTemplate` для создания вакансии из шаблона с возможностью переопределения полей

**Файл:** `app/routers/hr.py`
- Добавлены CRUD эндпоинты для шаблонов:
  - `POST /hr/templates` - создание шаблона
  - `GET /hr/templates` - получение всех шаблонов HR-менеджера
  - `GET /hr/templates/{template_id}` - получение конкретного шаблона
  - `PATCH /hr/templates/{template_id}` - обновление шаблона
  - `DELETE /hr/templates/{template_id}` - удаление шаблона
  - `POST /hr/templates/{template_id}/create-vacancy` - создание вакансии из шаблона

**Миграция:** `alembic/versions/8a7f9c1d2e3f_add_vacancy_templates_table.py`
- Создана миграция для таблицы `vacancy_templates`

### Как это работает

1. **Создание шаблона:**
   - HR-менеджер создает шаблон с названием, заголовком, описанием и навыками
   - Шаблон сохраняется и привязывается к HR-менеджеру

2. **Использование шаблона:**
   - При создании вакансии из шаблона все поля берутся из шаблона
   - Можно переопределить любое поле (title, description, required_skills) в запросе
   - Если поле не указано, используется значение из шаблона

3. **Управление шаблонами:**
   - HR-менеджер видит только свои шаблоны
   - Можно редактировать и удалять свои шаблоны
   - Шаблоны не влияют на существующие вакансии

### Пример запроса

**Создание шаблона:**
```http
POST /hr/templates
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Python Developer Template",
  "title": "Python Backend Developer",
  "description": "Мы ищем опытного Python разработчика для работы над backend проектами",
  "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"]
}
```

**Ответ:**
```json
{
  "id": 1,
  "name": "Python Developer Template",
  "title": "Python Backend Developer",
  "description": "Мы ищем опытного Python разработчика для работы над backend проектами",
  "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
  "hr_id": 2,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

**Получение всех шаблонов:**
```http
GET /hr/templates
Authorization: Bearer <token>
```

**Создание вакансии из шаблона (без изменений):**
```http
POST /hr/templates/1/create-vacancy
Authorization: Bearer <token>
Content-Type: application/json

{
  "is_active": true
}
```

**Создание вакансии из шаблона (с изменениями):**
```http
POST /hr/templates/1/create-vacancy
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Senior Python Backend Developer",
  "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Git"],
  "is_active": true
}
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Создать раздел управления шаблонами:**
   - Список шаблонов HR-менеджера
   - Форма создания нового шаблона
   - Форма редактирования шаблона
   - Кнопка удаления шаблона

2. **Интеграция с созданием вакансии:**
   - При создании вакансии добавить опцию "Создать из шаблона"
   - Выпадающий список с доступными шаблонами
   - Автозаполнение полей данными из шаблона с возможностью редактирования

3. **Визуализация:**
   - Показывать название шаблона, заголовок и количество навыков
   - Добавить предпросмотр шаблона перед созданием вакансии

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="vacancy-templates">
    <h1>Шаблоны вакансий</h1>

    <!-- Список шаблонов -->
    <div class="templates-list">
      <div
        v-for="template in templates"
        :key="template.id"
        class="template-card"
      >
        <h3>{{ template.name }}</h3>
        <p class="template-title">{{ template.title }}</p>
        <div class="template-skills">
          <span
            v-for="skill in template.required_skills"
            :key="skill"
            class="skill-tag"
          >
            {{ skill }}
          </span>
        </div>
        <div class="template-actions">
          <button @click="editTemplate(template.id)">Редактировать</button>
          <button @click="createVacancyFromTemplate(template.id)">Создать вакансию</button>
          <button @click="deleteTemplate(template.id)" class="danger">Удалить</button>
        </div>
      </div>
    </div>

    <!-- Кнопка создания нового шаблона -->
    <button @click="showCreateForm = true" class="create-button">
      Создать новый шаблон
    </button>

    <!-- Форма создания/редактирования шаблона -->
    <div v-if="showCreateForm || editingTemplate" class="template-form">
      <h2>{{ editingTemplate ? 'Редактировать шаблон' : 'Создать шаблон' }}</h2>
      <form @submit.prevent="saveTemplate">
        <div class="form-group">
          <label>Название шаблона</label>
          <input v-model="form.name" type="text" required />
        </div>
        <div class="form-group">
          <label>Заголовок вакансии</label>
          <input v-model="form.title" type="text" required />
        </div>
        <div class="form-group">
          <label>Описание</label>
          <textarea v-model="form.description" required></textarea>
        </div>
        <div class="form-group">
          <label>Требуемые навыки</label>
          <div class="skills-input">
            <input
              v-model="newSkill"
              type="text"
              @keyup.enter="addSkill"
              placeholder="Введите навык и нажмите Enter"
            />
            <button type="button" @click="addSkill">Добавить</button>
          </div>
          <div class="skills-list">
            <span
              v-for="(skill, index) in form.required_skills"
              :key="index"
              class="skill-tag"
            >
              {{ skill }}
              <button
                type="button"
                @click="removeSkill(index)"
                class="remove-skill"
              >
                ×
              </button>
            </span>
          </div>
        </div>
        <div class="form-actions">
          <button type="submit">Сохранить</button>
          <button type="button" @click="cancelForm">Отмена</button>
        </div>
      </form>
    </div>

    <!-- Модальное окно создания вакансии из шаблона -->
    <div v-if="creatingVacancy" class="modal">
      <div class="modal-content">
        <h2>Создать вакансию из шаблона</h2>
        <form @submit.prevent="confirmCreateVacancy">
          <div class="form-group">
            <label>Заголовок (можно изменить)</label>
            <input v-model="vacancyForm.title" type="text" />
          </div>
          <div class="form-group">
            <label>Описание (можно изменить)</label>
            <textarea v-model="vacancyForm.description"></textarea>
          </div>
          <div class="form-group">
            <label>Навыки (можно изменить)</label>
            <div class="skills-input">
              <input
                v-model="newVacancySkill"
                type="text"
                @keyup.enter="addVacancySkill"
              />
              <button type="button" @click="addVacancySkill">Добавить</button>
            </div>
            <div class="skills-list">
              <span
                v-for="(skill, index) in vacancyForm.required_skills"
                :key="index"
                class="skill-tag"
              >
                {{ skill }}
                <button
                  type="button"
                  @click="removeVacancySkill(index)"
                  class="remove-skill"
                >
                  ×
                </button>
              </span>
            </div>
          </div>
          <div class="form-group">
            <label>
              <input v-model="vacancyForm.is_active" type="checkbox" />
              Вакансия активна сразу
            </label>
          </div>
          <div class="form-actions">
            <button type="submit">Создать вакансию</button>
            <button type="button" @click="creatingVacancy = false">Отмена</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

interface VacancyTemplate {
  id: number
  name: string
  title: string
  description: string
  required_skills: string[]
  hr_id: number
  created_at: string
  updated_at: string
}

const router = useRouter()
const templates = ref<VacancyTemplate[]>([])
const loading = ref(false)
const showCreateForm = ref(false)
const editingTemplate = ref<VacancyTemplate | null>(null)
const creatingVacancy = ref(false)
const selectedTemplateId = ref<number | null>(null)

const form = ref({
  name: '',
  title: '',
  description: '',
  required_skills: [] as string[]
})

const vacancyForm = ref({
  title: '',
  description: '',
  required_skills: [] as string[],
  is_active: true
})

const newSkill = ref('')
const newVacancySkill = ref('')

const addSkill = () => {
  if (newSkill.value.trim() && !form.value.required_skills.includes(newSkill.value.trim())) {
    form.value.required_skills.push(newSkill.value.trim())
    newSkill.value = ''
  }
}

const removeSkill = (index: number) => {
  form.value.required_skills.splice(index, 1)
}

const addVacancySkill = () => {
  if (newVacancySkill.value.trim() && !vacancyForm.value.required_skills.includes(newVacancySkill.value.trim())) {
    vacancyForm.value.required_skills.push(newVacancySkill.value.trim())
    newVacancySkill.value = ''
  }
}

const removeVacancySkill = (index: number) => {
  vacancyForm.value.required_skills.splice(index, 1)
}

const loadTemplates = async () => {
  loading.value = true
  try {
    const data = await $fetch<VacancyTemplate[]>('/hr/templates', {
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })
    templates.value = data
  } catch (err) {
    console.error('Ошибка загрузки шаблонов:', err)
  } finally {
    loading.value = false
  }
}

const saveTemplate = async () => {
  try {
    if (editingTemplate.value) {
      await $fetch(`/hr/templates/${editingTemplate.value.id}`, {
        method: 'PATCH',
        body: form.value,
        headers: {
          Authorization: `Bearer ${useAuth().token.value}`
        }
      })
    } else {
      await $fetch('/hr/templates', {
        method: 'POST',
        body: form.value,
        headers: {
          Authorization: `Bearer ${useAuth().token.value}`
        }
      })
    }
    cancelForm()
    loadTemplates()
  } catch (err) {
    console.error('Ошибка сохранения шаблона:', err)
  }
}

const editTemplate = async (id: number) => {
  const template = templates.value.find(t => t.id === id)
  if (template) {
    editingTemplate.value = template
    form.value = {
      name: template.name,
      title: template.title,
      description: template.description,
      required_skills: [...template.required_skills]
    }
  }
}

const deleteTemplate = async (id: number) => {
  if (!confirm('Вы уверены, что хотите удалить этот шаблон?')) return
  
  try {
    await $fetch(`/hr/templates/${id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })
    loadTemplates()
  } catch (err) {
    console.error('Ошибка удаления шаблона:', err)
  }
}

const createVacancyFromTemplate = async (templateId: number) => {
  const template = templates.value.find(t => t.id === templateId)
  if (template) {
    selectedTemplateId.value = templateId
    vacancyForm.value = {
      title: template.title,
      description: template.description,
      required_skills: [...template.required_skills],
      is_active: true
    }
    creatingVacancy.value = true
  }
}

const confirmCreateVacancy = async () => {
  try {
    const vacancy = await $fetch(`/hr/templates/${selectedTemplateId.value}/create-vacancy`, {
      method: 'POST',
      body: {
        title: vacancyForm.value.title || undefined,
        description: vacancyForm.value.description || undefined,
        required_skills: vacancyForm.value.required_skills.length > 0 ? vacancyForm.value.required_skills : undefined,
        is_active: vacancyForm.value.is_active
      },
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })
    creatingVacancy.value = false
    router.push(`/hr/vacancies/${vacancy.id}`)
  } catch (err) {
    console.error('Ошибка создания вакансии:', err)
  }
}

const cancelForm = () => {
  showCreateForm.value = false
  editingTemplate.value = null
  form.value = {
    name: '',
    title: '',
    description: '',
    required_skills: []
  }
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.templates-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.template-card {
  padding: 20px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.template-card h3 {
  margin: 0 0 10px 0;
  color: #333;
}

.template-title {
  font-weight: bold;
  color: #666;
  margin: 10px 0;
}

.template-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin: 15px 0;
}

.skill-tag {
  display: inline-block;
  padding: 4px 8px;
  background-color: #e3f2fd;
  border-radius: 4px;
  font-size: 0.9em;
  position: relative;
}

.skill-tag .remove-skill {
  margin-left: 5px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2em;
  color: #999;
}

.template-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.template-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background-color: #2196f3;
  color: white;
}

.template-actions button.danger {
  background-color: #f44336;
}

.create-button {
  padding: 12px 24px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}

.template-form {
  margin-top: 30px;
  padding: 20px;
  border: 2px solid #2196f3;
  border-radius: 8px;
  background-color: white;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.form-group textarea {
  min-height: 100px;
  resize: vertical;
}

.skills-input {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.skills-input input {
  flex: 1;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 30px;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `POST /hr/templates` - создание нового шаблона
- `GET /hr/templates` - получение всех шаблонов HR-менеджера
- `GET /hr/templates/{template_id}` - получение конкретного шаблона
- `PATCH /hr/templates/{template_id}` - обновление шаблона
- `DELETE /hr/templates/{template_id}` - удаление шаблона
- `POST /hr/templates/{template_id}/create-vacancy` - создание вакансии из шаблона

### Совместимость

- Эндпоинты доступны только для HR-менеджеров (требуют токен авторизации с ролью HR)
- Каждый HR-менеджер видит и управляет только своими шаблонами
- Существующие эндпоинты не затронуты
- Для применения миграции нужно выполнить: `alembic upgrade head`

### Дополнительные заметки

- Шаблоны не связаны напрямую с вакансиями - после создания вакансии из шаблона связь теряется, изменения в шаблоне не влияют на существующие вакансии
- При создании вакансии из шаблона можно переопределить любое поле, если не указано - используется значение из шаблона
- Шаблоны хранятся отдельно от вакансий, что позволяет создавать множество вакансий из одного шаблона
- В будущем можно добавить общие шаблоны, доступные всем HR-менеджерам

---

## Поиск кандидатов по критериям для HR-менеджеров

### Описание изменений

Добавлена функциональность поиска кандидатов по различным критериям для HR-менеджеров. HR может искать кандидатов по навыкам, наличию резюме, статусу, а также рассчитывать соответствие кандидатов конкретным вакансиям.

### Что было изменено

**Файл:** `app/schemas/candidate_search.py` (новый)
- Создана схема `CandidateSearchFilters` для параметров поиска
- Создана схема `CandidateSearchResult` для результата поиска с информацией о кандидате и match_score

**Файл:** `app/routers/hr.py`
- Добавлен эндпоинт `GET /hr/candidates/search` для поиска кандидатов с различными фильтрами

### Как это работает

1. Эндпоинт поддерживает следующие критерии поиска:
   - **Навыки (skills)** - поиск кандидатов, у которых в резюме есть хотя бы один из указанных навыков
   - **Наличие резюме (has_resume)** - фильтр по наличию загруженного резюме
   - **Активность (is_active)** - фильтр по активности аккаунта
   - **Блокировка (is_blocked)** - фильтр по статусу блокировки (по умолчанию False - только незаблокированные)
   - **Вакансия (vacancy_id)** - ID вакансии для расчета match_score
   - **Минимальный match_score (min_match_score)** - минимальный процент совпадения с указанной вакансией
   - **Поиск по тексту (search_text)** - поиск по email, имени или тексту резюме

2. Если указан `vacancy_id`, система рассчитывает `match_score` для каждого кандидата на основе соответствия его резюме требованиям вакансии

3. Результаты сортируются:
   - Если указана вакансия - по match_score (от большего к меньшему)
   - Иначе - по email в алфавитном порядке

4. В результате поиска возвращается предпросмотр резюме (первые 200 символов)

### Пример запроса

**Поиск по навыкам:**
```http
GET /hr/candidates/search?skills=Python&skills=FastAPI&has_resume=true
Authorization: Bearer <token>
```

**Поиск кандидатов для конкретной вакансии:**
```http
GET /hr/candidates/search?vacancy_id=1&min_match_score=50.0&has_resume=true&is_blocked=false
Authorization: Bearer <token>
```

**Поиск по тексту:**
```http
GET /hr/candidates/search?search_text=backend&has_resume=true
Authorization: Bearer <token>
```

**Комбинированный поиск:**
```http
GET /hr/candidates/search?skills=Python&skills=Docker&has_resume=true&is_active=true&is_blocked=false&vacancy_id=1&min_match_score=60.0
Authorization: Bearer <token>
```

**Ответ (успех):**
```json
[
  {
    "id": 3,
    "email": "candidate@example.com",
    "full_name": "Иванов Иван Иванович",
    "has_resume": true,
    "is_active": true,
    "is_blocked": false,
    "match_score": 75.5,
    "resume_preview": "Опытный Python разработчик с 5-летним стажем. Работал с FastAPI, PostgreSQL, Docker. Участвовал в разработке микросервисной архитектуры..."
  },
  {
    "id": 5,
    "email": "developer@example.com",
    "full_name": "Петров Петр Петрович",
    "has_resume": true,
    "is_active": true,
    "is_blocked": false,
    "match_score": 66.67,
    "resume_preview": "Backend разработчик на Python. Опыт работы с Django, FastAPI, PostgreSQL..."
  }
]
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Создать страницу поиска кандидатов:**
   - Форма с полями для фильтров поиска
   - Выпадающий список вакансий для выбора (для расчета match_score)
   - Множественный выбор навыков
   - Чекбоксы для фильтров (has_resume, is_active, is_blocked)
   - Поле для текстового поиска

2. **Отображение результатов:**
   - Список найденных кандидатов с информацией
   - Отображение match_score с цветовой индикацией (если рассчитан)
   - Показ предпросмотра резюме
   - Сортировка результатов

3. **Дополнительные функции:**
   - Возможность просмотра полного резюме кандидата
   - Возможность создания заявки от имени кандидата (если есть такая функциональность)
   - Сохранение избранных кандидатов

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="candidate-search">
    <h1>Поиск кандидатов</h1>

    <!-- Форма поиска -->
    <div class="search-form">
      <div class="form-group">
        <label>Навыки</label>
        <div class="skills-input">
          <input
            v-model="newSkill"
            type="text"
            @keyup.enter="addSkill"
            placeholder="Введите навык и нажмите Enter"
          />
          <button type="button" @click="addSkill">Добавить</button>
        </div>
        <div class="skills-list">
          <span
            v-for="(skill, index) in filters.skills"
            :key="index"
            class="skill-tag"
          >
            {{ skill }}
            <button type="button" @click="removeSkill(index)" class="remove-skill">
              ×
            </button>
          </span>
        </div>
      </div>

      <div class="form-group">
        <label>Вакансия для расчета соответствия</label>
        <select v-model="filters.vacancy_id">
          <option :value="null">Не указывать</option>
          <option v-for="vacancy in vacancies" :key="vacancy.id" :value="vacancy.id">
            {{ vacancy.title }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label>Минимальный match_score</label>
        <input
          v-model.number="filters.min_match_score"
          type="number"
          min="0"
          max="100"
          step="1"
          :disabled="!filters.vacancy_id"
        />
      </div>

      <div class="form-group">
        <label>Поиск по тексту</label>
        <input
          v-model="filters.search_text"
          type="text"
          placeholder="Email, имя или текст из резюме"
        />
      </div>

      <div class="form-group">
        <label>
          <input
            v-model="filters.has_resume"
            type="checkbox"
          />
          Только с резюме
        </label>
      </div>

      <div class="form-group">
        <label>
          <input
            v-model="filters.is_active"
            type="checkbox"
          />
          Только активные
        </label>
      </div>

      <button @click="searchCandidates" class="search-button">Найти</button>
    </div>

    <!-- Результаты поиска -->
    <div v-if="loading" class="loading">Поиск...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="results.length === 0" class="no-results">
      Кандидаты не найдены
    </div>
    <div v-else class="results">
      <div class="results-count">Найдено: {{ results.length }}</div>
      <div class="candidates-list">
        <div
          v-for="candidate in results"
          :key="candidate.id"
          class="candidate-card"
        >
          <div class="candidate-header">
            <h3>{{ candidate.full_name || candidate.email }}</h3>
            <div v-if="candidate.match_score !== null" class="match-score" :class="getMatchScoreClass(candidate.match_score)">
              Совпадение: {{ candidate.match_score }}%
            </div>
          </div>
          <div class="candidate-info">
            <p><strong>Email:</strong> {{ candidate.email }}</p>
            <p><strong>Статус:</strong>
              <span v-if="candidate.is_active" class="status active">Активен</span>
              <span v-else class="status inactive">Неактивен</span>
              <span v-if="candidate.is_blocked" class="status blocked">Заблокирован</span>
            </p>
            <p><strong>Резюме:</strong> {{ candidate.has_resume ? 'Загружено' : 'Не загружено' }}</p>
          </div>
          <div v-if="candidate.resume_preview" class="resume-preview">
            <strong>Предпросмотр резюме:</strong>
            <p>{{ candidate.resume_preview }}</p>
          </div>
          <div class="candidate-actions">
            <button @click="viewCandidate(candidate.id)">Просмотр</button>
            <button v-if="filters.vacancy_id" @click="createApplication(candidate.id, filters.vacancy_id)">
              Создать заявку
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface CandidateSearchResult {
  id: number
  email: string
  full_name: string | null
  has_resume: boolean
  is_active: boolean
  is_blocked: boolean
  match_score: number | null
  resume_preview: string | null
}

interface Vacancy {
  id: number
  title: string
}

const filters = ref({
  skills: [] as string[],
  has_resume: true,
  is_active: true,
  is_blocked: false,
  vacancy_id: null as number | null,
  min_match_score: null as number | null,
  search_text: ''
})

const results = ref<CandidateSearchResult[]>([])
const vacancies = ref<Vacancy[]>([])
const loading = ref(false)
const error = ref('')
const newSkill = ref('')

const getMatchScoreClass = (score: number) => {
  if (score >= 70) return 'high'
  if (score >= 50) return 'medium'
  return 'low'
}

const addSkill = () => {
  if (newSkill.value.trim() && !filters.value.skills.includes(newSkill.value.trim())) {
    filters.value.skills.push(newSkill.value.trim())
    newSkill.value = ''
  }
}

const removeSkill = (index: number) => {
  filters.value.skills.splice(index, 1)
}

const loadVacancies = async () => {
  try {
    const data = await $fetch<Vacancy[]>('/hr/vacancies', {
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })
    vacancies.value = data
  } catch (err) {
    console.error('Ошибка загрузки вакансий:', err)
  }
}

const searchCandidates = async () => {
  loading.value = true
  error.value = ''

  try {
    const params: any = {
      has_resume: filters.value.has_resume,
      is_active: filters.value.is_active,
      is_blocked: filters.value.is_blocked
    }

    if (filters.value.skills.length > 0) {
      params.skills = filters.value.skills
    }

    if (filters.value.vacancy_id) {
      params.vacancy_id = filters.value.vacancy_id
    }

    if (filters.value.min_match_score !== null && filters.value.vacancy_id) {
      params.min_match_score = filters.value.min_match_score
    }

    if (filters.value.search_text) {
      params.search_text = filters.value.search_text
    }

    const data = await $fetch<CandidateSearchResult[]>('/hr/candidates/search', {
      method: 'GET',
      params,
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })

    results.value = data
  } catch (err: any) {
    error.value = 'Ошибка при поиске кандидатов'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const viewCandidate = (candidateId: number) => {
  // Навигация к профилю кандидата
  // router.push(`/hr/candidates/${candidateId}`)
}

const createApplication = async (candidateId: number, vacancyId: number) => {
  // Создание заявки от имени кандидата (если есть такая функциональность)
  // или навигация к форме создания заявки
}

onMounted(() => {
  loadVacancies()
})
</script>

<style scoped>
.search-form {
  background-color: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.skills-input {
  display: flex;
  gap: 10px;
}

.skills-input input {
  flex: 1;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 10px;
}

.skill-tag {
  display: inline-block;
  padding: 4px 8px;
  background-color: #e3f2fd;
  border-radius: 4px;
  font-size: 0.9em;
}

.remove-skill {
  margin-left: 5px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2em;
  color: #999;
}

.search-button {
  padding: 12px 24px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}

.candidate-card {
  padding: 20px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 20px;
  background-color: white;
}

.candidate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.match-score {
  padding: 5px 10px;
  border-radius: 4px;
  font-weight: bold;
}

.match-score.high {
  background-color: #4caf50;
  color: white;
}

.match-score.medium {
  background-color: #ff9800;
  color: white;
}

.match-score.low {
  background-color: #f44336;
  color: white;
}

.status {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
  margin-left: 5px;
}

.status.active {
  background-color: #4caf50;
  color: white;
}

.status.inactive {
  background-color: #999;
  color: white;
}

.status.blocked {
  background-color: #f44336;
  color: white;
}

.resume-preview {
  margin-top: 15px;
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.candidate-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.candidate-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background-color: #2196f3;
  color: white;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `GET /hr/candidates/search` - новый эндпоинт для поиска кандидатов по критериям

### Совместимость

- Эндпоинт доступен только для HR-менеджеров (требует токен авторизации с ролью HR)
- Все фильтры опциональны и могут комбинироваться
- Поиск по навыкам работает только для кандидатов с загруженным резюме
- Расчет match_score требует указания vacancy_id и наличия резюме у кандидата
- Существующие эндпоинты не затронуты

### Дополнительные заметки

- Поиск по навыкам использует простой поиск подстрок в тексте резюме (без учета регистра)
- Кандидат считается подходящим, если в его резюме есть хотя бы один из указанных навыков
- Поиск по тексту ищет в email, имени и тексте резюме одновременно
- Результаты автоматически сортируются по match_score (если рассчитан) или по email
- Предпросмотр резюме ограничен 200 символами для оптимизации ответа
- В будущем можно добавить полнотекстовый поиск с использованием PostgreSQL full-text search для более точных результатов
- Можно добавить пагинацию для больших результатов поиска

---

## Детальный анализ соответствия кандидатов вакансиям для HR-менеджеров

### Описание изменений

Добавлена функциональность детального анализа соответствия кандидатов требованиям вакансий. HR-менеджеры могут получить подробную информацию о том, почему кандидат подходит или не подходит на вакансию, с указанием конкретных навыков, которые есть или отсутствуют в резюме.

### Что было изменено

**Файл:** `app/services/candidate_analysis.py` (новый)
- Создан сервис `analyze_candidate_match()` для детального анализа соответствия кандидата вакансии
- Анализирует каждый требуемый навык и определяет, есть ли он в резюме
- Формирует объяснение соответствия с указанием найденных и отсутствующих навыков
- Определяет, проходит ли кандидат на вакансию (совпадение >= 50%)

**Файл:** `app/schemas/candidate_analysis.py` (новый)
- Созданы схемы для структурированного ответа:
  - `CandidateMatchAnalysis` - детальный анализ соответствия одного кандидата
  - `ApplicationAnalysis` - анализ заявки с информацией о кандидате
  - `VacancyApplicationsAnalysis` - общий анализ всех заявок на вакансию

**Файл:** `app/routers/hr.py`
- Добавлен эндпоинт `GET /hr/vacancies/{vacancy_id}/applications/analysis` для получения детального анализа всех заявок

### Как это работает

1. Эндпоинт получает все заявки на указанную вакансию
2. Для каждой заявки:
   - Проверяется наличие резюме у кандидата
   - Если резюме есть, проводится детальный анализ:
     - Каждый требуемый навык проверяется в тексте резюме
     - Формируются списки найденных и отсутствующих навыков
     - Рассчитывается процент совпадения (match_score)
     - Определяется, проходит ли кандидат (совпадение >= 50%)
     - Формируется объяснение с указанием причин
   - Если резюме отсутствует, возвращается ошибка

3. Результат включает:
   - Общую статистику (сколько кандидатов проходят, не проходят, без резюме)
   - Детальный анализ каждой заявки с объяснением

### Пример запроса

**Успешный запрос:**
```http
GET /hr/vacancies/1/applications/analysis
Authorization: Bearer <token>
```

**Ответ (успех):**
```json
{
  "vacancy_id": 1,
  "vacancy_title": "Python Backend Developer",
  "total_applications": 5,
  "passing_candidates": 3,
  "not_passing_candidates": 1,
  "applications_without_resume": 1,
  "applications": [
    {
      "application_id": 1,
      "candidate_id": 3,
      "candidate_email": "candidate1@example.com",
      "candidate_full_name": "Иванов Иван Иванович",
      "has_resume": true,
      "application_status": "new",
      "match_analysis": {
        "passes": true,
        "match_score": 75.0,
        "matched_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "missing_skills": ["Kubernetes"],
        "matched_skills_count": 4,
        "missing_skills_count": 1,
        "total_required_skills": 5,
        "explanation": "Кандидат хорошо подходит на вакансию. Совпадение: 75.0%. Найдено 4 из 5 требуемых навыков. Отсутствуют навыки: Kubernetes."
      },
      "error": null
    },
    {
      "application_id": 2,
      "candidate_id": 4,
      "candidate_email": "candidate2@example.com",
      "candidate_full_name": "Петров Петр Петрович",
      "has_resume": true,
      "application_status": "under_review",
      "match_analysis": {
        "passes": false,
        "match_score": 40.0,
        "matched_skills": ["Python", "Git"],
        "missing_skills": ["FastAPI", "PostgreSQL", "Docker"],
        "matched_skills_count": 2,
        "missing_skills_count": 3,
        "total_required_skills": 5,
        "explanation": "Кандидат не подходит на вакансию. Совпадение: 40.0%. Найдено только 2 из 5 требуемых навыков. Отсутствуют следующие навыки: FastAPI, PostgreSQL, Docker."
      },
      "error": null
    },
    {
      "application_id": 3,
      "candidate_id": 5,
      "candidate_email": "candidate3@example.com",
      "candidate_full_name": "Сидоров Сидор Сидорович",
      "has_resume": false,
      "application_status": "new",
      "match_analysis": null,
      "error": "У кандидата отсутствует резюме, невозможно провести анализ соответствия"
    }
  ]
}
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Создать страницу анализа заявок на вакансию:**
   - Показывать общую статистику (проходящие, не проходящие, без резюме)
   - Список всех заявок с детальным анализом каждой
   - Визуально выделять проходящих и не проходящих кандидатов

2. **Визуализация анализа:**
   - Цветовая индикация (зеленый для проходящих, красный для не проходящих, серый для без резюме)
   - Показывать списки найденных и отсутствующих навыков
   - Отображать объяснение соответствия
   - Показывать процент совпадения с прогресс-баром

3. **Дополнительные функции:**
   - Фильтрация по статусу (проходят/не проходят)
   - Сортировка по match_score
   - Возможность экспорта результатов анализа

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="applications-analysis">
    <h1>Анализ заявок на вакансию: {{ analysis?.vacancy_title }}</h1>

    <div v-if="loading">Загрузка анализа...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="analysis">
      <!-- Общая статистика -->
      <div class="statistics">
        <div class="stat-card passing">
          <h3>Проходящие кандидаты</h3>
          <div class="stat-value">{{ analysis.passing_candidates }}</div>
        </div>
        <div class="stat-card not-passing">
          <h3>Не проходящие кандидаты</h3>
          <div class="stat-value">{{ analysis.not_passing_candidates }}</div>
        </div>
        <div class="stat-card no-resume">
          <h3>Без резюме</h3>
          <div class="stat-value">{{ analysis.applications_without_resume }}</div>
        </div>
        <div class="stat-card total">
          <h3>Всего заявок</h3>
          <div class="stat-value">{{ analysis.total_applications }}</div>
        </div>
      </div>

      <!-- Список заявок -->
      <div class="applications-list">
        <div
          v-for="app in analysis.applications"
          :key="app.application_id"
          class="application-card"
          :class="getApplicationClass(app)"
        >
          <div class="application-header">
            <h3>{{ app.candidate_full_name || app.candidate_email }}</h3>
            <span class="status-badge" :class="app.application_status">
              {{ getStatusLabel(app.application_status) }}
            </span>
          </div>

          <div v-if="app.error" class="error-message">
            {{ app.error }}
          </div>

          <div v-else-if="app.match_analysis" class="match-analysis">
            <!-- Процент совпадения -->
            <div class="match-score-section">
              <div class="match-score-label">
                Совпадение: <strong>{{ app.match_analysis.match_score }}%</strong>
                <span :class="app.match_analysis.passes ? 'passes' : 'not-passes'">
                  {{ app.match_analysis.passes ? '✓ Проходит' : '✗ Не проходит' }}
                </span>
              </div>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :class="app.match_analysis.passes ? 'passes' : 'not-passes'"
                  :style="{ width: `${app.match_analysis.match_score}%` }"
                ></div>
              </div>
            </div>

            <!-- Объяснение -->
            <div class="explanation">
              {{ app.match_analysis.explanation }}
            </div>

            <!-- Найденные навыки -->
            <div v-if="app.match_analysis.matched_skills.length > 0" class="skills-section matched">
              <h4>Найденные навыки ({{ app.match_analysis.matched_skills_count }})</h4>
              <div class="skills-list">
                <span
                  v-for="skill in app.match_analysis.matched_skills"
                  :key="skill"
                  class="skill-tag matched"
                >
                  ✓ {{ skill }}
                </span>
              </div>
            </div>

            <!-- Отсутствующие навыки -->
            <div v-if="app.match_analysis.missing_skills.length > 0" class="skills-section missing">
              <h4>Отсутствующие навыки ({{ app.match_analysis.missing_skills_count }})</h4>
              <div class="skills-list">
                <span
                  v-for="skill in app.match_analysis.missing_skills"
                  :key="skill"
                  class="skill-tag missing"
                >
                  ✗ {{ skill }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

interface CandidateMatchAnalysis {
  passes: boolean
  match_score: number
  matched_skills: string[]
  missing_skills: string[]
  matched_skills_count: number
  missing_skills_count: number
  total_required_skills: number
  explanation: string
}

interface ApplicationAnalysis {
  application_id: number
  candidate_id: number
  candidate_email: string
  candidate_full_name: string | null
  has_resume: boolean
  application_status: string
  match_analysis: CandidateMatchAnalysis | null
  error: string | null
}

interface VacancyApplicationsAnalysis {
  vacancy_id: number
  vacancy_title: string
  total_applications: number
  passing_candidates: number
  not_passing_candidates: number
  applications_without_resume: number
  applications: ApplicationAnalysis[]
}

const route = useRoute()
const analysis = ref<VacancyApplicationsAnalysis | null>(null)
const loading = ref(false)
const error = ref('')

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    new: 'Новая',
    under_review: 'На рассмотрении',
    rejected: 'Отклонена',
    accepted: 'Принята'
  }
  return labels[status] || status
}

const getApplicationClass = (app: ApplicationAnalysis) => {
  if (app.error) return 'no-resume'
  if (app.match_analysis?.passes) return 'passing'
  return 'not-passing'
}

const loadAnalysis = async () => {
  loading.value = true
  error.value = ''
  const vacancyId = route.params.id

  try {
    const data = await $fetch<VacancyApplicationsAnalysis>(
      `/hr/vacancies/${vacancyId}/applications/analysis`,
      {
        headers: {
          Authorization: `Bearer ${useAuth().token.value}`
        }
      }
    )

    analysis.value = data
  } catch (err: any) {
    error.value = 'Ошибка при загрузке анализа'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAnalysis()
})
</script>

<style scoped>
.statistics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-card.passing {
  background-color: #d4edda;
  border: 2px solid #28a745;
}

.stat-card.not-passing {
  background-color: #f8d7da;
  border: 2px solid #dc3545;
}

.stat-card.no-resume {
  background-color: #fff3cd;
  border: 2px solid #ffc107;
}

.stat-card.total {
  background-color: #d1ecf1;
  border: 2px solid #17a2b8;
}

.stat-value {
  font-size: 2.5em;
  font-weight: bold;
  margin-top: 10px;
}

.application-card {
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 2px solid #e0e0e0;
}

.application-card.passing {
  border-color: #28a745;
  background-color: #f8fff9;
}

.application-card.not-passing {
  border-color: #dc3545;
  background-color: #fff8f8;
}

.application-card.no-resume {
  border-color: #ffc107;
  background-color: #fffef5;
}

.application-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.status-badge {
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: bold;
}

.status-badge.new {
  background-color: #007bff;
  color: white;
}

.status-badge.under_review {
  background-color: #ffc107;
  color: #333;
}

.status-badge.rejected {
  background-color: #dc3545;
  color: white;
}

.status-badge.accepted {
  background-color: #28a745;
  color: white;
}

.match-score-section {
  margin-bottom: 15px;
}

.match-score-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.match-score-label .passes {
  color: #28a745;
  font-weight: bold;
}

.match-score-label .not-passes {
  color: #dc3545;
  font-weight: bold;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.progress-fill.passes {
  background-color: #28a745;
}

.progress-fill.not-passes {
  background-color: #dc3545;
}

.explanation {
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
  margin-bottom: 15px;
  font-style: italic;
}

.skills-section {
  margin-bottom: 15px;
}

.skills-section.matched h4 {
  color: #28a745;
}

.skills-section.missing h4 {
  color: #dc3545;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.skill-tag {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.9em;
}

.skill-tag.matched {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #28a745;
}

.skill-tag.missing {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #dc3545;
}

.error-message {
  padding: 10px;
  background-color: #fff3cd;
  color: #856404;
  border-radius: 4px;
  border: 1px solid #ffc107;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `GET /hr/vacancies/{vacancy_id}/applications/analysis` - новый эндпоинт для получения детального анализа всех заявок на вакансию

### Совместимость

- Эндпоинт доступен только для HR-менеджеров (требует токен авторизации с ролью HR)
- HR-менеджер может получить анализ только для своих вакансий
- Если у кандидата нет резюме, анализ не выполняется, возвращается соответствующее сообщение
- Существующие эндпоинты не затронуты

### Дополнительные заметки

- Кандидат считается проходящим на вакансию, если совпадение >= 50%
- Анализ проводится на основе простого поиска подстрок в тексте резюме (без учета регистра)
- Для каждого кандидата указывается точный список найденных и отсутствующих навыков
- Объяснение формируется автоматически на основе результатов анализа
- В будущем можно улучшить алгоритм анализа, добавив синонимы навыков или использование NLP
- Можно добавить весовые коэффициенты для разных навыков (более важные навыки имеют больший вес)

---

## Уведомления HR-менеджеров о подходящих кандидатах

### Описание изменений

Добавлена функциональность уведомлений для HR-менеджеров. Когда на вакансию откликается кандидат, который подходит на эту вакансию по резюме (match_score >= 50%), HR-менеджер получает уведомление.

### Что было изменено

**Файл:** `app/routers/candidates.py`
- Модифицирована логика создания заявки
- Добавлено создание уведомления для HR-менеджера при подходящем кандидате (match_score >= 50%)
- Уведомление содержит информацию о кандидате и проценте совпадения

**Файл:** `app/routers/hr.py`
- Добавлен эндпоинт `GET /hr/notifications` для получения уведомлений HR-менеджера
- Добавлен эндпоинт `PATCH /hr/notifications/{notification_id}/read` для отметки уведомления как прочитанного

### Как это работает

1. Когда кандидат подает заявку на вакансию:
   - Рассчитывается match_score (процент совпадения резюме с требованиями вакансии)
   - Создается уведомление для кандидата (как было ранее)
   - Если match_score >= 50%, создается уведомление для HR-менеджера, который создал вакансию

2. Уведомление для HR содержит:
   - Название вакансии
   - Имя кандидата (или email, если имя не указано)
   - Процент совпадения

3. HR-менеджер может:
   - Просматривать все свои уведомления через эндпоинт `/hr/notifications`
   - Отмечать уведомления как прочитанные
   - Уведомления сортируются по дате создания (новые сверху)

### Пример запроса

**Получение уведомлений HR-менеджера:**
```http
GET /hr/notifications
Authorization: Bearer <token>
```

**Ответ (успех):**
```json
[
  {
    "id": 1,
    "user_id": 2,
    "message": "На вакансию 'Python Backend Developer' откликнулся подходящий кандидат: Иванов Иван Иванович. Совпадение: 75%",
    "is_read": false,
    "created_at": "2025-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "user_id": 2,
    "message": "На вакансию 'Frontend Developer' откликнулся подходящий кандидат: Петров Петр Петрович. Совпадение: 60%",
    "is_read": true,
    "created_at": "2025-01-14T15:20:00Z"
  }
]
```

**Отметить уведомление как прочитанное:**
```http
PATCH /hr/notifications/1/read
Authorization: Bearer <token>
```

### Интеграция с фронтендом

#### Что нужно сделать на фронтенде:

1. **Добавить раздел уведомлений для HR:**
   - Отобразить список уведомлений
   - Визуально выделять непрочитанные уведомления
   - Показывать счетчик непрочитанных уведомлений

2. **Функциональность:**
   - Автоматическое обновление уведомлений (polling или websockets)
   - Возможность отметить все уведомления как прочитанные
   - Фильтрация уведомлений (все, непрочитанные, прочитанные)
   - При клике на уведомление - переход к заявкам на соответствующую вакансию

3. **Визуализация:**
   - Бейдж с количеством непрочитанных уведомлений в навигации
   - Выделение новых уведомлений цветом или иконкой
   - Группировка уведомлений по вакансиям (опционально)

#### Пример для Nuxt 3 (Composition API):

```vue
<template>
  <div class="hr-notifications">
    <h1>Уведомления</h1>

    <div v-if="loading">Загрузка уведомлений...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="notifications-header">
        <div class="stats">
          Всего: {{ notifications.length }} | 
          Непрочитанных: {{ unreadCount }}
        </div>
        <button @click="markAllAsRead" v-if="unreadCount > 0" class="mark-all-read">
          Отметить все как прочитанные
        </button>
      </div>

      <div v-if="notifications.length === 0" class="no-notifications">
        Уведомлений нет
      </div>

      <div v-else class="notifications-list">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          class="notification-item"
          :class="{ 'unread': !notification.is_read }"
        >
          <div class="notification-content">
            <p class="notification-message">{{ notification.message }}</p>
            <div class="notification-meta">
              <span class="notification-date">
                {{ formatDate(notification.created_at) }}
              </span>
              <span v-if="!notification.is_read" class="unread-badge">Новое</span>
            </div>
          </div>
          <div class="notification-actions">
            <button
              v-if="!notification.is_read"
              @click="markAsRead(notification.id)"
              class="mark-read-button"
            >
              Отметить как прочитанное
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface Notification {
  id: number
  user_id: number
  message: string
  is_read: boolean
  created_at: string
}

const notifications = ref<Notification[]>([])
const loading = ref(false)
const error = ref('')
let refreshInterval: ReturnType<typeof setInterval> | null = null

const unreadCount = computed(() => {
  return notifications.value.filter(n => !n.is_read).length
})

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('ru-RU')
}

const loadNotifications = async () => {
  loading.value = true
  error.value = ''

  try {
    const data = await $fetch<Notification[]>('/hr/notifications', {
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })

    notifications.value = data
  } catch (err: any) {
    error.value = 'Ошибка при загрузке уведомлений'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const markAsRead = async (notificationId: number) => {
  try {
    await $fetch(`/hr/notifications/${notificationId}/read`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${useAuth().token.value}`
      }
    })

    // Обновляем локальное состояние
    const notification = notifications.value.find(n => n.id === notificationId)
    if (notification) {
      notification.is_read = true
    }
  } catch (err) {
    console.error('Ошибка при отметке уведомления:', err)
  }
}

const markAllAsRead = async () => {
  const unreadNotifications = notifications.value.filter(n => !n.is_read)
  
  try {
    await Promise.all(
      unreadNotifications.map(n => markAsRead(n.id))
    )
  } catch (err) {
    console.error('Ошибка при отметке всех уведомлений:', err)
  }
}

onMounted(() => {
  loadNotifications()
  // Автообновление каждые 30 секунд
  refreshInterval = setInterval(loadNotifications, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.hr-notifications {
  padding: 20px;
}

.notifications-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.mark-all-read {
  padding: 8px 16px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.notifications-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.notification-item {
  padding: 20px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  background-color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notification-item.unread {
  border-color: #2196f3;
  background-color: #e3f2fd;
}

.notification-content {
  flex: 1;
}

.notification-message {
  margin: 0 0 10px 0;
  font-size: 1.1em;
  color: #333;
}

.notification-meta {
  display: flex;
  gap: 15px;
  align-items: center;
  font-size: 0.9em;
  color: #666;
}

.unread-badge {
  padding: 3px 8px;
  background-color: #f44336;
  color: white;
  border-radius: 3px;
  font-size: 0.85em;
  font-weight: bold;
}

.notification-actions {
  margin-left: 20px;
}

.mark-read-button {
  padding: 8px 16px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.mark-read-button:hover {
  background-color: #45a049;
}

.no-notifications {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 1.2em;
}
</style>
```

### Эндпоинты, затронутые изменениями

- `POST /candidates/applications` - модифицирован для создания уведомлений HR (если кандидат подходит)
- `GET /hr/notifications` - новый эндпоинт для получения уведомлений HR-менеджера
- `PATCH /hr/notifications/{notification_id}/read` - новый эндпоинт для отметки уведомления как прочитанного

### Совместимость

- Уведомления создаются только если кандидат подходит на вакансию (match_score >= 50%)
- HR-менеджер получает уведомления только о подходящих кандидатах на свои вакансии
- Существующие уведомления для кандидатов не изменены
- Существующие эндпоинты не затронуты (кроме логики создания заявки, которая расширена)

### Дополнительные заметки

- Порог для создания уведомления HR установлен на 50% совпадения (можно изменить при необходимости)
- Уведомления создаются только при создании новой заявки
- Если кандидат не подходит (match_score < 50%), уведомление HR не создается
- В будущем можно добавить настройки для HR-менеджера (порог match_score для уведомлений, email-уведомления и т.д.)
- Можно добавить группировку уведомлений по вакансиям или периодам

