import argparse
import os

from tqdm import tqdm
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.dialogs import AudioDataForAnalysis
from app.models.users import Employee

from app.ml.audio_analyzer import AudioAnalyzer
from app.ml.requests_db import DBConnection
from app.ml.speech2text_analyzer import TextExtractor
from app.ml.llm_analyzer import LLMAnalyzer
from app.ml.logger import logger


def main_audio_analyzer_function(start_date, end_date):

    """
    Основная функция для запуска ML-сервиса

    :param start_date: Начальная дата диапазона
    :param end_date: Конечная дата диапазона
    :return:
    """

    # создание общего словаря
    # norm_form_phrase, [origin, name_dict]
    # general_dict_phrases = db_connection.create_general_dict_phrases()
    # assert len(general_dict_phrases) == 864

    # Инициализация основных подключений
    main_folder_audio: str = settings.FOLDER_W_FULL_AUDIO
    db_connection = DBConnection()
    audio_chunker = AudioAnalyzer()
    transcriptor = TextExtractor()
    llm_analyzer = LLMAnalyzer()

    all_rows_full_audio = db_connection.get_by_date_range(AudioDataForAnalysis, start_date=start_date, end_date=end_date)
    for row_full_audio in all_rows_full_audio:

        # обновления поля в модели
        # db_connection.update_row(model=AudioDataForAnalysis,
        #                          filter_field='id',
        #                          filter_value=row_full_audio.id,
        #                          is_analyzed=True)


        audio_name = row_full_audio.full_audio_filename
        # audio_name = '58393_2025-07-15_full.wav'
        logger.info(f"Обработка аудио {audio_name}")
        audio_folder, _ = audio_name.split('_full')
        current_folder: str = os.path.join(main_folder_audio, audio_folder)
        folder_w_dialogues: str =  os.path.join(current_folder, settings.FOLDER_W_DIALOGUES)

        os.makedirs(folder_w_dialogues, exist_ok=True)
        path_full_audio = os.path.join(current_folder, audio_name)

        # STAGE 1. Разделение дневных аудио на блоки (потенциальные диалоги)
        logger.info(f"STAGE 1: Разделение дневного аудио {audio_name} на блоки")
        status_vad, durations_pause, chunks =  audio_chunker.vad_split_audio_into_dialogues(
            path_audio=path_full_audio,
            min_duration_dialogue=settings.MIN_DURATION_DIALOGUE,
            min_duration_pause=settings.MIN_DURATION_PAUSE
        )

        if status_vad == 500:
            logger.error(f"STAGE 1: Разделение дневного аудио {audio_name} на блоки не завершено!")
            continue

        # Сохраняем чанки/блоки как отдельные файлы
        for i, (chunk, start_dialogue, end_dialogue) in tqdm(enumerate(chunks, 1)):
            start_dialogue = timedelta(seconds=round(start_dialogue))
            end_dialogue = timedelta(seconds=round(end_dialogue))
            name_chunk = f"chunk_{i}_{audio_folder}_{start_dialogue}_{end_dialogue}.wav".replace(':', '_')
            chunk.export(os.path.join(folder_w_dialogues, name_chunk), format="wav")
            logger.info(f"Сегмент {i} сохранён как {name_chunk}")

        del chunks, durations_pause

        logger.info(f"STAGE 1: Разделение дневного аудио {audio_name} на блоки успешно завершена!")

        # STAGE 2. Выделение текста из аудио блоков
        logger.info(f"STAGE 2: Диаризация и транскрибация для аудио блоков {folder_w_dialogues}")
        # transcriptor.get_transcription(current_folder)
        status_diarization_transcription = transcriptor.diarization_transcription_analysis(current_folder,
                                                                                           settings.CLEANING_DIARIZATION_FOLDER)

        if status_diarization_transcription == 500:
            logger.error(f"STAGE 2: Диаризация и транскрибация для аудио блоков {folder_w_dialogues} не завершена!")
            continue

        logger.info(f"STAGE 2: Диаризация и транскрибация для аудио блоков {folder_w_dialogues} успешна завершена!")

        # STAGE 3. Разделение текста на диалоги с использованием LLM
        logger.info(
            f"STAGE 3: Разделение блоков на диалоги, определение их типа с использованием LLM {folder_w_dialogues}!"
        )

        # TODO передать пользователя и аудизапись
        employee_id = row_full_audio.employee_id
        # получение сотрудника по id
        employee = db_connection.get_by_attribute(Employee, 'employee_id', employee_id)
        # создание записи диалога, зная сотрудника и дневную запись
        # db_connection.create_dialog(employee, row_full_audio)
        status_extract_dialogues = llm_analyzer.extract_dialogues(current_folder, employee, row_full_audio)

        if status_extract_dialogues == 500:
            logger.error(
                f"STAGE 3: Разделение блоков на диалоги, определение их типа "
                f"с использованием LLM {folder_w_dialogues} не завершена!"
            )
            continue

        logger.info(
            f"STAGE 3: Разделение блоков на диалоги, определение их типа "
            f"с использованием LLM {folder_w_dialogues} успешно завершено!"
        )

        # STAGE 4. Получение оценок по диалогам
        # logger.info(
        #     f"STAGE 4: Получение оценок с использованием LLM {folder_w_dialogues}!"
        # )
        #
        # status_get_scores = llm_analyzer.get_scores(current_folder)
        #
        # if status_get_scores == 500:
        #     logger.info(
        #         f"STAGE 4: Разделение блоков на диалоги, определение их типа "
        #         f"с использованием LLM {folder_w_dialogues} не завершена!"
        #     )
        #     continue
        #
        # logger.info(
        #     f"STAGE 4: Получение оценок с использованием LLM {folder_w_dialogues} успешно завершено!"
        # )




    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Анализ аудиоданных за указанный период')
    parser.add_argument(
        '--start_date', 
        type=str, 
        required=True, 
        help='Начальная дата в формате YYYY-MM-DD'
    )
    parser.add_argument(
        '--end_date', 
        type=str, 
        required=False, 
        help='Конечная дата в формате YYYY-MM-DD'
    )
    
    args = parser.parse_args()
    
    # Преобразование строк в объекты datetime
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    main_audio_analyzer_function(start_date, end_date)
