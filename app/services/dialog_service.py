import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import aiohttp
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydub import AudioSegment

# Импорт для морфологического анализа
from natasha import MorphVocab, Segmenter, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, NewsNERTagger
from natasha.doc import Doc

from app.core.config import settings
from app.core.logging import LoggerMixin
from app.crud.audio_data import audio_data_crud, audio_data_for_analysis_crud
from app.crud.users import employee_crud
from app.schemas.users import EmployeeCreate

# Инициализация компонентов natasha
MORPH = MorphVocab()
SEGMENTER = Segmenter()
EMB = NewsEmbedding()
MORPH_TAGGER = NewsMorphTagger(EMB)
SYNTAX_PARSER = NewsSyntaxParser(EMB)
NER_TAGGER = NewsNERTagger(EMB)

# Устанавливаем пути к ffmpeg для pydub (только для Windows)
if os.name == 'nt':  # Windows
    os.environ["PATH"] = settings.FFMPEG_PATH + ";" + os.environ.get("PATH", "")

    AudioSegment.converter = settings.FFMPEG_EXE
    AudioSegment.ffmpeg = settings.FFMPEG_EXE
    AudioSegment.ffprobe = settings.FFMPEG_FFPROBE


def normalize_word_natasha(word: str) -> str:
    """Приводит слово к нормальной форме используя natasha"""
    if not word:
        return word
    
    try:
        # Создаем документ для анализа
        doc = Doc(word)
        doc.segment(SEGMENTER)
        doc.tag_morph(MORPH_TAGGER)
        
        # Получаем нормальную форму
        for token in doc.tokens:
            if token.pos in ['NOUN', 'ADJ', 'VERB', 'ADV']:
                lemma = token.lemma.lower()
                # Проверяем, что лемма не пустая и отличается от исходного слова
                if lemma and lemma != word.lower():
                    return lemma
        
        # Если не удалось получить лемму или лемма совпадает с исходным словом,
        # используем fallback метод
        return normalize_word_fallback(word)
        
    except Exception:
        # В случае ошибки используем fallback метод
        return normalize_word_fallback(word)


def get_word_forms_natasha(word: str) -> Set[str]:
    """Получает все возможные формы слова используя natasha"""
    if not word:
        return {word}
    
    forms = {word.lower()}
    
    try:
        # Создаем документ для анализа
        doc = Doc(word)
        doc.segment(SEGMENTER)
        doc.tag_morph(MORPH_TAGGER)
        
        # Получаем нормальную форму
        for token in doc.tokens:
            if token.pos in ['NOUN', 'ADJ', 'VERB', 'ADV']:
                lemma = token.lemma.lower()
                forms.add(lemma)
                
                # Для глаголов добавляем основные формы
                if token.pos == 'VERB':
                    # Генерируем основные формы глагола
                    base = lemma[:-2] if lemma.endswith('ть') else lemma
                    forms.update([
                        base + 'ю', base + 'ешь', base + 'ет', base + 'ем', base + 'ете', base + 'ют',
                        base + 'л', base + 'ла', base + 'ло', base + 'ли',
                        base + 'ющий', base + 'ющая', base + 'ющее', base + 'ющие'
                    ])
                break
        
        # Если natasha не дала хороших результатов, используем fallback
        if len(forms) <= 2:  # Только исходное слово и лемма
            fallback_forms = get_word_forms_fallback(word)
            forms.update(fallback_forms)
        
        return forms
        
    except Exception:
        # В случае ошибки используем fallback
        return get_word_forms_fallback(word)


def extract_words_from_text_natasha(text: str) -> List[Dict[str, Any]]:
    """Извлекает слова из текста с их позициями и нормальными формами используя natasha"""
    import re
    
    if not text:
        return []
    
    try:
        # Создаем документ для анализа
        doc = Doc(text)
        doc.segment(SEGMENTER)
        doc.tag_morph(MORPH_TAGGER)
        
        words = []
        for token in doc.tokens:
            if token.pos in ['NOUN', 'ADJ', 'VERB', 'ADV', 'PROPN']:
                words.append({
                    'word': token.text,
                    'normal_form': token.lemma.lower(),
                    'start_pos': token.start,
                    'end_pos': token.stop,
                    'pos': token.pos,
                    'word_forms': get_word_forms_natasha(token.text)
                })
        
        return words
        
    except Exception:
        # В случае ошибки используем fallback метод
        return extract_words_from_text_fallback(text)


def normalize_word_fallback(word: str) -> str:
    """Fallback метод для нормализации слов (старый метод)"""
    if not word:
        return word
    
    word_lower = word.lower()
    
    # Словарь исключений для правильной нормализации
    exceptions = {
        'есть': 'быть',
        'интересует': 'интересовать',
        'интересуют': 'интересовать',
        'информацию': 'информация',
        'объясню': 'объяснить',
        'помог': 'помочь',
        'помогу': 'помочь',
        'поможем': 'помочь',
        'поможете': 'помочь',
        'помогут': 'помочь',
        # Добавляем исключения на основе данных из CSV
        'не привезли': 'не привозить',
        'не получил': 'не получать',
        'не доставили': 'не доставлять',
        'не успели': 'не успевать',
        'не ответили': 'не отвечать',
        'не пришел': 'не приходить',
        'не разобрались': 'не разбираться',
        'не прислали': 'не присылать',
        'не везут': 'не везти',
        'не приехал': 'не приезжать',
        'не назвали': 'не называть',
        'не связались': 'не связываться',
        'не рассказали': 'не рассказывать',
        'не сообщили': 'не сообщать',
        'не доехал': 'не доезжать',
        'не отправили': 'не отправлять',
        'не заехал': 'не заезжать'
    }
    
    # Проверяем исключения
    if word_lower in exceptions:
        return exceptions[word_lower]
    
    # Простая нормализация для русских глаголов
    if word_lower.endswith('л') or word_lower.endswith('ла') or word_lower.endswith('ло') or word_lower.endswith('ли'):
        # Прошедшее время -> инфинитив
        base = word_lower[:-1] if word_lower.endswith('л') else word_lower[:-2]
        return base + 'ть'
    elif word_lower.endswith('ю') or word_lower.endswith('ешь') or word_lower.endswith('ет') or word_lower.endswith('ем') or word_lower.endswith('ете') or word_lower.endswith('ют'):
        # Личные формы -> инфинитив
        base = word_lower[:-1] if word_lower.endswith('ю') else word_lower[:-2]
        return base + 'ть'
    elif word_lower.endswith('ющий') or word_lower.endswith('ющая') or word_lower.endswith('ющее') or word_lower.endswith('ющие'):
        # Причастие -> инфинитив
        base = word_lower[:-3] if word_lower.endswith('щий') or word_lower.endswith('щая') or word_lower.endswith('щее') or word_lower.endswith('щие') else word_lower[:-4]
        return base + 'ть'
    
    return word_lower


def normalize_word(word: str) -> str:
    """Приводит слово к нормальной форме используя natasha"""
    return normalize_word_natasha(word)


