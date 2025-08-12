#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы AudioDataProcessor
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from app.services.dialog_service import audio_processor
from app.db.session import async_session_maker


async def test_audio_processor():
    """Тестируем работу AudioDataProcessor"""
    
    print("Тестирование AudioDataProcessor...")
    
    async with async_session_maker() as db:
        try:
            # Тестируем обработку всех аудиоданных за предыдущие сутки
            print("Обрабатываем аудиоданные за предыдущие сутки...")
            results = await audio_processor.process_all_audio_data(db)
            
            if results:
                print(f"Успешно обработано {len(results)} сотрудников:")
                for employee_id, filename in results.items():
                    print(f"  Сотрудник {employee_id}: {filename}")
            else:
                print("Нет данных для обработки")
                
        except Exception as e:
            print(f"Ошибка при тестировании: {e}")


if __name__ == "__main__":
    asyncio.run(test_audio_processor())
