# VIDEO COMBINE AI — Dependency Map

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — очікує схвалення** |
| Версія | 0.1.0 |
| Принцип | Ядро — keyless; важкі/платні залежності — окремі файли й ледачий імпорт |

---

## 1. Вже встановлені та перевірені (не змінюємо)

### `requirements.txt`

| Пакет | Версія | Роль у VIDEO COMBINE AI |
|-------|--------|--------------------------|
| `pyyaml` | >=6.0 | pipeline_defs, config.yaml, skills registry |
| `pydantic` | >=2.0 | DTO API, AgentResult, Settings |
| `jsonschema` | >=4.20 | 20 JSON-схем артефактів |
| `python-dotenv` | >=1.0 | `.env` (значення лише локально) |
| `Pillow` | >=10.0 | thumbnails, titled clip |
| `numpy` | >=1.24 | обробка кадрів/аудіо |
| `requests` | >=2.31 | keyless stock downloads, network-check |
| `certifi` | >=2026.10.19 | TLS |
| `google-auth`, `google-genai` | >=2.0 / >=1.0.0 | опційний хмарний адаптер (ключ не обов'язковий) |
| `openai` | >=2.44.0 | опційний хмарний адаптер |
| `fastapi` | >=0.110 | база для `studio/api` (уже в Backlot) |
| `uvicorn` | >=0.29 | ASGI |
| `watchfiles` | >=0.21 | SSE/watch старий борд |
| `websockets` | >=14.0 | SSE |
| `pythainlp` | >=5.0 | мовна обробка (не для uk/en ядра) |

### `requirements-dev.txt`

`pytest>=8.0`, `pytest-asyncio>=0.23`, `httpx>=0.24` — уже є.
`tests/conftest.py` блокує non-loopback socket: safety net для keyless-тестів.

### `requirements-generator.txt` / `-optional.txt`

`edge-tts`, `piper-tts`, `kokoro`, `rembg`, `mediapipe`, `yt-dlp`, `gallery-dl`,
`faster-whisper` — драбина `tts_save`, фон, завантаження, транскрипція.
Залежності встановлюються **опційно**; ядро стартує без них.

### `requirements-gpu.txt`

`torch/torchaudio/torchvision` — тільки для GPU-адаптерів; на цьому стенді
немає CUDA/MPS, тому не встановлюється.

## 2. Нові backend залежності (`requirements-studio.txt` — NEW)

| Пакет | Мінімальна версія | Навіщо | Обов'язковий? |
|-------|-------------------|--------|---------------|
| `sqlalchemy` | >=2.0 | SQLAlchemy Core, DB-шар | так (профіль local/prod) |
| `alembic` | >=1.13 | міграції SQLite/PostgreSQL | так |
| `celery` | >=5.3 | черга рендерів | тільки `production` |
| `redis` | >=5.0 | broker/result backend | тільки `production` |
| `orjson` | >=3.9 | швидка серіалізація checkpoint | опційно |
| `tenacity` | >=8.2 | retry policy (дублює tool_registry — використовуємо лише якщо потрібно) | опційно |
| `python-multipart` | >=0.0.9 | завантаження користувацьких медіа | так |
| `pytest-cov` | >=4.1 | покриття | dev |

**Не додаємо:** нові LLM SDK, ключі, платіжні клієнти, VPN/DPI/proxy-пакети.

## 3. Нові frontend залежності (`dashboard/package.json` — NEW)

| Пакет | Версія | Навіщо |
|-------|--------|--------|
| `next` | ^15.0 | App Router |
| `react`, `react-dom` | ^19.0 | UI |
| `typescript` | ^5.6 | типи |
| `@tanstack/react-query` | ^5.0 | API-кеш/SSE-синхронізація |
| `zod` | ^3.23 | валідація DTO |
| `openapi-typescript` | ^7.0 | генерація типів з FastAPI OpenAPI |
| `vitest` | ^2.1 | unit-тести |
| `@testing-library/react` | ^16.0 | компонентні тести |
| `@playwright/test` | ^1.48 | e2e smoke |

Remotion-стек лишається в `remotion-composer/` (`remotion ^4.0.484`,
`react 18`) і **не змішується** з версіями React у dashboard — окремий install.

## 4. Системні залежності

| Компонент | Поточна версія | Примітка |
|-----------|----------------|----------|
| Python | 3.11.18 (`.python-version` 3.11) | Makefile default 3.10 — вирівняти до 3.11 |
| Node | 22.23.4 | `.node-version`, engines remotion |
| FFmpeg / ffprobe | 9.0.2 | де-факто render engine, 49 викликів у коді |
| GNU Make | 3.81 | `make test/lint/setup` |
| Docker | відсутній у репозиторії | додати Dockerfile/compose у Phase 1/10 |

## 5. Мапа «залежність → фаза»

```
Phase 1: sqlalchemy, alembic, python-multipart, next, react, vitest, playwright
Phase 2: (без нових pkg — Pydantic із requirements.txt)
Phase 3: requirements-generator/optional (вже є)
Phase 4: requirements-generator/optional (вже є)
Phase 5: (без нових pkg — tools/video вже є)
Phase 6: (без нових pkg — scene_detect/auto_reframe вже є)
Phase 7: (без нових pkg — Pillow вже є)
Phase 8: (без нових pkg)
Phase 9: celery, redis
Phase 10: postgres driver (psycopg[binary]), pytest-cov, Docker
```

## 6. Правила

1. **Ледачий імпорт.** `torch`, `rembg`, `kokoro`, `mediapipe`, `celery` —
   тільки всередині функцій/адаптерів; CLI стартує миттєво.
2. **Ніяких секретів у залежностях.** Ключі лише з env, у `.env.example` — порожньо.
3. **Пінування.** Мінімальні версії зверху; у CI — `pip freeze > constraints.txt`
   і `npm ci` з lockfile.
4. **Аудит.** `pip-audit` + `npm audit` у CI; failing → no merge.
5. **Опційні профілі.** `requirements-studio.txt` не тягне GPU/хмару;
   `requirements-gpu.txt` і опційні хмарні адаптери — окремо.

---

*Наступний документ: `08-ROADMAP.md` (вже створено), `10-PHASE1-PLAN.md`.*
