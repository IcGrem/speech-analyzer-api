#!/usr/bin/env python3
"""
Тест склеивания аудиофайлов
"""

import wave
import numpy as np
from pathlib import Path


def create_test_wav_file(filename: str, duration_seconds: float = 1.0, sample_rate: int = 16000):
    """Создать тестовый WAV файл"""
    # Генерируем простой синусоидальный сигнал
    frequency = 440  # 440 Hz
    samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, samples, False)
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Преобразуем в 16-bit PCM
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Записываем WAV файл
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Моно
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())


def concatenate_audio_files(audio_files: list, output_path: str) -> bool:
    """Склеить аудиофайлы в один WAV файл"""
    try:
        # Читаем первый файл для получения параметров
        with wave.open(audio_files[0], 'rb') as first_wav:
            channels = first_wav.getnchannels()
            sample_width = first_wav.getsampwidth()
            frame_rate = first_wav.getframerate()
        
        # Собираем все аудиоданные
        all_audio_data = []
        for audio_file in audio_files:
            with wave.open(audio_file, 'rb') as wav_file:
                # Проверяем совместимость параметров
                if (wav_file.getnchannels() != channels or 
                    wav_file.getsampwidth() != sample_width or 
                    wav_file.getframerate() != frame_rate):
                    print(f"Пропускаем файл {audio_file} - несовместимые параметры")
                    continue
                
                audio_data = wav_file.readframes(wav_file.getnframes())
                all_audio_data.append(audio_data)
        
        if not all_audio_data:
            print("Нет совместимых аудиофайлов для склеивания")
            return False
        
        # Записываем склеенный файл
        with wave.open(output_path, 'wb') as output_wav:
            output_wav.setnchannels(channels)
            output_wav.setsampwidth(sample_width)
            output_wav.setframerate(frame_rate)
            
            for audio_data in all_audio_data:
                output_wav.writeframes(audio_data)
        
        print(f"Склеен аудиофайл: {output_path}")
        return True
        
    except Exception as e:
        print(f"Ошибка при склеивании аудиофайлов: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("Создание тестовых аудиофайлов...")
    
    # Создаем тестовые файлы
    test_files = []
    for i in range(3):
        filename = f"test_audio_{i+1}.wav"
        create_test_wav_file(filename, duration_seconds=0.5)
        test_files.append(filename)
        print(f"Создан файл: {filename}")
    
    # Склеиваем файлы
    print("\nСклеивание аудиофайлов...")
    output_file = "concatenated_test.wav"
    success = concatenate_audio_files(test_files, output_file)
    
    if success:
        print(f"Тест успешен! Создан файл: {output_file}")
        
        # Проверяем длительность результирующего файла
        with wave.open(output_file, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / rate
            print(f"Длительность склеенного файла: {duration:.2f} секунд")
    else:
        print("Тест не прошел!")
    
    # Удаляем тестовые файлы
    print("\nУдаление тестовых файлов...")
    for filename in test_files + [output_file]:
        try:
            Path(filename).unlink()
            print(f"Удален файл: {filename}")
        except:
            pass


if __name__ == "__main__":
    main()
