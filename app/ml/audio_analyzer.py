import torch
import asyncio

from pyannote.audio import Pipeline
from pyannote.audio.pipelines import VoiceActivityDetection

from pydub import AudioSegment
from pydub.silence import split_on_silence

from app.core.config import settings
# from app.core.logging import get_logger
# logger = get_logger(__name__)
from app.ml.logger import logger
from app.ml.utils import timeit



class AudioAnalyzer:

    def __init__(self):
        self.logger = logger
        self.vad_model = settings.VAD_MODEL
        pass


    def vad_split_audio_into_dialogues(self,
                                       path_audio,
                                       min_duration_dialogue,
                                       min_duration_pause):
        """
        Делит аудио на чанки по тишине.

        :param audio_path: Путь к аудиофайлу
        :param min_duration_dialogue: минимальная длительность диалога
        :param min_duration_pause: минимальная пауза, чтобы отсечь диалог
        :return: Список объектов AudioSegment, представляющих диалоги
        """

        vad_pipeline = VoiceActivityDetection.from_pretrained(self.vad_model).to(torch.device("cuda"))
        vad_result = vad_pipeline(path_audio)

        audio = AudioSegment.from_file(path_audio)

        audio_dialogues = list()
        durations_pause = []
        segment_previous = None
        start_dialogue = None
        end_dialogue = None
        # перебираем фрагменты речи
        for segment_current in vad_result.get_timeline():
            # если первый сегмент ещё не определили, устанавливаем его, а также старт и конец диалога
            if segment_previous is None:
                start_dialogue = segment_current.start
                end_dialogue = segment_current.end
            # если у нас есть предыдущий отрезок и текущий, то проверяем размер паузы между ними
            else:
                duration_pause = segment_current.start - segment_previous.end
                durations_pause.append(duration_pause)
                # print('===================')
                # print(round(duration_pause, 2))
                # если пауза довольно длинная, значит можно завершать диалог
                if duration_pause >= min_duration_pause:
                    duration_dialogue = end_dialogue - start_dialogue
                    # также проверяем длительность диалога, если она меньше 30 секунд, значит пропускаем
                    if duration_dialogue >= min_duration_dialogue:
                        logger.info('===================')
                        logger.info('Сохраняем чанк')
                        logger.info(round(duration_pause, 2))
                        # определяем новые начала и конец диалога
                        audio_dialogues.append(
                            (audio[int(start_dialogue * 1000):int(end_dialogue * 1000)], start_dialogue, end_dialogue)
                            )
                        start_dialogue = segment_current.start
                        end_dialogue = segment_current.end
                # если пауза небольшая, то увеличиваем длительность диалога
                else:
                    end_dialogue = segment_current.end
            segment_previous = segment_current
        return durations_pause, audio_dialogues