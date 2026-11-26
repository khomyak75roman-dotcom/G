# Генератор відео (keyless CLI)

Цей репозиторій містить повний вихідний код [OpenMontage](https://github.com/OpenMontageInc/OpenMontage) **плюс** компактний CLI-генератор, який збирає відео з текстового запиту **без API-ключів і без Node.js**.

## Що він робить

```
промпт / готовий сценарій
   -> сценарій і розбиття на сцени (generator/script.py)
   -> озвучка edge-tts з послівними таймкодами (generator/speech.py)
   -> SRT-субтитри через OpenMontage SubtitleGen (generator/render.py)
   -> безкоштовні кліпи через OpenMontage DirectClipSearch (generator/media.py)
   -> фінальний MP4 через OpenMontage VideoCompose + FFmpeg
```

Джерела відео без ключів: Wikimedia Commons, NASA, Archive.org, Library of Congress, Coverr. Якщо для сцени не знайдено кліпа або працюєш офлайн, генератор створює локальну титрову сцену (Pillow + FFmpeg) — відео все одно збирається.

Озвучка: `edge-tts` (без ключа, з таймкодами слів). Якщо мережі немає — Windows SAPI (offline), далі — тиша з розрахованими таймкодами. Генератор не падає через відсутність TTS.

## Встановлення (мінімум)

Потрібні Python 3.10+ і FFmpeg (`ffmpeg`/`ffprobe` у PATH).

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
python -m pip install -r requirements-generator.txt
# macOS/Linux
source .venv/bin/activate
python -m pip install -r requirements-generator.txt
```

Повне середовище OpenMontage (Backlot, Remotion, HyperFrames, усі провайдери): `make setup`.

> **Windows ім'я користувача з кирилицею.** Для повного прогону `make test` на цій машині встановлено змінні користувача:
> `PYTHONUTF8=1` (UTF-8 для concat-лістів ffmpeg), `PYTEST_DEBUG_TEMPROOT=C:/omtest/pytest` і
> `PYTEST_ADDOPTS=--basetemp=C:/omtest/pytest/base` (ASCII-шляхи для tmp pytest), а також MIME `.webp`
> у реєстрі (`HKCU\Software\Classes\.webp` → `Content Type = image/webp`). Крім того,
> `showcase_card` і його тест на Windows передають у `drawtext` конкретний файл шрифту — FFmpeg 9.x
> падає, коли шрифт шукається через fontconfig. Тест `make ensure-venv` з пробілом у шляху також
> очищає успадковані `MAKEFLAGS`: локалізований вивід GnuWin32 make (cp1251) ламає UTF-8-декодування.

## Запуск

```bash
# Ukrainian explainer, 4 сцени, 16:9
python -m generator "чому небо синє" --out final.mp4

# Vertical shorts, English, with a custom voice
python -m generator "how black holes form" --lang en --profile youtube_shorts \
  --voice en-US-AriaNeural

# Your own script from a UTF-8 file, offline title cards only
python -m generator --script-file script.txt --offline --profile tiktok

# Inspect available keyless stock adapters
python -m generator --list-sources

# Plan only: print the script and settings without network or rendering
python -m generator "city life in the rain" --dry-run
```

### Ярлик на робочому столі (Windows)

На цій машині створено ярлик **OpenMontage Generator.lnk**: подвійний клік відкриває вікно вводу теми, генерує MP4 у `projects/desktop/` і відкриває готовий файл. Логіка — у `launch_generator.ps1` (корінь репозиторію); ярлик запускає його через PowerShell з `-ExecutionPolicy Bypass`. Щоб перестворити ярлик на іншій машині:

```powershell
$root = "C:\шлях\до\OpenMontage"
$link = Join-Path ([Environment]::GetFolderPath('Desktop')) 'OpenMontage Generator.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
$s.TargetPath = Join-Path $PSHOME 'powershell.exe'
$s.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $root 'launch_generator.ps1') + '"'
$s.WorkingDirectory = $root
$s.IconLocation = (Join-Path $root '.venv\Scripts\python.exe') + ',0'
$s.Save()
```

Основні опції:

| Опція | Що робить |
|-------|-----------|
| `--scenes N` | Кількість сцен (за замовчуванням 4) |
| `--lang uk\|en` | Мова озвучки (визначається автоматично) |
| `--voice NAME` | Голос edge-tts |
| `--rate +10%` | Швидкість мовлення |
| `--profile NAME` | Профіль з `lib/media_profiles.py` (наприклад `youtube_landscape`, `tiktok`) |
| `--sources ...` | Які stock-адаптери використовувати |
| `--offline` | Не звертатися до мережі за кліпами |
| `--no-audio`, `--no-subtitles` | Вимкнути озвучку / субтитри |
| `--timeout SEC` | Ліміт часу пошуку кліпів (за замовчуванням 180) |

## Результат

Кожен запуск створює проєкт у `projects/<project-id>/` (сумісний з Backlot):

```
projects/<project-id>/
├── project.json                  # marker для Backlot
├── artifacts/
│   ├── script.json
│   ├── narration_timing.json
│   ├── subtitles.srt
│   └── generator_report.json     # джерела кліпів, тривалість, шляхи
├── assets/video/source/          # завантажені кліпи / титрові fallback-и
└── renders/final.mp4             # або --out
```

## Архітектура

- `generator/script.py` — детерміністичний сценарій без LLM.
- `generator/speech.py` — TTS з fail-open ланцюжком і послівними таймкодами.
- `generator/media.py` — `tools.video.direct_clip_search.DirectClipSearch` + локальний fallback.
- `generator/render.py` — `tools.subtitle.subtitle_gen.SubtitleGen` + `tools.video.video_compose.VideoCompose` (`operation="compose"`, FFmpeg, без Node).
- `generator/cli.py` — оркестрація, проєктний простір і звіт.

Повний агентський пайплайн OpenMontage (дослідження → пропоза → затвердження → асети → рендер) описаний в `AGENT_GUIDE.md` і `pipeline_defs/*.yaml`. CLI вище — швидкий локальний шлях, який не потребує агента чи API-ключів.

## Ліцензія

OpenMontage — AGPL-3.0 (див. `LICENSE`).
