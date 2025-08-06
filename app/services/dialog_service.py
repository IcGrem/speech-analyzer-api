import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiohttp
import aiofiles

from app.core.config import settings
from app.core.logging import LoggerMixin


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
        
        # Создаем папку speech_data если её нет
        self.speech_data_path.mkdir(exist_ok=True)
    
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
        """Выполняет HTTP запрос к API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"API request failed: {response.status} - {await response.text()}")
    
    async def _download_audio(self, record_id: int, audio_path: Path) -> None:
        """Загружает аудиофайл по ID записи"""
        audio_url = f"{self.base_url}/audio/records/{record_id}/audio"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url, headers=self.headers) as response:
                if response.status == 200:
                    async with aiofiles.open(audio_path, 'wb') as f:
                        await f.write(await response.read())
                else:
                    raise Exception(f"Failed to download audio for record {record_id}: {response.status}")
    
    async def _save_record_info(self, record: Dict[str, Any], record_path: Path) -> None:
        """Сохраняет информацию о записи в JSON файл"""
        json_path = record_path / f"{record['id']}.json"
        async with aiofiles.open(json_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(record, ensure_ascii=False, indent=2))
    
    async def download_records(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
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
            
            # Обрабатываем каждую запись
            downloaded_records = []
            for record in records:
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
                    
                    downloaded_records.append(record)
                    self.logger.info(f"Загружена запись {record_id}: {record['employeeName']} - {record['durationSec']}с")
                    
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
        end_date: str
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
            return await self.download_records(start_dt, end_dt)
        except ValueError as e:
            self.logger.error(f"Ошибка в формате даты: {e}")
            return []


# Создаем экземпляр сервиса
voca_service = VocaAPIService()
