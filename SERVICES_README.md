# `app/services` — сервисный слой приложения (краткая карта)

Папка `app/services` содержит сервисы «бизнес-логики» и зависимости для роутов: аутентификация, работа с анализами/диалогами, планировщик фоновых задач и интеграции (в т.ч. Voca.tech).

---

## `__init__.py`
Публичный реэкспорт функций администрирования из `main_services.py`:

- `create_default_admin`
- `ensure_admin_exists`
- `reset_admin_password`

---

## `dependencies.py`

### `class OAuth2PasswordBearerCookie(OAuth2)`
OAuth2 схема, которая **берёт Bearer-токен из cookie `Authorization`**, а не из заголовка.

- **`__call__(self, request: Request) -> Optional[str]`**
  - Возвращает токен (строку) или кидает `HTTPException(401)`.

### `security`
Экземпляр `OAuth2PasswordBearerCookie` с `token_url=f"{settings.API_PREFIX}/users/login"`.

### `get_current_user(security_scopes, token, db) -> User`
FastAPI dependency:
- декодирует JWT (`HS256`, `settings.SECRET_KEY`),
- проверяет пользователя в БД (`user_crud.get_by_username`),
- проверяет `is_active`,
- проверяет scope’ы (`SecurityScopes`),
- возвращает объект пользователя или кидает `HTTPException`.

---

## `main_services.py`

### `EnumEncoder`
JSON-энкодер для сериализации `Enum` (кладёт `Enum.name`).

### `create_default_admin(db) -> Optional[User]`
Создаёт администратора по умолчанию из `settings.ADMIN_*` (если ещё нет).

### `ensure_admin_exists(db) -> User`
Гарантирует, что в системе есть администратор: если нет — создаёт дефолтного.

### `reset_admin_password(db, new_password) -> Optional[User]`
Меняет пароль дефолтного администратора (хеширует и обновляет через CRUD).

---

## `health_service.py`

### `check_health(db) -> HealthResponse`
Проверка здоровья приложения:
- `SELECT 1` на БД,
- дополнительный health-счётчик через `analysis_crud.count(db)`,
- возвращает `HealthResponse` со статусом/версией.

---

## `analysis_service.py`

### `class AnalysisService(LoggerMixin)`
Сервис для workflow «загрузить аудио → создать запись анализа → обработать → обновить статус/результат».

- **`__init__(db)`**: хранит `AsyncSession`, создаёт `SpeechProcessor`, гарантирует папку `uploads/`.
- **`create_analysis(file: UploadFile) -> AnalysisResponse`**
  - сохраняет загруженный файл на диск,
  - создаёт запись анализа через `analysis_crud.create`,
  - запускает обработку `_process_analysis_background(...)`.
- **`get_analyses(skip, limit) -> list[AnalysisList]`**: список анализов (с сортировкой).
- **`get_analysis(analysis_id) -> AnalysisResponse`**: получить один анализ или ошибка `AnalysisNotFoundError`.
- **`delete_analysis(analysis_id)`**: удаляет файл и запись в БД.
- **`_process_analysis_background(analysis_id, file_path)`**
  - запускает `speech_processor.process_audio_with_db_update(...)`,
  - при ошибке ставит статус `failed`.

---

## `speech_processor.py`

### `class SpeechProcessor(LoggerMixin)`
Сервис обработки аудио для модуля «analysis».

- **`process_audio(file_path, analysis_id=None) -> dict`**
  - Сейчас это **заглушка**: `sleep(2)` и статический результат (text/confidence/…).
  - Если задан `analysis_id` и есть `self.db`, обновляет запись анализа через `analysis_crud.update_result`.
- **`process_audio_with_db_update(file_path, analysis_id, db) -> dict`**
  - ставит статус `processing`,
  - вызывает `process_audio(...)`,
  - пишет результат и `completed`,
  - при ошибке ставит `failed`.

---

## `dialog_service.py`
Большой модуль сервисов вокруг диалогов/аудио и словарей.

### NLP/нормализация (на базе `natasha`)
Набор функций для нормализации и генерации форм слов (наташа + fallback):
- `normalize_word_natasha`, `get_word_forms_natasha`, `extract_words_from_text_natasha`
- `normalize_word_fallback`, `get_word_forms_fallback`, `extract_words_from_text_fallback`
- публичные обёртки: `normalize_word`, `get_word_forms`, `extract_words_from_text`

