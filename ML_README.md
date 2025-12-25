# `app/ml` — ML-обработка аудио и диалогов (краткая карта)

Эта папка содержит «ML-конвейер» обработки дневных аудиозаписей:

1) **VAD-сегментация аудио** → 2) **диаризация + ASR (speech-to-text)** → 3) **LLM-разбиение на диалоги, типизация и скоринг** → 4) **сохранение в БД**.

Ниже — что за что отвечает в каждом модуле.

---

## `audio_analyzer.py`

### `class AudioAnalyzer`
Класс для первичной обработки аудио: выделение «диалоговых блоков» по паузам с помощью VAD (voice activity detection).

- **`__init__(self)`**
  - Готовит VAD-pipeline (`pyannote.audio.pipelines.VoiceActivityDetection`) по модели из `settings.VAD_MODEL`.
  - В текущей реализации принудительно использует `cuda` (`torch.device("cuda")`).

- **`vad_split_audio_into_dialogues(self, path_audio, min_duration_dialogue, min_duration_pause)`**
  - Делит исходный аудиофайл на чанки на основании пауз между участками речи.
  - **Вход**:
    - `path_audio`: путь к файлу.
    - `min_duration_dialogue`: минимальная длительность диалога (сек).
    - `min_duration_pause`: минимальная пауза, чтобы завершить текущий диалог (сек).
  - **Выход**: `(status_code, durations_pause, audio_dialogues)`, где:
    - `durations_pause`: список длительностей пауз между сегментами речи,
    - `audio_dialogues`: список кортежей `(AudioSegment, start_sec, end_sec)` — вырезанные диалоги и их границы.

---

## `speech2text_analyzer.py`

### `class TextExtractor`
Класс для Speech-to-Text (ASR) и диаризации спикеров в пределах каждого аудио-чанка.

- **`__init__(self)`**
  - Инициализирует:
    - ASR-модель/процессор (HuggingFace) и `transformers.pipeline("automatic-speech-recognition")`
    - диаризацию `pyannote.audio.Pipeline` по модели из `settings.DIARIZATION_MODEL`
  - Выбирает устройство `cuda` при доступности.

- **`diarization_analysis(self, path_audio) -> list`**
  - Запускает диаризацию на аудио-чанке.
  - Склеивает подряд идущие сегменты одного и того же спикера в «реплики».
  - **Выход**: список реплик вида `[speaker_label, start_ms, end_ms]`.

- **`extract_and_save_text(self, path_audio, replicas_list, folder_w_diarization, chunk_number)`**
  - Нарезает аудио-чанк на реплики по `replicas_list`, сохраняет каждую реплику `.wav` в `folder_w_diarization`.
  - Для каждой реплики делает ASR (`get_chunk_transcription`) и дописывает строку вида `"SPEAKER_XX: текст"` в файл транскрипции (`self.path_to_transcription`).
  - Фильтрует:
    - слишком короткие реплики (`< 500ms`)
    - «пустой/неинформативный» текст (regex + `settings.uninformative_phrases`)

- **`diarization_transcription_analysis(self, current_folder: str, cleaning=False)`**
  - Основной batch-метод по папке дневной записи:
    - берёт все `.wav` чанки из `current_folder/settings.FOLDER_W_DIALOGUES`,
    - для каждого запускает `diarization_analysis` + `extract_and_save_text`,
    - результат сохраняет в `*_transcription.txt` рядом с чанком.
  - `cleaning=True` — по завершению чистит папку `settings.FOLDER_W_DIARIZATION`.

- **`get_chunk_transcription(self, path_speaker_chunk: str)`**
  - Вызывает ASR pipeline на отдельной реплике (файл `.wav`), возвращает распознанный текст.

- **`get_transcription(self, current_folder)`**
  - Делает ASR «целиком» по всей дневной записи (первый найденный `.wav` в `current_folder`).
  - Сохраняет в `transcription_original.txt`.

---

## `llm_analyzer.py`

### `class LLMAnalyzer`
Класс для пост-обработки транскрипций через LLM (OpenAI-совместимый API):
разбиение на диалоги, классификация типов диалогов и (для части диалогов) скоринг качества общения.

- **`__init__(self)`**
  - Конфигурирует OpenAI client (`openai.OpenAI`) по `settings.OPENAI_*`.
  - Поддерживает работу через прокси (`settings.USE_PROXY`, `settings.PROXY_URL`).
  - Хранит промежуточное состояние: `split_dialogues`, `identified_dialogues`, `prompt`.

- **`request_model(self, context: str, prompt: str = prompts.PROMPT_TO_EXTRACT_DIALOGS, get_scores: bool = False) -> tuple[int, str]`**
  - Универсальный метод вызова LLM:
    - для разбиения/типизации диалогов (`PROMPT_TO_EXTRACT_DIALOGS`)
    - для скоринга (`PROMPT_TO_SCORE_DIALOGS`, с `PROMPT_SYSTEM`)
  - Обрабатывает `RateLimitError` (ждёт, либо возвращает `429` при слишком большом запросе для модели).

