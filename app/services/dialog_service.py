import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiohttp
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydub import AudioSegment

# Устанавливаем пути к ffmpeg для pydub
import os
os.environ["PATH"] = "C:\\Program Files\\ffmpeg\\bin;" + os.environ.get("PATH", "")

AudioSegment.converter = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
AudioSegment.ffmpeg = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
AudioSegment.ffprobe = "C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe"

from app.core.config import settings
from app.core.logging import LoggerMixin
from app.crud.audio_data import audio_data_crud, audio_data_for_analysis_crud
from app.crud.users import employee_crud
from app.schemas.users import EmployeeCreate



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
                base_frame_rate = first_audio.frame_rate
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
            # output_path = employee_folder / output_filename
            output_path = output_filename
            
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
            relative_filename = str(output_path.relative_to(self.full_speech_data_path))
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
