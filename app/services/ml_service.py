import os

from tqdm import tqdm
from datetime import timedelta

from app.ml.audio_analyzer import AudioAnalyzer
from app.ml.requests_db import DBConnection
from app.core.config import settings
from app.models.dialogs import AudioDataForAnalysis
from app.ml.logger import logger

def main_audio_analyzer_function():

    """
    Основная функция для запуска ML-сервиса

    :return:
    """

    # создание общего словаря
    # norm_form_phrase, [origin, name_dict]
    # general_dict_phrases = db_connection.create_general_dict_phrases()
    # assert len(general_dict_phrases) == 864

    # Инициализация основных подключений
    db_connection = DBConnection()
    audio_chunker = AudioAnalyzer()

    all_rows_full_audio = db_connection.get_all_rows(AudioDataForAnalysis)
    for row_full_audio in all_rows_full_audio:

        logger.info(f"Обработка аудио {row_full_audio.full_audio_filename}")
        # обновления поля в модели
        # db_connection.update_row(model=AudioDataForAnalysis,
        #                          filter_field='id',
        #                          filter_value=row_full_audio.id,
        #                          is_analyzed=True)

        # employee_id = row_full_audio.employee_id
        # получение сотрудника по id
        # employee = db_connection.get_by_attribute(Employee, 'employee_id', employee_id)
        # создание записи диалога, зная сотрудника и дневную запись
        # db_connection.create_dialog(employee, row_full_audio)


        main_path_audio = settings.PATH_W_FULL_AUDIO
        audio_name = row_full_audio.full_audio_filename
        audio_folder, _ = audio_name.split('_full')

        os.makedirs(os.path.join(main_path_audio, audio_folder, 'dialogues'), exist_ok=True)
        path_full_audio = os.path.join(main_path_audio, audio_folder, audio_name)

        # STAGE 1. Разделение дневных аудио на блоки (потенциальные диалоги)
        logger.info(f"STAGE 1: Разделение дневного аудио {row_full_audio.full_audio_filename} на блоки")
        status, durations_pause, chunks =  audio_chunker.vad_split_audio_into_dialogues(
            path_audio=path_full_audio,
            min_duration_dialogue=settings.MIN_DURATION_DIALOGUE,
            min_duration_pause=settings.MIN_DURATION_PAUSE
        )

        if status == 500:
            logger.error(f"STAGE 1: Разделение дневного аудио "
                         f"{row_full_audio.full_audio_filename} "
                         f"на блоки не завершено!")
            continue

        # Сохраняем чанки/блоки как отдельные файлы
        for i, (chunk, start_dialogue, end_dialogue) in tqdm(enumerate(chunks, 1)):
            start_dialogue = timedelta(seconds=round(start_dialogue))
            end_dialogue = timedelta(seconds=round(end_dialogue))
            name_chunk = f"chunk_{i}_{audio_folder}_{start_dialogue}_{end_dialogue}.wav".replace(':', '_')
            chunk.export(os.path.join(main_path_audio, audio_folder, 'dialogues', name_chunk), format="wav")
            logger.info(f"Сегмент {i} сохранён как {name_chunk}")

        del chunks, durations_pause

        logger.info(f"STAGE 1: Разделение дневного аудио "
                    f"{row_full_audio.full_audio_filename} "
                    f"на блоки успешно завершена!")

        # STAGE 2. Выделение текста из аудио блоков
        logger.info(f"STAGE 2: Выделение текста из аудио блоков")
        _, model_name = settings.TRANSCRIPTION_MODEL.split('/')
        logger.info(f"Model name: {model_name}")

    return


if __name__ == '__main__':
    main_audio_analyzer_function()