def get_word_forms_fallback(word: str) -> Set[str]:
    """Fallback метод для получения форм слов (старый метод)"""
    if not word:
        return {word}
    
    forms = {word.lower()}
    word_lower = word.lower()
    
    # Для глаголов добавляем основные формы
    if word_lower.endswith('ть'):
        # Инфинитив -> личные формы
        base = word_lower[:-2]
        forms.update([
            base + 'ю', base + 'ешь', base + 'ет', base + 'ем', base + 'ете', base + 'ют',
            base + 'л', base + 'ла', base + 'ло', base + 'ли',
            base + 'ющий', base + 'ющая', base + 'ющее', base + 'ющие'
        ])
    elif word_lower.endswith('л') or word_lower.endswith('ла') or word_lower.endswith('ло') or word_lower.endswith('ли'):
        # Прошедшее время -> инфинитив и другие формы
        base = word_lower[:-1] if word_lower.endswith('л') else word_lower[:-2]
        infinitive = base + 'ть'
        forms.add(infinitive)
        forms.update([
            base + 'ю', base + 'ешь', base + 'ет', base + 'ем', base + 'ете', base + 'ют',
            base + 'ющий', base + 'ющая', base + 'ющее', base + 'ющие'
        ])
    elif word_lower.endswith('ю') or word_lower.endswith('ешь') or word_lower.endswith('ет') or word_lower.endswith('ем') or word_lower.endswith('ете') or word_lower.endswith('ют'):
        # Личные формы -> инфинитив и другие формы
        base = word_lower[:-1] if word_lower.endswith('ю') else word_lower[:-2]
        infinitive = base + 'ть'
        forms.add(infinitive)
        forms.update([
            base + 'л', base + 'ла', base + 'ло', base + 'ли',
            base + 'ющий', base + 'ющая', base + 'ющее', base + 'ющие'
        ])
    
    return forms


def get_word_forms(word: str) -> Set[str]:
    """Получает все возможные формы слова используя natasha"""
    return get_word_forms_natasha(word)


def extract_words_from_text_fallback(text: str) -> List[Dict[str, Any]]:
    """Fallback метод для извлечения слов из текста (старый метод)"""
    import re
    
    if not text:
        return []
    
    # Разбиваем текст на слова, сохраняя позиции
    words = []
    word_pattern = re.compile(r'\b\w+\b', re.UNICODE)
    
    for match in word_pattern.finditer(text):
        word = match.group()
        start_pos = match.start()
        end_pos = match.end()
        
        words.append({
            'word': word,
            'normal_form': normalize_word(word),
            'start_pos': start_pos,
            'end_pos': end_pos,
            'word_forms': get_word_forms(word)
        })
    
    return words


def extract_words_from_text(text: str) -> List[Dict[str, Any]]:
    """Извлекает слова из текста с их позициями и нормальными формами используя natasha"""
    return extract_words_from_text_natasha(text)


