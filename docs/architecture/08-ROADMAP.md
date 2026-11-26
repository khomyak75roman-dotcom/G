# VIDEO COMBINE AI — Implementation Roadmap

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — очікує схвалення** |
| Версія | 0.1.0 |
| Правило | Фаза вважається завершеною **тільки** після зелених тестів, документації й окремого коміту |

---

## 0. Фаза 0 — Архітектура (поточний стан)

**Вхід:** MASTER PROJECT INSTRUCTION.
**Вихід:** цей набір документів (`docs/architecture/`), оновлений `AGENTS.md`.
**Exit criteria:** архітектура схвалена користувачем → дозвіл на Phase 1.
**Commit:** `docs: approve VIDEO COMBINE AI architecture` (після схвалення).

## 1. Phase 1 — Project foundation and dashboard

- **Мета:** працюючий каркас із 11 розділами dashboard та здоровим API.
- **Скоуп:** FastAPI app, Pydantic schemas, SQLite + migrations, React/Next.js
  shell, Docker compose (`local`), settings, structured logging, health check,
  thin pipeline runner (мінімальний Orchestrator-каркас без агентів).
- **Не входить:** генерація контенту, рендер, черга Celery у локальному профілі.
- **Тести:** API contract tests, DB migration tests, frontend smoke/render tests.
- **Документація:** README runbook, API reference, `AGENTS.md`.
- **Acceptance:** `docker compose up` → дашборд показує 11 розділів; створення
  проєкту зберігається в SQLite; `make test` зелений; окремий commit.

## 2. Phase 2 — Original script generation and scene planning

- Скоуп: Research Agent, Script Agent, `outline → script → staging → storyboard`,
  гейт G2, редактор сцен у UI.
- Тести: контракти агентів, валідація гейтів, ідемпотентність, uk/en.
- Acceptance: сценарій + сцен з таймінгами створюються без ключів; гейт блокує
  подальші етапи до затвердження.

## 3. Phase 3 — Local voice generation and subtitles

- Скоуп: Voice Agent, драбина `tts_save`, Piper uk_UA, word timings, SRT,
  Voice Studio UI, переклад SRT через опційний LibreTranslate.
- Тести: синтез uk/en, fallback ladder, збереження таймкодів, silence-fallback.
- Acceptance: озвучка й SRT генеруються keyless; драбина не падає за відсутності
  edge-tts; у rare silence-випадку Quality Agent попереджає.

## 4. Phase 4 — Media discovery and media library

- Скоуп: Media Agent, keyless stock sources, ранжування за сценою, відсіювання,
  provenance/license tracking, завантаження користувачем, Media Library UI.
- Тести: джерела, ліцензійні поля, sha256, відхилення невизначеної ліцензії.
- Acceptance: кожен вибраний кліп має джерело/ліцензію/хеш; заборонені джерела
  не завантажуються.

## 5. Phase 5 — FFmpeg video assembly and rendering

- Скоуп: Editing Agent, scene timeline, переходи, аудіомікс, анімовані субтитри,
  оверлеї, ken-burns, інтро/аутро, рефреймінг, 1080p/720p, editable project.
- Тести: збірка таймлайну, H.264 MP4, геометрія 16:9/9:16, відтворюваність.
- Acceptance: готовий MP4 відповідає профілю; таймлайн зберігається й
  редагується; рендер не блокує UI.

## 6. Phase 6 — YouTube Clip Studio

- Скоуп: Clip Agent, детекція сцен/моментів, відбір, рефреймінг, новий коментар,
  підтвердження прав, атрибуція, експорт окремих кліпів.
- Тести: відмова без `rights_confirmed`, атрибуція в звіті, відсутність
  метаданійних трюків.
- Acceptance: створюється оригінальна редактура з повною provenance.

## 7. Phase 7 — Thumbnail generation

- Скоуп: Thumbnail Agent, 16:9/9:16, варіанти, шари, продукт, шрифти,
  Thumbnail Studio UI.
- Тести: геометрія, редаговані шари, експорт PNG, гейт вибору.
- Acceptance: принаймні 2 варіанти для кожного формату; шари редагуються.

## 8. Phase 8 — YouTube SEO

- Скоуп: SEO Agent, title/description/tags/hashtags/keywords/pinned comment,
  окремі long/short і uk/en, SEO Studio UI.
- Тести: факти з ResearchOutput, відсутність суперечностей зі сценарієм.
- Acceptance: метадані згенеровані й затверджені для обох форматів/мов.

## 9. Phase 9 — Orchestrator and agent automation

- Скоуп: повний Orchestrator, DAG, залежності, retry, гейти, resume, Celery/Redis
  у profille `production`, реєстр агентів/скілів, live-моніторинг.
- Тести: переривання на кожному етапі, resume, ідемпотентність, версії агентів.
- Acceptance: конвеєр відновлюється після збою на будь-якому етапі без втрати
  артефактів.

## 10. Phase 10 — Quality assurance and production deployment

- Скоуп: Quality Agent (чорні кадри/LUFS/ASR/синхронізація/атрибуція/секрети),
  self-QC, PostgreSQL path, Docker production, CD, runbook, matrix uk/en ×
  long/short × 16:9/9:16 × 1080p/720p.
- Тести: повний `make test`, frontend tests, contract tests, e2e smoke.
- Acceptance: всі 16 комбінацій матриці проходять; секрети відсутні; реліз
  блокується Quality Agent-ом за наявності blocking-проблем.

## 11. Порядок комітів

```
docs: VIDEO COMBINE AI architecture (Phase 0)
feat(phase1): foundation and dashboard
feat(phase2): research and script agents
feat(phase3): voice and subtitles
feat(phase4): media discovery and library
feat(phase5): ffmpeg assembly and rendering
feat(phase6): youtube clip studio
feat(phase7): thumbnail generator
feat(phase8): youtube seo
feat(phase9): orchestrator and agents
feat(phase10): quality gates and production deployment
```

## 12. Вертикальний зріз замість «великого вибуху»

Рекомендація: у Phase 1–5 створити **один наскрізний keyless smoke**
(тема → сценарій → голос → медіа → MP4) і лише потім розширювати агентів.
Це дає працюючий продукт раніше, ніж буде побудований повний Orchestrator.

---

*Наступні документи: `10-PHASE1-PLAN.md`, `11-RISKS-AND-GAPS.md`.*
