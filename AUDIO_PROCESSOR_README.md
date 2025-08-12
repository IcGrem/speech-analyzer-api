# AudioDataProcessor - Обработка аудиоданных

## Описание

Класс `AudioDataProcessor` предназначен для обработки аудиоданных перед транскрибацией и анализом. Основная функция - склеивание аудиофайлов из таблицы `audio_data` в единые файлы для каждого сотрудника за предыдущие сутки.

## Основные возможности

1. **Получение данных**: Извлекает необработанные записи из таблицы `audio_data` за предыдущие сутки
2. **Группировка по сотрудникам**: Группирует записи по `employee_id` в хронологическом порядке
3. **Склеивание аудио**: Объединяет аудиофайлы в один WAV файл для каждого сотрудника
4. **Сохранение результатов**: Сохраняет склеенные файлы в структурированную папку
5. **Обновление БД**: Отмечает записи как обработанные и создает записи в `audio_data_for_analysis`

## Структура файлов

```
full_speech_data/
├── {employee_id}_{YYYY-MM-DD}/
│   └── {employee_id}_{YYYY-MM-DD}_full.wav
├── {employee_id}_{YYYY-MM-DD}/
│   └── {employee_id}_{YYYY-MM-DD}_full.wav
└── ...
```

## Использование

### 1. Обработка всех сотрудников

```python
from app.services.dialog_service import audio_processor
from app.db.session import async_session_maker

async def process_all_audio():
    async with async_session_maker() as db:
        results = await audio_processor.process_all_audio_data(db)
        
        for employee_id, filename in results.items():
            print(f"Сотрудник {employee_id}: {filename}")
```

### 2. Обработка конкретного сотрудника

```python
from datetime import datetime

async def process_employee_audio(employee_id: int):
    async with async_session_maker() as db:
        target_date = datetime.now()
        filename = await audio_processor.process_employee_audio_data(
            db, employee_id, target_date
        )
        
        if filename:
            print(f"Обработан сотрудник {employee_id}: {filename}")
        else:
            print(f"Нет данных для сотрудника {employee_id}")
```

### 3. Через API

```bash
# Обработка за предыдущие сутки (от текущей даты)
POST /api/v1/dialogs/audio-data/process-previous-day

# Обработка за предыдущие сутки от указанной даты
POST /api/v1/dialogs/audio-data/process-previous-day?target_date=2024-01-15T00:00:00
```

## Алгоритм работы

1. **Получение данных**: Запрос к БД для получения необработанных записей за предыдущие сутки
2. **Группировка**: Записи группируются по `employee_id` и сортируются по `creation_date`
3. **Проверка файлов**: Проверяется существование аудиофайлов в папке `speech_data`
4. **Склеивание**: Аудиофайлы объединяются в один WAV файл с сохранением параметров
5. **Сохранение**: Результирующий файл сохраняется в `full_speech_data/{employee_id}_{date}/`
6. **Обновление БД**: 
   - Устанавливается `is_processed = True` для обработанных записей
   - Создается запись в `audio_data_for_analysis` с путем к склеенному файлу

## Требования к аудиофайлам

- Формат: WAV
- Совместимые параметры (частота дискретизации, количество каналов, битность)
- Файлы должны существовать в папке `speech_data`

## Обработка ошибок

- **Отсутствующие файлы**: Логируется предупреждение, файл пропускается
- **Несовместимые параметры**: Файл пропускается с предупреждением
- **Ошибки БД**: Исключение с детальным описанием
- **Ошибки файловой системы**: Исключение с описанием проблемы

## Логирование

Класс использует `LoggerMixin` для логирования всех операций:
- Информационные сообщения о ходе обработки
- Предупреждения о пропущенных файлах
- Ошибки с детальным описанием

## Зависимости

- `numpy` - для работы с аудиоданными
- `wave` - для чтения/записи WAV файлов
- `asyncio` - для асинхронной работы
- `sqlalchemy` - для работы с БД

## Тестирование

### Тест склеивания аудиофайлов
```bash
python test_audio_concatenation.py
```

### Тест процессора
```bash
python test_audio_processor.py
```

## Интеграция с существующим кодом

Класс интегрирован в существующую архитектуру:
- Использует существующие CRUD операции
- Следует паттернам логирования проекта
- Интегрирован в API через эндпоинт `/audio-data/process-previous-day`
- Совместим с существующими моделями данных