class VocaAPIService(LoggerMixin):
    """Сервис для работы с API Voca.tech"""
    
    def __init__(self):
        self.base_url = "https://api.voca.tech/api"
        self.api_key = settings.VOCA_API_KEY
        self.speech_data_path = Path("speech_data")
        self.headers = {
            "accept": "text/plain",
            "X-API-KEY": self.api_key
        }
        
        # Rate limiting: 30 запросов в минуту = 1 запрос каждые 2 секунды
        self.rate_limit_semaphore = asyncio.Semaphore(1)  # Только 1 одновременный запрос
        self.min_request_interval = 2.0  # Минимальный интервал между запросами в секундах
        self.last_request_time = 0
        
        # Создаем папку speech_data если её нет
        self.speech_data_path.mkdir(exist_ok=True)
    
    async def _rate_limited_request(self, url: str, params: Optional[Dict[str, Any]] = None, retry_count: int = 0) -> Any:
        """Выполняет HTTP запрос с соблюдением rate limiting"""
        max_retries = 5  # Максимальное количество попыток
        
        async with self.rate_limit_semaphore:
            # Ждем минимальный интервал между запросами
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                wait_time = self.min_request_interval - time_since_last
                await asyncio.sleep(wait_time)
            
            self.last_request_time = asyncio.get_event_loop().time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        if retry_count >= max_retries:
                            raise Exception(f"Rate limit exceeded after {max_retries} retries")
                        
                        # Rate limit exceeded - ждем дольше
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limit exceeded (attempt {retry_count + 1}/{max_retries}). Waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        # Повторяем запрос с увеличенным счетчиком
                        return await self._rate_limited_request(url, params, retry_count + 1)
                    else:
                        raise Exception(f"API request failed: {response.status} - {await response.text()}")
    
    async def _rate_limited_download(self, url: str, file_path: Path, retry_count: int = 0) -> None:
        """Загружает файл с соблюдением rate limiting"""
        max_retries = 5  # Максимальное количество попыток
        
        async with self.rate_limit_semaphore:
            # Ждем минимальный интервал между запросами
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                wait_time = self.min_request_interval - time_since_last
                await asyncio.sleep(wait_time)
            
            self.last_request_time = asyncio.get_event_loop().time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(await response.read())
                    elif response.status == 429:
                        if retry_count >= max_retries:
                            raise Exception(f"Rate limit exceeded during download after {max_retries} retries")
                        
                        # Rate limit exceeded - ждем дольше
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limit exceeded during download (attempt {retry_count + 1}/{max_retries}). Waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        # Повторяем загрузку с увеличенным счетчиком
                        await self._rate_limited_download(url, file_path, retry_count + 1)
                    else:
                        raise Exception(f"Failed to download file: {response.status}")
    
    def _format_period(self, start_date: datetime, end_date: datetime) -> str:
        """Форматирует период в формат API Voca.tech"""
        return f"s{start_date.strftime('%d.%m.%YT%H-%M')}e{end_date.strftime('%d.%m.%YT%H-%M')}"
    
    def _get_previous_hour_period(self) -> tuple[datetime, datetime]:
        """Возвращает период предыдущего полного часа"""
        now = datetime.now()
        end_hour = now.replace(minute=0, second=0, microsecond=0)
        start_hour = end_hour - timedelta(hours=1)
        return start_hour, end_hour
    
    async def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Выполняет HTTP запрос к API с rate limiting"""
        return await self._rate_limited_request(url, params)
    
    async def _download_audio(self, record_id: int, audio_path: Path) -> None:
        """Загружает аудиофайл по ID записи с rate limiting"""
        audio_url = f"{self.base_url}/audio/records/{record_id}/audio"
        await self._rate_limited_download(audio_url, audio_path)
    
    async def _save_record_info(self, record: Dict[str, Any], record_path: Path) -> None:
        """Сохраняет информацию о записи в JSON файл"""
        json_path = record_path / f"{record['id']}.json"
        async with aiofiles.open(json_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(record, ensure_ascii=False, indent=2))
    
    def _parse_employee_name(self, employee_name: str) -> tuple[str, Optional[str]]:
        """Парсит полное имя сотрудника на имя и фамилию"""
        name_parts = employee_name.strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
        elif len(name_parts) == 1:
            first_name = name_parts[0]
            last_name = None
        else:
            first_name = "Неизвестно"
            last_name = None
        
        return first_name, last_name
    
    async def _ensure_employee_exists(
        self, 
        db: AsyncSession, 
        record: Dict[str, Any]
    ) -> bool:
        """Проверяет существование сотрудника и создает запись если нужно"""
        try:
            employee_id = record['employeeId']
            
            # Проверяем, существует ли уже сотрудник
            existing_employee = await employee_crud.get_by_employee_id(db, employee_id)
            if existing_employee:
                self.logger.info(f"Сотрудник с ID {employee_id} уже существует в базе данных")
                return True
            
            # Парсим имя сотрудника
            first_name, last_name = self._parse_employee_name(record['employeeName'])
            
            # Создаем запись сотрудника
           
            employee_data = EmployeeCreate(
                employee_id=employee_id,
                first_name=first_name,
                last_name=last_name,
                position=record['employeePosition'],
                organization_id=UUID(settings.DEFAULT_ORGANIZATION_ID),
                is_active=True
            )
            
            await employee_crud.create(db, employee_data)
            self.logger.info(f"Создана запись сотрудника: {first_name} {last_name} (ID: {employee_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании записи сотрудника: {e}")
            return False
    
    async def _save_record_to_database(
        self, 
        db: AsyncSession, 
        record: Dict[str, Any], 
        audio_path: Path
    ) -> bool:
        """Сохраняет информацию о записи в базу данных"""
        try:
            # Проверяем, не существует ли уже запись с таким audio_data_id
            existing_record = await audio_data_crud.get_by_audio_data_id(db, record['id'])
            if existing_record:
                self.logger.info(f"Запись с ID {record['id']} уже существует в базе данных")
                return True
            
            # Убеждаемся, что сотрудник существует в базе данных
            employee_created = await self._ensure_employee_exists(db, record)
            if not employee_created:
                self.logger.warning(f"Не удалось создать запись сотрудника для записи {record['id']}")
            
            # Создаем относительный путь к файлу для сохранения в БД
            relative_filename = str(audio_path.relative_to(self.speech_data_path))
            
            # Создаем запись в базе данных
            await audio_data_crud.create_from_voca_record(db, record, relative_filename)
            
            self.logger.info(f"Запись {record['id']} сохранена в базу данных")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении записи {record['id']} в базу данных: {e}")
            return False
    
    async def download_records(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Загружает записи за указанный период
        
        Args:
            start_date: Начало периода (если None, используется предыдущий час)
            end_date: Конец периода (если None, используется предыдущий час)
        
        Returns:
            Список загруженных записей
        """
        # Если период не указан, используем предыдущий час
        if start_date is None or end_date is None:
            start_date, end_date = self._get_previous_hour_period()
        
        # Форматируем период для API
        period = self._format_period(start_date, end_date)
        
        # Получаем список записей
        records_url = f"{self.base_url}/audio/records"
        params = {"period": period}
        
        try:
            records = await self._make_request(records_url, params)
            
            if not records:
                self.logger.info(f"Нет записей за период {period}")
                return []
            
            self.logger.info(f"Найдено {len(records)} записей за период {period}")
            
            # Обрабатываем каждую запись последовательно
            downloaded_records = []
            for i, record in enumerate(records, 1):
                record_id = record['id']
                record_path = self.speech_data_path / str(record_id)
                
                # Создаем папку для записи
                record_path.mkdir(exist_ok=True)
                
                try:
                    # Сохраняем информацию о записи
                    await self._save_record_info(record, record_path)
                    
                    # Загружаем аудиофайл
                    audio_path = record_path / f"{record_id}.wav"
                    await self._download_audio(record_id, audio_path)
                    
                    # Сохраняем запись в базу данных, если передан объект БД
                    if db:
                        db_saved = await self._save_record_to_database(db, record, audio_path)
                        if not db_saved:
                            self.logger.warning(f"Не удалось сохранить запись {record_id} в базу данных")
                    
                    downloaded_records.append(record)
                    self.logger.info(f"Загружена запись {record_id} ({i}/{len(records)}): {record['employeeName']} - {record['durationSec']}с")
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при загрузке записи {record_id}: {e}")
                    continue
            
            self.logger.info(f"Успешно загружено {len(downloaded_records)} записей из {len(records)}")
            return downloaded_records
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении записей: {e}")
            return []
    
    async def download_records_by_date_range(
        self, 
        start_date: str, 
        end_date: str,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Загружает записи по строковым датам
        
        Args:
            start_date: Начало периода в формате "YYYY-MM-DD HH:MM"
            end_date: Конец периода в формате "YYYY-MM-DD HH:MM"
        
        Returns:
            Список загруженных записей
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M")
            return await self.download_records(start_dt, end_dt, db)
        except ValueError as e:
            self.logger.error(f"Ошибка в формате даты: {e}")
            return []
    
    async def get_audio_data_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Получить статистику по аудиозаписям"""
        try:
            total_count = await audio_data_crud.get_total_count(db)
            processed_count = await audio_data_crud.get_processed_count(db)
            unprocessed_count = await audio_data_crud.get_unprocessed_count(db)
            
            processed_percentage = (processed_count / total_count * 100) if total_count > 0 else 0
            
            return {
                "total_count": total_count,
                "processed_count": processed_count,
                "unprocessed_count": unprocessed_count,
                "processed_percentage": round(processed_percentage, 2)
            }
        except Exception as e:
            self.logger.error(f"Ошибка при получении статистики: {e}")
            return {
                "total_count": 0,
                "processed_count": 0,
                "unprocessed_count": 0,
                "processed_percentage": 0.0
            }
    
    async def get_unprocessed_audio_data(self, db: AsyncSession, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить необработанные аудиозаписи"""
        try:
            records = await audio_data_crud.get_unprocessed(db, limit)
            return [
                {
                    "id": record.id,
                    "audio_data_id": record.audio_data_id,
                    "creation_date": record.creation_date,
                    "employee_name": record.employee_name,
                    "duration_sec": record.duration_sec,
                    "filename": record.filename,
                    "is_processed": record.is_processed
                }
                for record in records
            ]
        except Exception as e:
            self.logger.error(f"Ошибка при получении необработанных записей: {e}")
            return []
    
    async def mark_audio_data_as_processed(self, db: AsyncSession, audio_data_id: int) -> bool:
        """Отметить аудиозапись как обработанную"""
        try:
            result = await audio_data_crud.mark_as_processed(db, audio_data_id)
            if result:
                self.logger.info(f"Запись {audio_data_id} отмечена как обработанная")
                return True
            else:
                self.logger.warning(f"Запись {audio_data_id} не найдена")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при отметке записи {audio_data_id} как обработанной: {e}")
            return False


# Создаем экземпляр сервиса
voca_service = VocaAPIService()


class AudioDataProcessor(LoggerMixin):
    """Класс для обработки аудиоданных перед транскрибацией и анализом"""
    
    def __init__(self):
        self.full_speech_data_path = Path("full_speech_data")
        self.speech_data_path = Path("speech_data")
        
        # Создаем папки если их нет
        self.full_speech_data_path.mkdir(exist_ok=True)
        self.speech_data_path.mkdir(exist_ok=True)
    
    def _get_employee_date_folder(self, employee_id: int, date: datetime) -> Path:
        """Получить путь к папке для сотрудника и даты"""
        date_str = date.strftime("%Y-%m-%d")
        folder_name = f"{employee_id}_{date_str}"
        return self.full_speech_data_path / folder_name
    
    def _get_full_audio_filename(self, employee_id: int, date: datetime) -> str:
        """Получить имя файла для склеенного аудио"""
        date_str = date.strftime("%Y-%m-%d")
        return f"{employee_id}_{date_str}_full.wav"
    
    def _get_audio_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Получает информацию об аудиофайле"""
        try:
            audio = AudioSegment.from_file(str(file_path))
            return {
                'channels': audio.channels,
                'sample_width': audio.sample_width,
                'frame_rate': audio.frame_rate,
                'duration_ms': len(audio)
            }
        except Exception as e:
            self.logger.warning(f"Ошибка при получении информации о файле {file_path}: {e}")
            return None
    
    async def _concatenate_audio_files(
        self, 
        audio_files: List[Path], 
        output_path: Path
    ) -> bool:
        """Склеить аудиофайлы в один WAV файл используя pydub"""
        try:
            # Создаем папку если её нет
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Проверяем существование файлов
            valid_files = []
            for audio_file in audio_files:
                if not audio_file.exists():
                    self.logger.warning(f"Файл не существует: {audio_file}")
                    continue
                
                # Проверяем, что файл можно загрузить
                audio_info = self._get_audio_info(audio_file)
                if audio_info:
                    valid_files.append(audio_file)
                    self.logger.info(f"Файл {audio_file.name}: {audio_info['channels']} каналов, "
                                   f"{audio_info['frame_rate']} Hz, {audio_info['duration_ms']}ms")
                else:
                    self.logger.warning(f"Не удалось загрузить файл {audio_file}")
            
            if not valid_files:
                self.logger.error("Нет валидных аудиофайлов для склеивания")
                return False
            
            self.logger.info(f"Найдено {len(valid_files)} валидных файлов из {len(audio_files)}")
            
            # Загружаем первый файл для получения базовых параметров
            try:
                first_audio = AudioSegment.from_file(str(valid_files[0]))
                base_channels = first_audio.channels
                # base_frame_rate = first_audio.frame_rate
                base_frame_rate = settings.FRAME_RATE
                base_sample_width = first_audio.sample_width
            except Exception as e:
                self.logger.error(f"Ошибка при загрузке первого файла {valid_files[0]}: {e}")
                return False
            
            # Склеиваем все файлы
            combined_audio = AudioSegment.empty()
            
            for audio_file in valid_files:
                try:
                    # Загружаем аудиофайл
                    audio = AudioSegment.from_file(str(audio_file))
                    
                    # Приводим к единым параметрам если нужно
                    if audio.channels != base_channels:
                        if base_channels == 1:
                            audio = audio.set_channels(1)
                        else:
                            audio = audio.set_channels(2)
                    
                    if audio.frame_rate != base_frame_rate:
                        audio = audio.set_frame_rate(base_frame_rate)
                    
                    if audio.sample_width != base_sample_width:
                        audio = audio.set_sample_width(base_sample_width)
                    
                    # Добавляем к общему аудио
                    combined_audio += audio
                    self.logger.debug(f"Добавлен файл {audio_file.name} ({len(audio)}ms)")
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка при обработке файла {audio_file}: {e}")
                    continue
            
            if len(combined_audio) == 0:
                self.logger.error("Не удалось склеить аудиофайлы")
                return False
            
            # Экспортируем результат в WAV
            try:
                combined_audio.export(
                    str(output_path),
                    format="wav",
                    parameters=[
                        "-acodec", "pcm_s16le",  # 16-bit PCM
                        "-ar", str(base_frame_rate),  # Sample rate
                        "-ac", str(base_channels)  # Channels
                    ]
                )
                
                self.logger.info(f"Склеен аудиофайл: {output_path} "
                               f"({len(valid_files)} файлов, {len(combined_audio)}ms)")
                return True
                
            except Exception as e:
                self.logger.error(f"Ошибка при экспорте файла {output_path}: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"Ошибка при склеивании аудиофайлов: {e}")
            return False
    
    async def process_employee_audio_data(
        self, 
        db: AsyncSession, 
        employee_id: int, 
        target_date: datetime
    ) -> Optional[str]:
        """
        Обработать аудиоданные для конкретного сотрудника за предыдущие сутки
        
        Args:
            db: Сессия базы данных
            employee_id: ID сотрудника
            target_date: Дата, для которой обрабатываем предыдущие сутки
            
        Returns:
            Путь к склеенному файлу или None в случае ошибки
        """
        try:
            # Получаем предыдущий день
            previous_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            self.logger.info(f"previous_day: {previous_day}")
            # Получаем необработанные записи для сотрудника за предыдущий день
            audio_records = await audio_data_crud.get_unprocessed_by_employee_and_date(
                db, employee_id, previous_day
            )
            
            if not audio_records:
                self.logger.info(f"Нет необработанных записей для сотрудника {employee_id} за {previous_day.date()}")
                return None
            
            self.logger.info(f"Найдено {len(audio_records)} записей для сотрудника {employee_id} за {previous_day.date()}")
            
            # Собираем пути к аудиофайлам
            audio_files = []
            for record in audio_records:
                audio_file_path = self.speech_data_path / record.filename
                if audio_file_path.exists():
                    audio_files.append(audio_file_path)
                else:
                    self.logger.warning(f"Файл не найден: {audio_file_path}")
            
            if not audio_files:
                self.logger.error(f"Нет доступных аудиофайлов для сотрудника {employee_id}")
                return None
            
            # Создаем папку для сотрудника и даты
            employee_folder = self._get_employee_date_folder(employee_id, previous_day)
            employee_folder.mkdir(parents=True, exist_ok=True)
            
            # Формируем имя выходного файла
            output_filename = self._get_full_audio_filename(employee_id, previous_day)
            output_path = employee_folder / output_filename
            # output_path = Path(output_filename)
            
            # Склеиваем аудиофайлы
            success = await self._concatenate_audio_files(audio_files, output_path)
            
            if not success:
                self.logger.error(f"Не удалось склеить аудиофайлы для сотрудника {employee_id}")
                return None
            
            # Отмечаем записи как обработанные
            audio_data_ids = [record.audio_data_id for record in audio_records]
            updated_count = await audio_data_crud.mark_multiple_as_processed(db, audio_data_ids)
            
            if updated_count != len(audio_data_ids):
                self.logger.warning(f"Обновлено {updated_count} из {len(audio_data_ids)} записей")
            
            # Создаем запись в таблице audio_data_for_analysis
            # relative_filename = str(output_path.relative_to(self.full_speech_data_path))
            relative_filename = output_path.name
            await audio_data_for_analysis_crud.create_or_update_for_employee_date(
                db, employee_id, previous_day, relative_filename
            )
            
            self.logger.info(f"Успешно обработаны аудиоданные для сотрудника {employee_id}: {relative_filename}")
            return relative_filename
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке аудиоданных для сотрудника {employee_id}: {e}")
            return None
    
    async def process_all_audio_data(
        self, 
        db: AsyncSession, 
        target_date: datetime = None
    ) -> Dict[int, str]:
        """
        Обработать аудиоданные для всех сотрудников за предыдущие сутки
        
        Args:
            db: Сессия базы данных
            target_date: Дата, для которой обрабатываем предыдущие сутки (если None, используется текущая дата)
            
        Returns:
            Словарь {employee_id: filename} с результатами обработки
        """
        if target_date is None:
            target_date = datetime.now()
        
        try:
            # Получаем все необработанные записи за предыдущие сутки
            all_records = await audio_data_crud.get_unprocessed_by_previous_day(db, target_date)
            
            if not all_records:
                self.logger.info(f"Нет необработанных записей за предыдущие сутки от {target_date.date()}")
                return {}
            
            # Группируем записи по сотрудникам
            employee_records = {}
            for record in all_records:
                if record.employee_id not in employee_records:
                    employee_records[record.employee_id] = []
                employee_records[record.employee_id].append(record)
            
            self.logger.info(f"Найдено {len(employee_records)} сотрудников с необработанными записями")
            
            # Обрабатываем каждого сотрудника
            results = {}
            for employee_id, records in employee_records.items():
                self.logger.info(f"Обрабатываем сотрудника {employee_id} ({len(records)} записей)")
                
                filename = await self.process_employee_audio_data(db, employee_id, target_date)
                if filename:
                    results[employee_id] = filename
                
                # Небольшая пауза между обработкой сотрудников
                await asyncio.sleep(0.1)
            
            self.logger.info(f"Обработано {len(results)} сотрудников из {len(employee_records)}")
            return results
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке всех аудиоданных: {e}")
            return {}


# Создаем экземпляр процессора аудиоданных
audio_processor = AudioDataProcessor()


class DialogTextHighlighter(LoggerMixin):
    """Сервис для подсветки слов в тексте диалогов на основе словарей"""
    
    def __init__(self):
        self._phrase_cache = None
        self._dictionary_cache = None
    
    async def _load_phrases_and_dictionaries(self, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        """Загружает все фразы и словари в кэш с поддержкой однокоренных слов"""
        if self._phrase_cache is not None:
            return self._phrase_cache
        
        from app.models.dialogs import Phrase, Dictionary
        from sqlalchemy import select
        
        # Загружаем все фразы с их словарями
        query = select(
            Phrase.phrase,
            Phrase.normal_form,
            Dictionary.id,
            Dictionary.title,
            Dictionary.color
        ).join(Dictionary, Phrase.dictionary_id == Dictionary.id)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        # Создаем кэш: {phrase: {dictionary_id, title, color, normal_form, word_forms}}
        phrase_cache = {}
        for row in rows:
            # Используем нормализованную форму из БД, если она есть
            normal_form = row.normal_form if row.normal_form else normalize_word(row.phrase)
            
            # Получаем все формы слова для поиска однокоренных слов
            word_forms = get_word_forms(row.phrase)
            
            phrase_info = {
                'dictionary_id': row.id,
                'title': row.title,
                'color': row.color or '#000000',
                'normal_form': normal_form,
                'word_forms': word_forms
            }
            
            # Добавляем оригинальную фразу
            phrase_cache[row.phrase] = phrase_info
            
            # Добавляем нормализованную форму из БД
            phrase_cache[normal_form] = phrase_info
            
            # Добавляем все формы слова
            for form in word_forms:
                phrase_cache[form] = phrase_info
        
        self._phrase_cache = phrase_cache
        return phrase_cache
    
    def _find_phrases_in_text(self, text: str, phrase_cache: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Находит все фразы из словарей в тексте с поддержкой однокоренных слов"""
        import re
        
        found_phrases = []
        text_lower = text.lower()
        
        # Извлекаем слова из текста с их нормальными формами
        text_words = extract_words_from_text(text)
        
        # Создаем словарь для быстрого поиска по нормальным формам
        text_normal_forms = {}
        for word_info in text_words:
            text_normal_forms[word_info['normal_form']] = word_info
            # Также добавляем все формы слова
            for form in word_info['word_forms']:
                text_normal_forms[form] = word_info
        
        # Сортируем фразы по длине (от длинных к коротким), чтобы избежать частичных совпадений
        sorted_phrases = sorted(phrase_cache.keys(), key=len, reverse=True)
        
        for phrase in sorted_phrases:
            phrase_lower = phrase.lower()
            phrase_info = phrase_cache[phrase]
            
            # Проверяем точное совпадение
            if phrase_lower in text_normal_forms:
                word_info = text_normal_forms[phrase_lower]
                found_phrases.append({
                    'phrase': word_info['word'],
                    'start_pos': word_info['start_pos'],
                    'end_pos': word_info['end_pos'],
                    'dictionary_info': phrase_info
                })
                continue
            
            # Проверяем совпадение по нормальной форме
            if phrase_info['normal_form'] in text_normal_forms:
                word_info = text_normal_forms[phrase_info['normal_form']]
                found_phrases.append({
                    'phrase': word_info['word'],
                    'start_pos': word_info['start_pos'],
                    'end_pos': word_info['end_pos'],
                    'dictionary_info': phrase_info
                })
                continue
            
            # Проверяем совпадение по формам слова
            for form in phrase_info['word_forms']:
                if form in text_normal_forms:
                    word_info = text_normal_forms[form]
                    found_phrases.append({
                        'phrase': word_info['word'],
                        'start_pos': word_info['start_pos'],
                        'end_pos': word_info['end_pos'],
                        'dictionary_info': phrase_info
                    })
                    break
        
        # Сортируем по позиции в тексте
        found_phrases.sort(key=lambda x: x['start_pos'])
        
        # Удаляем перекрывающиеся фразы (оставляем самые длинные)
        filtered_phrases = []
        for phrase_info in found_phrases:
            is_overlapping = False
            for existing_phrase in filtered_phrases:
                if (phrase_info['start_pos'] < existing_phrase['end_pos'] and 
                    phrase_info['end_pos'] > existing_phrase['start_pos']):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered_phrases.append(phrase_info)
        
        return filtered_phrases
    
    def _is_word_boundary(self, text: str, start_pos: int, end_pos: int) -> bool:
        """Проверяет, что найденная фраза является отдельным словом/фразой"""
        import re
        
        # Определяем границы слова
        word_boundary_pattern = r'\b'
        
        # Проверяем начало
        if start_pos > 0:
            before_text = text[:start_pos]
            if not re.search(r'\W$', before_text) and not re.search(r'\s$', before_text):
                return False
        
        # Проверяем конец
        if end_pos < len(text):
            after_text = text[end_pos:]
            if not re.search(r'^\W', after_text) and not re.search(r'^\s', after_text):
                return False
        
        return True
    
    def _highlight_text_with_phrases(self, text: str, found_phrases: List[Dict[str, Any]]) -> str:
        """Подсвечивает найденные фразы в тексте HTML-тегами"""
        if not found_phrases:
            return text
        
        # Создаем список изменений (позиция, тип, данные)
        changes = []
        
        for phrase_info in found_phrases:
            # Добавляем открывающий тег
            changes.append({
                'pos': phrase_info['start_pos'],
                'type': 'open',
                'data': phrase_info
            })
            # Добавляем закрывающий тег
            changes.append({
                'pos': phrase_info['end_pos'],
                'type': 'close',
                'data': phrase_info
            })
        
        # Сортируем изменения по позиции
        changes.sort(key=lambda x: x['pos'])
        
        # Применяем изменения к тексту
        result = ""
        last_pos = 0
        
        for change in changes:
            # Добавляем текст до изменения
            result += text[last_pos:change['pos']]
            
            if change['type'] == 'open':
                # Добавляем открывающий тег с цветом
                color = change['data']['dictionary_info']['color']
                title = change['data']['dictionary_info']['title']
                result += f'<span style="background-color: {color}; color: white; padding: 1px 3px; border-radius: 3px;" title="{title}">'
            else:
                # Добавляем закрывающий тег
                result += '</span>'
            
            last_pos = change['pos']
        
        # Добавляем оставшийся текст
        result += text[last_pos:]
        
        return result
    
    async def highlight_dialog_text(self, db: AsyncSession, dialog_id: UUID) -> Optional[str]:
        """Подсвечивает текст диалога найденными фразами из словарей и обновляет его в БД"""
        try:
            from app.models.dialogs import Dialog
            from sqlalchemy import select, update
            
            # Получаем диалог
            query = select(Dialog).where(Dialog.id == dialog_id)
            result = await db.execute(query)
            dialog = result.scalar_one_or_none()
            
            if not dialog:
                self.logger.warning(f"Диалог с ID {dialog_id} не найден")
                return None
            
            # Загружаем фразы и словари
            phrase_cache = await self._load_phrases_and_dictionaries(db)
            
            # Находим фразы в тексте
            found_phrases = self._find_phrases_in_text(dialog.conversation, phrase_cache)
            
            if not found_phrases:
                self.logger.info(f"В диалоге {dialog_id} не найдено фраз из словарей")
                return dialog.conversation
            
            # Подсвечиваем текст
            highlighted_text = self._highlight_text_with_phrases(dialog.conversation, found_phrases)
            
            # Обновляем запись в БД
            stmt = update(Dialog).where(Dialog.id == dialog_id).values(conversation=highlighted_text)
            await db.execute(stmt)
            await db.commit()
            
            self.logger.info(f"В диалоге {dialog_id} найдено и подсвечено {len(found_phrases)} фраз, обновлено в БД")
            
            return highlighted_text
            
        except Exception as e:
            self.logger.error(f"Ошибка при подсветке текста диалога {dialog_id}: {e}")
            await db.rollback()
            return None
    
    async def highlight_all_dialogs(self, db: AsyncSession, organization_id: Optional[UUID] = None) -> Dict[UUID, str]:
        """Подсвечивает текст всех диалогов организации и обновляет их в БД"""
        try:
            from app.models.dialogs import Dialog
            from app.models.users import Employee
            from sqlalchemy import select, update
            
            # Формируем запрос
            query = select(Dialog.id, Dialog.conversation).join(Employee, Dialog.employee_id == Employee.id)
            
            if organization_id:
                query = query.where(Employee.organization_id == organization_id)
            
            result = await db.execute(query)
            dialogs = result.fetchall()
            
            if not dialogs:
                self.logger.info("Не найдено диалогов для подсветки")
                return {}
            
            # Загружаем фразы и словари
            phrase_cache = await self._load_phrases_and_dictionaries(db)
            
            highlighted_dialogs = {}
            updated_count = 0
            
            for dialog in dialogs:
                try:
                    # Находим фразы в тексте
                    found_phrases = self._find_phrases_in_text(dialog.conversation, phrase_cache)
                    
                    if found_phrases:
                        # Подсвечиваем текст
                        highlighted_text = self._highlight_text_with_phrases(dialog.conversation, found_phrases)
                        highlighted_dialogs[dialog.id] = highlighted_text
                        
                        # Обновляем запись в БД
                        stmt = update(Dialog).where(Dialog.id == dialog.id).values(conversation=highlighted_text)
                        await db.execute(stmt)
                        updated_count += 1
                        
                        self.logger.info(f"В диалоге {dialog.id} найдено и подсвечено {len(found_phrases)} фраз")
                    else:
                        # Если фразы не найдены, возвращаем оригинальный текст
                        highlighted_dialogs[dialog.id] = dialog.conversation
                        
                except Exception as e:
                    self.logger.error(f"Ошибка при подсветке диалога {dialog.id}: {e}")
                    # В случае ошибки возвращаем оригинальный текст
                    highlighted_dialogs[dialog.id] = dialog.conversation
            
            # Коммитим все изменения
            await db.commit()
            
            self.logger.info(f"Подсвечено {len(highlighted_dialogs)} диалогов, обновлено в БД: {updated_count}")
            return highlighted_dialogs
            
        except Exception as e:
            self.logger.error(f"Ошибка при подсветке всех диалогов: {e}")
            # Откатываем изменения в случае ошибки
            await db.rollback()
            return {}

    async def highlight_dialogs_by_dictionary(
        self,
        db: AsyncSession,
        dictionary_id: UUID,
        organization_id: Optional[UUID] = None
    ) -> Dict[UUID, str]:
        """Подсвечивает текст диалогов организации только словами из указанного словаря и обновляет их в БД"""
        try:
            from app.models.dialogs import Dialog
            from app.models.users import Employee
            from sqlalchemy import select, update

            # Получаем диалоги
            query = select(Dialog.id, Dialog.conversation).join(Employee, Dialog.employee_id == Employee.id)
            if organization_id:
                query = query.where(Employee.organization_id == organization_id)

            result = await db.execute(query)
            dialogs = result.fetchall()

            if not dialogs:
                self.logger.info("Не найдено диалогов для подсветки по словарю")
                return {}

            # Загружаем кэш фраз и фильтруем по словарю
            phrase_cache = await self._load_phrases_and_dictionaries(db)
            filtered_cache = {
                phrase: info for phrase, info in phrase_cache.items() if info.get('dictionary_id') == dictionary_id
            }

            if not filtered_cache:
                self.logger.info(f"Для словаря {dictionary_id} нет фраз")
                return {}

            highlighted_dialogs: Dict[UUID, str] = {}
            updated_count = 0

            for dialog in dialogs:
                try:
                    found_phrases = self._find_phrases_in_text(dialog.conversation, filtered_cache)
                    if found_phrases:
                        highlighted_text = self._highlight_text_with_phrases(dialog.conversation, found_phrases)
                        highlighted_dialogs[dialog.id] = highlighted_text

                        # Обновляем запись в БД
                        stmt = update(Dialog).where(Dialog.id == dialog.id).values(conversation=highlighted_text)
                        await db.execute(stmt)
                        updated_count += 1
                        self.logger.info(
                            f"В диалоге {dialog.id} подсвечено {len(found_phrases)} фраз по словарю {dictionary_id}"
                        )
                    else:
                        highlighted_dialogs[dialog.id] = dialog.conversation
                except Exception as e:
                    self.logger.error(
                        f"Ошибка при подсветке диалога {dialog.id} по словарю {dictionary_id}: {e}"
                    )
                    highlighted_dialogs[dialog.id] = dialog.conversation

            await db.commit()
            self.logger.info(
                f"Подсветка по словарю {dictionary_id}: обработано {len(highlighted_dialogs)}, обновлено {updated_count}"
            )
            return highlighted_dialogs

        except Exception as e:
            self.logger.error(f"Ошибка при подсветке диалогов по словарю {dictionary_id}: {e}")
            await db.rollback()
            return {}
    
    def clear_cache(self):
        """Очищает кэш фраз и словарей"""
        self._phrase_cache = None
        self._dictionary_cache = None


# Создаем экземпляр сервиса подсветки
dialog_highlighter = DialogTextHighlighter()


class DialogDictionaryPopulator(LoggerMixin):
    """Сервис для заполнения таблицы dialog_dictionary на основе найденных слов в диалогах"""
    
    def __init__(self):
        self._phrase_cache = None
    
    async def _load_phrases_and_dictionaries(self, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        """Загружает все фразы и словари в кэш с поддержкой однокоренных слов"""
        if self._phrase_cache is not None:
            return self._phrase_cache
        
        from app.models.dialogs import Phrase, Dictionary
        from sqlalchemy import select
        
        # Загружаем все фразы с их словарями
        query = select(
            Phrase.phrase,
            Phrase.normal_form,
            Dictionary.id,
            Dictionary.title,
            Dictionary.color
        ).join(Dictionary, Phrase.dictionary_id == Dictionary.id)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        # Создаем кэш: {phrase: {dictionary_id, title, color, normal_form, word_forms}}
        phrase_cache = {}
        for row in rows:
            # Используем нормализованную форму из БД, если она есть
            normal_form = row.normal_form if row.normal_form else normalize_word(row.phrase)
            
            # Получаем все формы слова для поиска однокоренных слов
            word_forms = get_word_forms(row.phrase)
            
            phrase_info = {
                'dictionary_id': row.id,
                'title': row.title,
                'color': row.color or '#000000',
                'normal_form': normal_form,
                'word_forms': word_forms
            }
            
            # Добавляем оригинальную фразу
            phrase_cache[row.phrase] = phrase_info
            
            # Добавляем нормализованную форму из БД
            phrase_cache[normal_form] = phrase_info
            
            # Добавляем все формы слова
            for form in word_forms:
                phrase_cache[form] = phrase_info
        
        self._phrase_cache = phrase_cache
        return phrase_cache
    
    def _find_phrases_in_text(self, text: str, phrase_cache: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Находит все фразы из словарей в тексте с поддержкой однокоренных слов"""
        import re
        
        found_phrases = []
        text_lower = text.lower()
        
        # Извлекаем слова из текста с их нормальными формами
        text_words = extract_words_from_text(text)
        
        # Создаем словарь для быстрого поиска по нормальным формам
        text_normal_forms = {}
        for word_info in text_words:
            text_normal_forms[word_info['normal_form']] = word_info
            # Также добавляем все формы слова
            for form in word_info['word_forms']:
                text_normal_forms[form] = word_info
        
        # Сортируем фразы по длине (от длинных к коротким), чтобы избежать частичных совпадений
        sorted_phrases = sorted(phrase_cache.keys(), key=len, reverse=True)
        
        for phrase in sorted_phrases:
            phrase_lower = phrase.lower()
            phrase_info = phrase_cache[phrase]
            
            # Проверяем точное совпадение
            if phrase_lower in text_normal_forms:
                word_info = text_normal_forms[phrase_lower]
                found_phrases.append({
                    'phrase': word_info['word'],
                    'start_pos': word_info['start_pos'],
                    'end_pos': word_info['end_pos'],
                    'dictionary_info': phrase_info
                })
                continue
            
            # Проверяем совпадение по нормальной форме
            if phrase_info['normal_form'] in text_normal_forms:
                word_info = text_normal_forms[phrase_info['normal_form']]
                found_phrases.append({
                    'phrase': word_info['word'],
                    'start_pos': word_info['start_pos'],
                    'end_pos': word_info['end_pos'],
                    'dictionary_info': phrase_info
                })
                continue
            
            # Проверяем совпадение по формам слова
            for form in phrase_info['word_forms']:
                if form in text_normal_forms:
                    word_info = text_normal_forms[form]
                    found_phrases.append({
                        'phrase': word_info['word'],
                        'start_pos': word_info['start_pos'],
                        'end_pos': word_info['end_pos'],
                        'dictionary_info': phrase_info
                    })
                    break
        
        # Сортируем по позиции в тексте
        found_phrases.sort(key=lambda x: x['start_pos'])
        
        # Удаляем перекрывающиеся фразы (оставляем самые длинные)
        filtered_phrases = []
        for phrase_info in found_phrases:
            is_overlapping = False
            for existing_phrase in filtered_phrases:
                if (phrase_info['start_pos'] < existing_phrase['end_pos'] and 
                    phrase_info['end_pos'] > existing_phrase['start_pos']):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered_phrases.append(phrase_info)
        
        return filtered_phrases
    
    def _is_word_boundary(self, text: str, start_pos: int, end_pos: int) -> bool:
        """Проверяет, что найденная фраза является отдельным словом/фразой"""
        import re
        
        # Определяем границы слова
        word_boundary_pattern = r'\b'
        
        # Проверяем начало
        if start_pos > 0:
            before_text = text[:start_pos]
            if not re.search(r'\W$', before_text) and not re.search(r'\s$', before_text):
                return False
        
        # Проверяем конец
        if end_pos < len(text):
            after_text = text[end_pos:]
            if not re.search(r'^\W', after_text) and not re.search(r'^\s', after_text):
                return False
        
        return True
    
    async def _get_existing_dialog_dictionaries(self, db: AsyncSession, dialog_id: UUID) -> Set[UUID]:
        """Получает существующие связи диалога со словарями"""
        from app.models.dialogs import DialogDictionary
        from sqlalchemy import select
        
        query = select(DialogDictionary.dictionary_id).where(DialogDictionary.dialog_id == dialog_id)
        result = await db.execute(query)
        return {row.dictionary_id for row in result.fetchall()}
    
    async def populate_dialog_dictionary(self, db: AsyncSession, dialog_id: UUID) -> Dict[str, Any]:
        """Заполняет таблицу dialog_dictionary для конкретного диалога"""
        try:
            from app.models.dialogs import Dialog, DialogDictionary
            from sqlalchemy import select
            
            # Получаем диалог
            query = select(Dialog).where(Dialog.id == dialog_id)
            result = await db.execute(query)
            dialog = result.scalar_one_or_none()
            
            if not dialog:
                self.logger.warning(f"Диалог с ID {dialog_id} не найден")
                return {"success": False, "message": "Диалог не найден", "added_count": 0}
            
            # Загружаем фразы и словари
            phrase_cache = await self._load_phrases_and_dictionaries(db)
            
            # Находим фразы в тексте
            found_phrases = self._find_phrases_in_text(dialog.conversation, phrase_cache)
            
            if not found_phrases:
                self.logger.info(f"В диалоге {dialog_id} не найдено фраз из словарей")
                return {"success": True, "message": "Фразы не найдены", "added_count": 0}
            
            # Получаем существующие связи
            existing_dictionary_ids = await self._get_existing_dialog_dictionaries(db, dialog_id)
            
            # Собираем уникальные словари из найденных фраз
            found_dictionary_ids = set()
            for phrase_info in found_phrases:
                found_dictionary_ids.add(phrase_info['dictionary_info']['dictionary_id'])
            
            # Определяем новые связи для добавления
            new_dictionary_ids = found_dictionary_ids - existing_dictionary_ids
            
            if not new_dictionary_ids:
                self.logger.info(f"Для диалога {dialog_id} все связи со словарями уже существуют")
                return {
                    "success": True, 
                    "message": "Все связи уже существуют", 
                    "added_count": 0,
                    "total_found": len(found_dictionary_ids)
                }
            
            # Создаем новые записи в dialog_dictionary
            new_records = []
            for dictionary_id in new_dictionary_ids:
                new_records.append(DialogDictionary(
                    dialog_id=dialog_id,
                    dictionary_id=dictionary_id
                ))
            
            # Добавляем записи в базу данных
            db.add_all(new_records)
            await db.commit()
            
            self.logger.info(f"Для диалога {dialog_id} добавлено {len(new_records)} новых связей со словарями")
            
            return {
                "success": True,
                "message": f"Добавлено {len(new_records)} новых связей",
                "added_count": len(new_records),
                "total_found": len(found_dictionary_ids),
                "found_phrases_count": len(found_phrases)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при заполнении dialog_dictionary для диалога {dialog_id}: {e}")
            await db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}", "added_count": 0}
    
    async def populate_all_dialogs_dictionaries(self, db: AsyncSession, organization_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Заполняет таблицу dialog_dictionary для всех диалогов организации"""
        try:
            from app.models.dialogs import Dialog
            from app.models.users import Employee
            from sqlalchemy import select
            
            # Формируем запрос
            query = select(Dialog.id, Dialog.conversation).join(Employee, Dialog.employee_id == Employee.id)
            
            if organization_id:
                query = query.where(Employee.organization_id == organization_id)
            
            result = await db.execute(query)
            dialogs = result.fetchall()
            
            if not dialogs:
                self.logger.info("Не найдено диалогов для заполнения словарей")
                return {
                    "success": True,
                    "message": "Не найдено диалогов",
                    "processed_count": 0,
                    "total_added": 0
                }
            
            self.logger.info(f"Найдено {len(dialogs)} диалогов для обработки")
            
            total_added = 0
            processed_count = 0
            errors = []
            
            for dialog in dialogs:
                try:
                    result = await self.populate_dialog_dictionary(db, dialog.id)
                    if result["success"]:
                        total_added += result["added_count"]
                        processed_count += 1
                        
                        if result["added_count"] > 0:
                            self.logger.info(f"Диалог {dialog.id}: добавлено {result['added_count']} связей")
                    else:
                        errors.append(f"Диалог {dialog.id}: {result['message']}")
                        
                except Exception as e:
                    error_msg = f"Диалог {dialog.id}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            self.logger.info(f"Обработано {processed_count} диалогов, добавлено {total_added} связей")
            
            return {
                "success": True,
                "message": f"Обработано {processed_count} диалогов, добавлено {total_added} связей",
                "processed_count": processed_count,
                "total_added": total_added,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при заполнении словарей для всех диалогов: {e}")
            return {
                "success": False,
                "message": f"Ошибка: {str(e)}",
                "processed_count": 0,
                "total_added": 0
            }
    
    async def clear_dialog_dictionaries(self, db: AsyncSession, dialog_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Очищает связи диалогов со словарями"""
        try:
            from app.models.dialogs import DialogDictionary
            from sqlalchemy import delete
            
            if dialog_id:
                # Удаляем связи для конкретного диалога
                query = delete(DialogDictionary).where(DialogDictionary.dialog_id == dialog_id)
                result = await db.execute(query)
                await db.commit()
                
                deleted_count = result.rowcount
                self.logger.info(f"Удалено {deleted_count} связей для диалога {dialog_id}")
                
                return {
                    "success": True,
                    "message": f"Удалено {deleted_count} связей для диалога {dialog_id}",
                    "deleted_count": deleted_count
                }
            else:
                # Удаляем все связи
                query = delete(DialogDictionary)
                result = await db.execute(query)
                await db.commit()
                
                deleted_count = result.rowcount
                self.logger.info(f"Удалено {deleted_count} связей для всех диалогов")
                
                return {
                    "success": True,
                    "message": f"Удалено {deleted_count} связей для всех диалогов",
                    "deleted_count": deleted_count
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка при очистке связей диалогов со словарями: {e}")
            await db.rollback()
            return {
                "success": False,
                "message": f"Ошибка: {str(e)}",
                "deleted_count": 0
            }

    async def populate_dialog_dictionary_by_dictionary(
        self,
        db: AsyncSession,
        dialog_id: UUID,
        dictionary_id: UUID
    ) -> Dict[str, Any]:
        """Заполняет связь dialog_dictionary для конкретного диалога ТОЛЬКО по указанному словарю"""
        try:
            from app.models.dialogs import Dialog, DialogDictionary
            from sqlalchemy import select

            # Получаем диалог
            query = select(Dialog).where(Dialog.id == dialog_id)
            result = await db.execute(query)
            dialog = result.scalar_one_or_none()

            if not dialog:
                self.logger.warning(f"Диалог с ID {dialog_id} не найден")
                return {"success": False, "message": "Диалог не найден", "added_count": 0}

            # Загружаем фразы и словари
            phrase_cache = await self._load_phrases_and_dictionaries(db)

            # Находим фразы в тексте
            found_phrases = self._find_phrases_in_text(dialog.conversation, phrase_cache)

            # Фильтруем по нужному словарю
            filtered_phrases = [p for p in found_phrases if p['dictionary_info']['dictionary_id'] == dictionary_id]

            if not filtered_phrases:
                self.logger.info(f"В диалоге {dialog_id} не найдено фраз из словаря {dictionary_id}")
                return {
                    "success": True,
                    "message": "Фразы не найдены",
                    "added_count": 0,
                    "total_found": 0,
                    "found_phrases_count": 0
                }

            # Проверяем, существует ли уже связь
            exists_query = select(DialogDictionary).where(
                DialogDictionary.dialog_id == dialog_id,
                DialogDictionary.dictionary_id == dictionary_id
            )
            exists_result = await db.execute(exists_query)
            exists = exists_result.scalar_one_or_none()

            if exists:
                self.logger.info(f"Для диалога {dialog_id} связь со словарем {dictionary_id} уже существует")
                return {
                    "success": True,
                    "message": "Связь уже существует",
                    "added_count": 0,
                    "total_found": 1,
                    "found_phrases_count": len(filtered_phrases)
                }

            # Добавляем новую связь
            record = DialogDictionary(dialog_id=dialog_id, dictionary_id=dictionary_id)
            db.add(record)
            await db.commit()

            self.logger.info(f"Для диалога {dialog_id} добавлена связь со словарем {dictionary_id}")

            return {
                "success": True,
                "message": "Добавлена 1 связь",
                "added_count": 1,
                "total_found": 1,
                "found_phrases_count": len(filtered_phrases)
            }

        except Exception as e:
            self.logger.error(f"Ошибка при заполнении dialog_dictionary для диалога {dialog_id} по словарю {dictionary_id}: {e}")
            await db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}", "added_count": 0}

    async def populate_all_dialogs_by_dictionary(
        self,
        db: AsyncSession,
        dictionary_id: UUID,
        organization_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Заполняет dialog_dictionary для всех диалогов организации ТОЛЬКО по указанному словарю"""
        try:
            from app.models.dialogs import Dialog, DialogDictionary
            from app.models.users import Employee
            from sqlalchemy import select

            # Выбираем диалоги
            query = select(Dialog.id, Dialog.conversation).join(Employee, Dialog.employee_id == Employee.id)
            if organization_id:
                query = query.where(Employee.organization_id == organization_id)

            result = await db.execute(query)
            dialogs = result.fetchall()

            if not dialogs:
                self.logger.info("Не найдено диалогов для заполнения связей по словарю")
                return {
                    "success": True,
                    "message": "Не найдено диалогов",
                    "processed_count": 0,
                    "total_added": 0
                }

            # Загружаем кэш фраз
            phrase_cache = await self._load_phrases_and_dictionaries(db)

            processed_count = 0
            total_added = 0
            errors: list[str] = []

            for dialog in dialogs:
                try:
                    # Находим фразы
                    found_phrases = self._find_phrases_in_text(dialog.conversation, phrase_cache)
                    has_target_dict = any(
                        p['dictionary_info']['dictionary_id'] == dictionary_id for p in found_phrases
                    )

                    if not has_target_dict:
                        processed_count += 1
                        continue

                    # Проверяем существование связи
                    exists_query = select(DialogDictionary).where(
                        DialogDictionary.dialog_id == dialog.id,
                        DialogDictionary.dictionary_id == dictionary_id
                    )
                    exists_result = await db.execute(exists_query)
                    exists = exists_result.scalar_one_or_none()

                    if exists:
                        processed_count += 1
                        continue

                    # Добавляем связь
                    db.add(DialogDictionary(dialog_id=dialog.id, dictionary_id=dictionary_id))
                    await db.commit()
                    total_added += 1
                    processed_count += 1
                except Exception as e:
                    error_msg = f"Диалог {dialog.id}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    await db.rollback()

            return {
                "success": True,
                "message": f"Обработано {processed_count} диалогов, добавлено {total_added} связей",
                "processed_count": processed_count,
                "total_added": total_added,
                "errors": errors if errors else None
            }

        except Exception as e:
            self.logger.error(f"Ошибка при заполнении словарей по словарю {dictionary_id} для всех диалогов: {e}")
            return {
                "success": False,
                "message": f"Ошибка: {str(e)}",
                "processed_count": 0,
                "total_added": 0
            }
    
    def clear_cache(self):
        """Очищает кэш фраз и словарей"""
        self._phrase_cache = None


# Создаем экземпляр сервиса заполнения словарей
dialog_dictionary_populator = DialogDictionaryPopulator()
