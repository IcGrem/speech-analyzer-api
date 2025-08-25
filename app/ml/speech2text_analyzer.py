import torch
import os
import re
import shutil

from pyannote.audio import Pipeline
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from pydub import AudioSegment

from app.core.config import settings
from app.ml.logger import logger
from app.ml.utils import save_txt_file

class TextExtractor:

    """
    Класс для решения задачи speech2text
    """

    def __init__(self):

        self.name_transcription_model = settings.TRANSCRIPTION_MODEL
        self.name_diarization_model = settings.DIARIZATION_MODEL

        self.path_to_transcription = None
        self.chunk_text_transcription = None

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        self.transcription_model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.name_transcription_model,
            use_auth_token=settings.HF_TOKEN,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=False,
            use_safetensors=True,
            attn_implementation="sdpa"
            ).to(
                device
            )

        processor = AutoProcessor.from_pretrained(self.name_transcription_model)

        # Если нужно на ходу обрабатывать длинные аудиофайлы
        # chunk_length_s=30
        self.transcription_pipeline = pipeline("automatic-speech-recognition",
                                               model=self.transcription_model,
                                               tokenizer=processor.tokenizer,
                                               feature_extractor=processor.feature_extractor,
                                               torch_dtype=torch_dtype,
                                               device=device,
                                               chunk_length_s=30)


        self.generate_kwargs = {"max_new_tokens": 448,
                                "num_beams": 1,
                                "condition_on_prev_tokens": False,
                                "compression_ratio_threshold": 1.35,
                                # zlib compression ratio threshold (in token space)
                                "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
                                "logprob_threshold": -1.0,
                                "no_speech_threshold": 0.6,
                                "return_timestamps": True, }

        self.generate_kwargs = {"language": "ru"}

        self.diarization_pipeline = Pipeline.from_pretrained(
            self.name_diarization_model,
            use_auth_token=settings.HF_TOKEN
            ).to(
            torch.device("cuda")
            )

        return

    def diarization_analysis(self, path_audio) -> list:

        """
        Метод для диаризации спикеров в рамках аудио блока

        :param path_audio: путь до аудио файла блока
        :return: возвращает список реплик
        """

        # можно указать количество спикеров num_speakers=2
        diarization_result = self.diarization_pipeline(path_audio)

        replicas_list = []
        current_speaker = None
        # склеиваем реплики
        for turn, _, speaker in diarization_result.itertracks(yield_label=True):

            if current_speaker is None:
                current_speaker = speaker
                # в миллисекундах
                start = int(turn.start * 1000)
                end = int(turn.end * 1000)
            elif current_speaker == speaker:
                end = int(turn.end * 1000)
            elif current_speaker != speaker:
                # сохраняем спикера реплики всю
                replicas_list.append([current_speaker, start, end])
                # обновляем данные для нового спикера
                current_speaker = speaker
                start = int(turn.start * 1000)
                end = int(turn.end * 1000)

        return replicas_list

    def extract_and_save_text(self,
                              path_audio: str,
                              replicas_list: list,
                              folder_w_diarization: str,
                              chunk_number: str):

        """
        Метод на обработку аудио и выделения текста

        :param path_audio: путь до исходного аудио блока
        :param replicas_list: список реплик
        :param folder_w_diarization: папка для сохранения фрагментов реплик
        :param chunk_number: str
        :return:
        """

        def is_empty_text(text):

            """
            Функция проверки, есть ли полезная информция в полученном тексте
            """

            return bool(re.fullmatch(r'[\s\W_]*', text))

        # загружаем исходное аудио блока
        audio = AudioSegment.from_file(path_audio)
        # speakers_list = set(replica[0] for replica in replicas_list)
        # speakers_audio = dict(zip(speakers_list, len(speakers_list) * [AudioSegment.empty()]))

        for [speaker, start, end] in replicas_list:

            # print(f"{speaker}: start={start:.1f}ms stop={end:.1f}ms ")

            chunk_length = end - start
            # фильтруем короткие сегменты менее 0.5 секунды
            if chunk_length > 500:
                # print(folder_audio)
                # Вырезаем сегмент и сохраняем в файл в рамках диаризации
                segment = audio[start:end]
                start_sec = start//1000
                end_sec = end // 1000
                path_speaker_chunk = os.path.join(folder_w_diarization, f"{chunk_number}_{start_sec}_{end_sec}_{speaker}.wav")
                segment = segment.set_frame_rate(settings.FRAME_RATE)
                segment.export(path_speaker_chunk, format="wav")

                # получаем текст в рамках конкретного фрагмента
                text = self.get_chunk_transcription(path_speaker_chunk)

                # добавляем сегмент конкретному диктору, чтобы потом сохранить всю дорожку
                # speakers_audio[speaker] += segment

                # сохраняем только те реплики, в которых удалось распознать текст
                if not (is_empty_text(text)) and not (text in settings.uninformative_phrases):
                    with open(self.path_to_transcription, "a", encoding="utf-8") as text_file:
                        text_file.write(f"{speaker}: {text}\n")

        return


    def diarization_transcription_analysis(self,
                                           current_folder: str,
                                           cleaning=False):

        """
        Метод предназначен для
        1. диаризации спикеров в рамках блоков, которые представляют собой разбитый дневной файл
        2. Разделение на реплики и транскрибация каждой реплики

        :param current_folder: папка, где лежит все для конкретной дневной записи
        :param cleaning: флаг, определяющий чистить ли папку с диаризацией, после выполнения всех операций или нет
        :return: статус выполнения транксрибации/диризации
        """

        def cleaning_folder(folder, path_transcription=None):

            """
            Функция очистки папок
            """

            # Cleaning path with chunks
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.makedirs(folder)

            if path_transcription and os.path.exists(path_transcription):
                os.remove(path_transcription)

            logger.info(f'Очистка папки {folder} прошла успешно!')
            return

        def get_chunk_number(chunk_name: str) -> str:
            """
            Функция для получения номера чанка

            :param chunk_name: имя следующего вида chunk_1_58393_2025-07-15_0_00_03_0_01_22.wav
            :return: строку chunk_1
            """
            match = re.match(r"chunk_(\d+)", chunk_name)

            chunk_number = ""

            if match:
                chunk_number = f"chunk{match.group(1)}"

            return  chunk_number

        try:

            folder_w_dialogues: str =  os.path.join(current_folder, settings.FOLDER_W_DIALOGUES)
            chunks_names = os.listdir(folder_w_dialogues)
            chunks_names = [chunk_name for chunk_name in chunks_names if chunk_name.endswith('.wav')]
            chunks_names = sorted(chunks_names, key=lambda x: int(re.search(r'chunk_(\d+)_', x).group(1)))
            logger.info(f"Дневная запись {folder_w_dialogues}")
            logger.info(f"Список аудио блоков {chunks_names}")

            # пусть до папки с разделением после диаризации аудиофрагментами
            folder_w_diarization = os.path.join(current_folder, settings.FOLDER_W_DIARIZATION)
            os.makedirs(folder_w_diarization, exist_ok=True)
            for chunk_name in chunks_names:
                # путь до файла с транскрибцией
                chunk_name, _ = chunk_name.split('.')
                chunk_number = get_chunk_number(chunk_name)
                self.path_to_transcription = os.path.join(folder_w_dialogues, f'{chunk_name}_transcription.txt')

                if not os.path.exists(self.path_to_transcription):

                    # создаем пустой файл транскрибции
                    with open(self.path_to_transcription, 'w') as f:
                        pass

                    logger.info(f"Транскрибация и диаризация для {folder_w_dialogues} - {chunk_name} начинается!")

                    path_audio = os.path.join(folder_w_dialogues, f"{chunk_name}.wav")
                    # удаление диаризации с прошлого блока аудио, чтобы они не капились
                    # cleaning_folder(folder_w_diarization)

                    replicas_list = self.diarization_analysis(path_audio)
                    self.extract_and_save_text(path_audio, replicas_list, folder_w_diarization, chunk_number)

                else:
                    logger.info(f"⚠️ Транскрибация и диаризация для {chunk_name} уже выполнялась!")

            if cleaning:
                cleaning_folder(folder_w_diarization)
        except Exception as e:
            logger.error(f'Ошибка при Диаризации/Транскрибации {e}')
            return 500

    def get_chunk_transcription(self, path_speaker_chunk: str):

        """
        Метод для обращения к модели и получения текста из аудио

        :param path_speaker_chunk: путь до ауидо-реплики
        :return: текст
        """

        # path_speaker_chunk = '.\\20250206\\2024-09-24_1_Н\\diarization\\1617_9497_SPEAKER_00.wav'
        self.chunk_text_transcription = self.transcription_pipeline(path_speaker_chunk,
                                                                    generate_kwargs=self.generate_kwargs)

        return self.chunk_text_transcription["text"][1:]

    def get_transcription(self, current_folder):

        """
        Метод для получения транскрибции сразу из всего аудиофайла
        # сохраняет в transcription_original.txt
        """

        file_name = [file for file in os.listdir(current_folder) if file.endswith('.wav')][0]

        path_to_wav = os.path.join(current_folder, file_name)

        transcript = self.transcription_pipeline(path_to_wav,
                                                      batch_size=16,
                                                      generate_kwargs=self.generate_kwargs)

        text = transcript["text"]
        path_transcription = os.path.join(current_folder, 'transcription_original.txt')
        save_txt_file(way_file=path_transcription, text=text)
        return text