- **`get_transcriptions_names(folder_w_dialogues: str)`** *(static)*
  - Находит и сортирует файлы `*_transcription.txt` в папке с чанкованием.

- **`filter_dialogues(self) -> list`**
  - Применяет regex-паттерны из `regex.py` к `self.split_dialogues` (ответу LLM после разбиения).
  - Формирует список словарей вида `{"type": "...", "text": "..."}` для типов:
    - `m2c` (manager-to-client),
    - `m2m` (прочие/не-`m2c` в текущей логике — см. `PATTERN_MANAGERS_UNKNOWN`).

- **`get_dialogues_by_type(self, folder_w_dialogues: str, chunk_name: str)`**
  - Берёт результат `filter_dialogues()` и сохраняет его в `*_identified_dialogues.txt` (JSON).
  - Добавляет в каждый найденный диалог поле `chunk_name`.

- **`extract_dialogues(self, current_folder: str, employee, row_full_audio)`**
  - Главный batch-метод для LLM-стадии по дневной папке:
    - читает транскрипции чанков,
    - отправляет в LLM на разбиение/типизацию,
    - вытаскивает диалоги нужных типов (`get_dialogues_by_type`),
    - для найденных диалогов запрашивает оценки (`get_scores`),
    - сохраняет результат в БД через `DBConnection.create_dialog(...)`.
  - Примечание: в методе есть «служебные» вещи (маппинг метрик, дефолтные оценки).

- **`parse_scores(scores_dialog: str) -> dict[str, float]`** *(static)*
  - Парсит текст ответа LLM со скорингом вида `### Критерий: X/5` в словарь `{критерий: X}`.

- **`get_scores(self, folder_w_dialogues: str)`**
  - Для диалогов типа `m2c` запрашивает у LLM оценки качества общения и записывает в каждый диалог:
    - `scores_dialog` (сырой текст),
    - `scores` (словарь оценок).
  - Сохраняет итоговый JSON в `*_scores_dialogues.txt`.

---

## `requests_db.py`

### `class DBConnection`
Синхронный слой доступа к БД через SQLAlchemy (engine + `sessionmaker`), который используется ML-частью для чтения/записи данных.

- **`__init__(self)`**
  - Собирает URL через `utils.get_url_db()` (замена asyncpg → sync-драйвер для совместимости).

- **`get_all_rows(self, models)`**
  - Возвращает все записи таблицы `models`.

- **`get_filtered_rows(self, session: Session, models, order_by: Optional[str] = None, **filters)`**
  - Универсальная фильтрация через `select(models)` с фильтрами формата:
    - `field=value` (eq),
    - `field__gte=value`,
    - `field__lte=value`,
  - Поддерживает сортировку `order_by="field"` или `order_by="-field"`.

- **`get_by_date_range(self, models, start_date: datetime, end_date: datetime)`**
  - Обёртка над `get_filtered_rows` для фильтрации по `date` в диапазоне.

- **`get_by_attribute(self, model, field_name: str, value)`**
  - Возвращает первую запись `model`, где `field_name == value`.

- **`update_row(self, model, filter_field: str, filter_value, **updates)`**
  - Обновляет найденную запись и коммитит.

- **`create_fake_dialog(self, employee, audio_data_for_analysis)`**
  - Генератор тестовой записи `Dialog` со случайными метриками.

- **`create_dialog(self, dialog_data)`**
  - Создаёт запись `Dialog` из словаря данных.

- **`create_general_dict_phrases(self)`**
  - Строит общий словарь триггер-фраз из таблиц `Phrase`/`Dictionary`:
    - ключ: `normal_form`,
    - значение: `[исходная фраза, описание словаря]`.

---

## `prompts.py`
Набор промптов для LLM:

- **`PROMPT_TO_EXTRACT_DIALOGS`**: разбиение транскрипта на диалоги + классификация типа + приведение SPEAKER_* к ролям.
- **`PROMPT_TO_SCORE_DIALOGS`**: скоринг качества общения менеджера с клиентом по критериям.
- **`PROMPT_SYSTEM`**: system-инструкция для режима скоринга.

---

## `regex.py`
Регулярные выражения для выделения диалогов по типу из текста ответа LLM:

- **`PATTERN_MANAGERS_CLIENT`**: извлекает блоки типа «Менеджер и клиент» / «Разговор коллег с клиентом».
- **`PATTERN_MANAGERS_UNKNOWN`**: извлекает блоки типа «Разговор коллег» / «Неопределённо».

---

## `utils.py`
Вспомогательные функции:

- **`timeit(func)`**: декоратор печати времени выполнения.
- **`get_url_db()`**: формирует URL подключения к БД, заменяя `postgresql+asyncpg://` → `postgresql://`.
- **`save_txt_file(way_file, text, mode="w", encoding="utf-8")`**: запись текста в файл.

---

## `logger.py`
Конфиг логирования через `loguru`:

- добавляет файл-лог в `settings.LOGGER_FOLDER/<date>/main_<hour>_<minute>.log`,
- `level=DEBUG`, `rotation=10 MB`, `compression=zip`, `enqueue=True`.


