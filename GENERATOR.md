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

На цій машині створено ярлик **OpenMontage Generator.lnk**: подвійний клік відкриває вікно вводу теми, генерує MP4 у `projects/desktop/` і відкриває готовий файл. Логіка — у `launch_generator.ps1` (корінь репозиторію); ярлик запускає його через PowerShell з `-ExecutionPolicy Bypass`. Типово використовуються джерела `wikimedia nasa archive_org` — вони працюють без ключів; якщо ваша мережа блокує інші сайти (наприклад `loc.gov` віддає Cloudflare 403), генератор усе одно збирає відео з локальних титрових сцен. Вибрати джерела можна параметром `-Sources wikimedia nasa`. Щоб перестворити ярлик на іншій машині:

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
| `--repos` | Показати стан усіх репозиторіїв (runtime / read-only / out-of-scope) |
| `--network-check` | Перевірити доступність keyless-джерел через поточне оточення |

## Мережа й проксі

Генератор не встановлює й не активує VPN, анти-DPI, proxy-pools, Telegram-транзит
або інші засоби обходу обмежень. Він лише поважає стандартні змінні оточення
`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` (і їхні нижньорегістрові
варіанти), які вже використовують `requests`, `yt-dlp` і `gallery-dl`.

```powershell
# Перевірити, чи доступні Wikimedia / NASA / Archive.org через ваш проксі
python -m generator --network-check
```

Значення проксі ніколи не друкуються: у звіті лишаються лише схема, хост і порт
(без логіна/пароля). Мережеві репозиторії зі списку вище залишаються `out-of-scope`.

## Інтегровані open-source репозиторії

Повний перелік і реальний стан (встановлено / потребує GPU / потребує URL / не увімкнено / лише для читання / поза межами генератора):

```powershell
python -m generator --repos
```

| Група | Репозиторії | Як використовуються |
|-------|-------------|---------------------|
| TTS-драбина `tts_save` | `rany2/edge-tts`, `rhasspy/piper`, `rhasspy/piper-voices`, `hexgrad/kokoro` | `auto`: edge → Piper (локальний `uk_UA`, CPU, MIT) → Kokoro → Windows SAPI → тиша. `--tts piper --piper-voice uk_UA-tetiana-high` примусово використає Piper |
| GPU TTS | `OpenBMB/VoxCPM2`, `leemysw/yovoice` | `VoxCPM2` — Apache-2.0 код+ваги, мультимовний cloning-TTS; обидва активуються лише з CUDA/MPS і шляхом (`VOXCPM2_REPO`, `YOVOICE_REPO`) |
| Заміна фону | `danielgatis/rembg`, `PeterL1n/RobustVideoMatting`, `xuebinqin/U-2-Net`, `google-ai-edge/mediapipe`, `backgroundremover` | `--remove-bg` (rembg `u2net` через ffmpeg raw-пайп), `--bg-engine selfie` для MediaPipe, `--selfie-preview` для прев'ю; фолбек — ffmpeg chromakey |
| Завантаження/пошук | `yt-dlp/yt-dlp`, `imputnet/cobalt`, `mikf/gallery-dl`, `searxng/searxng`, `WordPress/openverse` | URL-ланцюжок yt-dlp → cobalt → gallery-dl; SearxNG — опційний `--sources searxng` (потрібен `SEARXNG_URL`); Openverse уже в stock-адаптерах |
| Переклад | `LibreTranslate/LibreTranslate` | `--translate en` перекладає текст SRT, не змінюючи таймкоди; `LIBRETRANSLATE_URL` (типово `http://localhost:5000`) |
| Транскрипція | `Graphify-Labs/graphify`, `SYSTRAN/faster-whisper`, `m-bain/whisperX` | Патерн `faster-whisper + yt-dlp`: `--transcribe FILE\|URL --whisper-model tiny`; `--remove-pauses` стискає довгі паузи в таймкодах; whisperX — опційний вирівнювач |
| Локальне відео | `lllyasviel/FramePack`, `Tencent-Hunyuan/HunyuanVideo`, `zai-org/CogVideo`, `Lightricks/LTX-Video`, `Wan-Video/Wan2.2`, `LTX/Wan2GP`, `AlibabaCloud-Official/Wan3.0`, `Stability-AI/generative-models`, `duixcom/Duix-Avatar`, `wide-trace/open-higgsfield`, `kandinskylab/kandinsky-5` | Каталоговані статус-адаптери; активуються шляхом `*_REPO` за наявності CUDA/MPS. FramePack — головний кандидат (~6 GB VRAM), Duix-Avatar — офлайн-ведучий. На цій машині GPU немає |
| Бенчмарки (read-only) | `harry0703/MoneyPrinterTurbo`, `HKUDS/ViMax`, `lcy362/agnes-video-generator`, `YILS-LIN/short-video-factory`, `ddean2009/MoneyPrinterPlus`, `calesthio/OpenMontage`, `Resemble-AI/Chatterbox` | Порівняння фіч і методологій; код не імпортується. Для `MoneyPrinterPlus` (GPL + заборона комерції) і `OpenMontage` (AGPL) читати тільки README; Chatterbox — RETIRED |
| Методології (read-only) | `affaan-m/ECC`, `polishuk01/shuohao-skills`, `digitalsamba/claude-code-video-toolkit`, `JuneYaooo/capsule-cinema`, `darkzOGx/youtube-automation-agent`, `h4ckf0r0day/Obscura` та ін. | Джерела гейтів, self-QC, Memory Vault, outline→script→staging→storyboard. Репозиторії з непідтвердженим owner позначені `needs-verification` і не клонуються автоматично |

