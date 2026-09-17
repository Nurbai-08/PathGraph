# PathGraph

PathGraph превращает учебные материалы в интерактивный граф знаний и персональный маршрут
обучения.

## Возможности

- Firebase Authentication, защищённая cookie-сессия и приватные рабочие пространства;
- загрузка URL, текста и PDF, очистка, семантическое разбиение и возобновляемые задания;
- Ollama и Gemini, зашифрованные API-ключи, извлечение понятий и связей с provenance;
- экономичная Gemini Flash Lite по умолчанию и ограничение размера одного AI-анализа;
- обзор и фокус-режим графа, поиск, фильтры, выбор графа отдельного материала и карточки понятий;
- детерминированные учебные пути, пробелы, статусы освоения и тесты;
- RAG-объяснения, сравнение, «почему это важно» и чат по графу с проверенными цитатами.
- русские материалы обрабатываются на русском, английские — на русском и английском.

## Запуск через Docker

Создайте локальный файл окружения, заполните Firebase-параметры и обязательно замените секрет:

```bash
cp .env.example .env
# Отредактируйте JWT_SECRET в .env
docker compose up --build
```

Интерфейс: `http://localhost:5173`. API и Swagger UI: `http://localhost:8000` и
`http://localhost:8000/docs`.

## Локальная разработка

Скопируйте `.env.example` в `.env`. Один корневой файл читают и backend, и Vite.

Backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
DATABASE_URL=sqlite+pysqlite:///./pathgraph.db JWT_SECRET=local-development-secret \
  .venv/bin/alembic upgrade head
DATABASE_URL=sqlite+pysqlite:///./pathgraph.db JWT_SECRET=local-development-secret \
  .venv/bin/uvicorn app.main:app --reload
```

Frontend во втором терминале:

```bash
cd frontend
npm ci
npm run dev
```

SQLite подходит для локальной разработки и тестов; Docker Compose использует PostgreSQL.

## Firebase Authentication

В Firebase Console включите `Authentication → Sign-in method → Email/Password`. Из настроек Web
App перенесите `apiKey`, `authDomain`, `projectId` и `appId` в соответствующие
`VITE_FIREBASE_*` переменные. Backend проверяет полученный ID token через Firebase Admin; укажите
тот же `FIREBASE_PROJECT_ID` и путь `GOOGLE_APPLICATION_CREDENTIALS` к service-account JSON.
Сам JSON не добавляйте в Git — подходящие имена уже исключены в `.gitignore`.
Для контейнера значение можно передать через secret-переменную `FIREBASE_CREDENTIALS_JSON`;
не фиксируйте её в репозитории.

Для проверки без внешних ключей можно временно запустить backend с
`LOCAL_AUTH_ENABLED=true DEMO_GRAPH_ENABLED=true`, а frontend с
`VITE_LOCAL_AUTH_ENABLED=true`. Эти флаги выключены по умолчанию и предназначены только для
локальной демонстрации. Готовый файл находится в
[`sample-data/neural-networks.pdf`](./sample-data/neural-networks.pdf).

## Проверки

```bash
cd frontend
npm run typecheck
npm run lint
npm run build

cd ../backend
DATABASE_URL=sqlite+pysqlite:///./pathgraph-test.db JWT_SECRET=test-secret \
  .venv/bin/alembic upgrade head
.venv/bin/pytest
.venv/bin/ruff check .
```

Для интеграции с AI задайте провайдера и модели в настройках приложения. Ollama может работать
локально без API-ключа; для Gemini ключ хранится на backend в зашифрованном виде. Рекомендуемая
экономичная модель — `gemini-flash-lite-latest`, эмбеддинги — `gemini-embedding-001`.
