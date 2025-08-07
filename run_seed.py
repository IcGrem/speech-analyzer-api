#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных фейковыми данными
"""

import sys
import os

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.seed_data import seed_data
import asyncio

if __name__ == "__main__":
    print("Начинаем заполнение базы данных фейковыми данными...")
    asyncio.run(seed_data())
    print("Заполнение завершено!") 