### `class VocaAPIService(LoggerMixin)`
Интеграция с `api.voca.tech`:
- **rate limiting**: 1 одновременный запрос + минимум 2 секунды между запросами.
- **`download_records(start_date, end_date, db=None) -> list[dict]`**
  - получает записи за период,
  - сохраняет json-метаданные + скачивает `.wav`,
  - опционально пишет записи в БД через `audio_data_crud.create_from_voca_record`,
  - создаёт/проверяет сотрудников (`employee_crud.get_by_employee_id` / `employee_crud.create`).
- **`download_records_by_date_range(start_date, end_date, db=None)`**: то же, но даты строками.
- **`get_audio_data_stats(db)`**, **`get_unprocessed_audio_data(db)`**, **`mark_audio_data_as_processed(db, audio_data_id)`**: вспомогательные методы.

Экземпляр:
- `voca_service = VocaAPIService()`

### `class AudioDataProcessor(LoggerMixin)`
Сервис «подготовки аудиоданных» (склейка множества записей в 1 дневной файл):
- склеивает WAV’ы через `pydub`/ffmpeg, приводит к параметрам (sample rate/каналы),
- **`process_employee_audio_data(db, employee_id, target_date) -> Optional[str]`**
  - берёт необработанные записи за предыдущие сутки,
  - склеивает их в `full_speech_data/<employee>_<date>/*_full.wav`,
  - помечает исходные записи обработанными,
  - создаёт/обновляет запись `audio_data_for_analysis`.
- **`process_all_audio_data(db, target_date=None) -> dict[int, str]`**
  - делает то же для всех сотрудников.

Экземпляр:
- `audio_processor = AudioDataProcessor()`

### `class DialogTextHighlighter(LoggerMixin)`
Подсветка слов/фраз в тексте диалогов цветами словарей:
- грузит фразы/словари в кэш,
- находит совпадения (2 режима):
  - по нормализованным формам/вариантам слова,
  - точный поиск «как есть» по выражениям из `Phrase.phrase` (игнорируя реплики клиента).
- обновляет `Dialog.conversation` в БД, вставляя HTML `<span style="background-color: ...">...</span>`.

Экземпляр:
- `dialog_highlighter = DialogTextHighlighter()`

### `class DialogDictionaryPopulator(LoggerMixin)`
Заполняет таблицу связей `dialog_dictionary` между диалогами и словарями:
- `populate_dialog_dictionary(...)` / `populate_all_dialogs_dictionaries(...)`
- варианты «точного поиска» по выражениям и «нормализованного» поиска
- методы массовой обработки по словарю/организации + очистка связей.

Экземпляр:
- `dialog_dictionary_populator = DialogDictionaryPopulator()`

---

## `ml_service.py`
CLI-скрипт для запуска ML-конвейера по диапазону дат (не FastAPI-сервис).

### `main_audio_analyzer_function(start_date, end_date)`
Основная функция запуска ML-обработки:
- берёт `AudioDataForAnalysis` из БД в диапазоне дат через `DBConnection.get_by_date_range`,
- **STAGE 1**: VAD-нарезка дневной записи на чанки (`AudioAnalyzer.vad_split_audio_into_dialogues`) и сохранение `.wav`,
- **STAGE 2**: диаризация + транскрибация (`TextExtractor.diarization_transcription_analysis`),
- **STAGE 3**: LLM-разбиение/типизация и сохранение диалогов/оценок в БД (`LLMAnalyzer.extract_dialogues`).

Запуск: `python -m app.services.ml_service --start_date YYYY-MM-DD [--end_date YYYY-MM-DD]`

---

## `scheduler_service.py`

### `class SchedulerService(LoggerMixin)`
Фоновый планировщик, который **каждый час** запускает загрузку записей через `voca_service.download_records(...)`.

- **`set_db_session_factory(session_factory)`**: прокидывает фабрику `AsyncSession` (генератор `async for db in ...`).
- **`start_hourly_download()`**: основной цикл ожидания до следующего часа и запуска.
- **`start()` / `stop()`**: управление asyncio-задачей.
- **`is_running`**: флаг состояния.

Экземпляр:
- `scheduler_service = SchedulerService()`