Мережеві репозиторії з «Партії 26» (VPN/DPI/proxy/tunnel/Telegram-транзит/rclone/R2)
занесені в каталог як `out-of-scope`. Генератор не обходить обмеження мережі,
не ротує проксі й не використовує сторонні тунелі; ці записи існують лише для
повноти обліку й ніколи не активуються.

### Практичні приклади

```powershell
# Українська озвучка повністю локально (перший запуск завантажить голос Piper)
python -m generator "чому небо синє" --tts piper --offline --out local.mp4

# Заміна фону на однотонний колір + прибирання пауз
python -m generator "місто в дощі" --remove-bg --bg-color "#122033" --remove-pauses

# Транскрипція наявного відео (без ключів, локальна модель faster-whisper)
python -m generator --transcribe "C:\шлях\до\video.mp4" --whisper-model tiny --dry-run
```

Базовий CLI лишається keyless: додаткові пакети встановлюються окремо через
`pip install -r requirements-generator-optional.txt`, а за їх відсутності
відповідний крок тихо пропускається. Змінні оточення для опційних сервісів
(`SEARXNG_URL`, `LIBRETRANSLATE_URL`, `COBALT_API_URL`, `PIPER_VOICES_DIR`,
`*_REPO`) описані в `.env.example`.

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
- `generator/speech.py` — TTS-драбина `tts_save` (edge → Piper → Kokoro → SAPI → тиша) з fail-open і послівними таймкодами.
- `generator/external_repos.py` — каталог і перевірка стану всіх репозиторіїв: runtime, бенчмарки, методології та `out-of-scope` мережеві записи.
- `generator/background.py`, `generator/pause_removal.py`, `generator/translation.py`,
  `generator/transcription.py`, `generator/downloads.py` — опційні локальні адаптери.
- `generator/media.py` — `tools.video.direct_clip_search.DirectClipSearch` + локальний fallback.
- `generator/render.py` — `tools.subtitle.subtitle_gen.SubtitleGen` + `tools.video.video_compose.VideoCompose` (`operation="compose"`, FFmpeg, без Node).
- `generator/cli.py` — оркестрація, проєктний простір і звіт.

Повний агентський пайплайн OpenMontage (дослідження → пропоза → затвердження → асети → рендер) описаний в `AGENT_GUIDE.md` і `pipeline_defs/*.yaml`. CLI вище — швидкий локальний шлях, який не потребує агента чи API-ключів.

## Ліцензія

OpenMontage — AGPL-3.0 (див. `LICENSE`).
