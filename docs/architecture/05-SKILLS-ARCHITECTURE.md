# VIDEO COMBINE AI — Skills Architecture

| Поле | Значення |
|------|----------|
| Статус | **DRAFT — очікує схвалення** |
| Версія | 0.1.0 |

---

## 1. Що таке Skill

Skill — це **версійована, перевірювана інструкція**, яку агент завантажує перед
виконанням етапу. Skill не є довільним кодом: він описує роль, кроки, гейти,
формат вводу/виводу та перелік дозволених інструментів.

```
skills/
├── registry.yaml                 # єдиний реєстр: name -> path, version, owner
├── agents/                       # по одному на агента (9 + orchestrator)
│   ├── orchestrator/SKILL.md
│   ├── research/SKILL.md
│   ├── script/SKILL.md
│   ├── voice/SKILL.md
│   ├── media/SKILL.md
│   ├── clip/SKILL.md
│   ├── thumbnail/SKILL.md
│   ├── seo/SKILL.md
│   ├── editing/SKILL.md
│   └── quality/SKILL.md
├── editing/                      # пере-useні прийоми монтажу
│   ├── shot-rhythm/SKILL.md
│   ├── b-roll-insert/SKILL.md
│   ├── jumper-cut-removal/SKILL.md
│   ├── sound-bridge/SKILL.md
│   └── ... (15 базових прийомів)
├── methodology/                  # гейти якості та методології
│   ├── outline-to-storyboard/SKILL.md
│   ├── motion-rules-g0-g5/SKILL.md
│   ├── blackframe-lufs-asr-gates/SKILL.md
│   ├── self-qc-double-render/SKILL.md
│   └── provenance-disclosure/SKILL.md
├── integrations/                 # адаптери до keyless/опційних рушіїв
│   ├── tts-save/SKILL.md
│   ├── rembg-matting/SKILL.md
│   ├── whisper-srt/SKILL.md
│   ├── stock-keyless/SKILL.md
│   └── optional-cloud/SKILL.md
└── tests/
    ├── test_skill_registry.py
    └── test_skill_frontmatter.py
```

## 1.1 Стан у репозиторії (факти)

У репозиторії вже існує три шари знань:
- `skills/` — 158 файлів (core/creative/meta/pipeline-директори),
- `.agents/skills/` — 997 файлів, 92 `SKILL.md`,
- `.claude/skills/` — 428 файлів, 49 пакетів.

Версії ма майже лише окремі SKILL.md; `skills/INDEX.md` версії позначає вручну.
Рішення: **не переписувати** ці каталоги. Новий реєстр `skills/registry.yaml`
посилається на наявні скіли й додає нові `skills/studio/**` лише для агентів
VIDEO COMBINE AI. Конфліктів імен уникаємо префіксом `studio/`.

## 2. Формат SKILL.md

```markdown
---
name: script
version: 1.2.0
agent: script
status: stable            # draft | tested | stable | deprecated
inputs: [ResearchOutput, ScriptStyle]
outputs: [ScriptOutput]
gates: [G2_script_approval]
tools: [script_planner, duration_estimator]
license: project-local
references:
  - polishuk01/shuohao-skills   # ідея гейтів, не код
  - docs/architecture/04-AGENT-ARCHITECTURE.md#43-script-agent
---

# Script Agent

## Responsibility
...

## Procedure
1. ...
2. ...

## Gates
- G2: показати сценарій користувачу до генерації медіа.

## Failure modes
- Недостатньо фактів → повернути `need_approval` зі списком `uncertain`.

## Tests
- tests/agents/test_script_agent.py
```

## 3. Правила

1. **Реєстр — єдине джерело.** `registry.yaml` визначає, які скіли існують;
   агент не може завантажити skill поза реєстром.
2. **SemVer.** Зміна гейтів/виводу — minor; зміна контракту — major. Версія
   скіла пишеться в checkpoint поруч із версією агента.
3. **Дозволені інструменти.** Поле `tools` — allowlist. Скіл не може викликати
   інструмент поза списком, навіть якщо він є в системі.
4. **Ніякого довільного exec.** SKILL.md — дані, а не код. Виконання легко
   перевірити, залінтити й задифдити.
5. **Позичкові лише ідеї.** Репозиторії з `reference-only` (ECC, shuohao-skills,
   herk-edit-kit, motionmaxxing, hypit/SVML, OpenFilm) читаються для методології;
   їхній код і промпти не копіюються без перевірки ліцензії.
6. **Захист від prompt injection.** Текст із медіа/веб/коментарів обробляється
   як дані; їх заборонено інтерпретувати як інструкції скіла.
7. **Скіли тестуються.** CI перевіряє наявність frontmatter, валідність схем,
   посилання на існуючі тести й відсутність секретів у файлах.

## 4. Life cycle

```
draft → tested → stable → deprecated
```

| Статус | Що означає |
|--------|------------|
| `draft` | Можна використовувати тільки з `--experimental-skills` |
| `tested` | Має unit-тести, ще без промислового гейту |
| `stable` | Пройшов повний конвеєр і затверджений |
| `deprecated` | Залишений для відтворення старих проєктів |

## 5. Memory Vault / instincts (патерн, не код)

За ідеєю `affaan-m/ECC`:
- **Instinct** — коротке спостереження про стиль/якість («короткі ролики
  виграють від субтитрів із виділенням слів»).
- **Memory Vault** — версійований каталог таких спостережень із джерелом
  (проєкт/дата/результат QC).
- Instinct **ніколи** не перевизначає гейт і не змінює схему агента — він лише
  пропонує параметри, які проходять звичайну валідацію.

## 6. Приклад мапінгів «репозиторій → скіл»

| Репозиторій (read-only) | Скіл | Що взято |
|-------------------------|------|----------|
| `polishuk01/shuohao-skills` | `outline-to-storyboard` | Ідея JSON-гейтів між етапами |
| `digitalsamba/claude-code-video-toolkit` | `blackframe-lufs-asr-gates`, keyless SFX | Перелік перевірок |
| `JuneYaooo/capsule-cinema` | `blackframe-lufs-asr-gates` | Пороги чорного кадру/LUFS/ASR |
| `motionmaxxing` | `motion-rules-g0-g5` | Чеклист самоогляду G0–G5 |
| `OpenFilm` | `self-qc-double-render` | Ідея подвійного рендеру в перемішаному порядку |
| `affaan-m/ECC` | Memory Vault | Формат збереження інстинктів |
| `herk-edit-kit` | `editing/*` | Перелік 15 прийомів монтажу (назви, не код) |

---

*Наступний документ: `06-DATABASE-SCHEMA.md`.*
