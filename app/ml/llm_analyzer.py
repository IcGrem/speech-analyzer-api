import httpx
import time
import os
import json

from datetime import datetime
from app.ml.requests_db import DBConnection
from openai import OpenAI, RateLimitError
from json.decoder import JSONDecodeError
from typing import List

from app.core.config import settings
from app.ml import prompts
from app.ml.logger import logger
from app.ml.regex import *

class LLMAnalyzer:

    def __init__(self):
        self.model_type = settings.OPENAI_MODEL_TYPE
        # transport = httpx.Proxy(settings.PROXY_URL)
        http_client = httpx.Client(proxies=settings.PROXY_URL,
            timeout=60.0,            
            follow_redirects=True,
            )        
        if not settings.USE_PROXY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY,
                                 base_url=settings.OPENAI_BASE_URL)
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY,
                                 base_url=settings.OPENAI_BASE_URL,
                                 http_client=http_client)

        self.context = ""
        self.split_dialogues = ""
        self.identified_dialogues = list()
        self.prompt = None


    def request_model(self,
                      context: str,
                      prompt: str=prompts.PROMPT_TO_EXTRACT_DIALOGS,
                      get_scores: bool=False) -> tuple[int, str]:
        """
        Метод отправки запроса

        :param prompt: промт для генерации запроса
        :param context: текст контекста
        :param get_scores: запрос на получение оценок или разбиение на диалоги
        :return: возвращает ответ от модели в виде текста, либо код ошибки, если при запросе что-то случилось
        """

        self.prompt = prompt + context

        if get_scores:
            system_prompt = prompts.PROMPT_SYSTEM
        else:
            system_prompt = ''

        result = ""

        while True:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_type,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": self.prompt
                        },
                    ]
                )

                result = completion.choices[0].message.content
                return 200, result

            except JSONDecodeError as e:
                logger.info(
                    f"Ошибка (JSONDecodeError) при обработке ответа запроса: {e}"
                )
            except RateLimitError as e:
                logger.info(
                    f"OpenAI Превышен лимит TPM: {e}"
                )
                message = e.response.json()['error']['message']
                if re.findall(r"Request too large for gpt-4o", message, re.DOTALL):
                    return 429, result
                time_sleep = int(re.findall(r"Please try again in (\d+)", message, re.DOTALL)[0]) + 1
                time.sleep(time_sleep)


    @staticmethod
    def get_transcriptions_names(folder_w_dialogues: str):
        """
        Статический метод для извлечения всех транскрибтов для блоков, которые относятся к конкретной дневной аудио.

        :param folder_w_dialogues: папка с блоками для дневной аудио
        :return:
        """


        chunks_names = os.listdir(folder_w_dialogues)
        transcription_names = [chunk_name for chunk_name in chunks_names if chunk_name.endswith('_transcription.txt')]
        transcription_names = sorted(transcription_names, key=lambda x: int(re.search(r'chunk_(\d+)_', x).group(1)))
        logger.info(
            f"Дневная запись {folder_w_dialogues}"
        )
        logger.info(
            f"Список транскрибций {transcription_names}"
        )

        return transcription_names

    def filter_dialogues(self) -> List:

        """
        Метод для фильтрации и селекции диалогов с помощью регулярных выражений
        Менеджер и клиент
        Разговор коллег с клиентом
        Разговор коллег
        Неизвестно

        :return: возвращает список диалогов определенного типа
        """

        dialogues_list = [

            {"type": dtype, "text": match.strip()}

            for regex, dtype in [
            (PATTERN_MANAGERS_CLIENT, "m2c"),
            (PATTERN_MANAGERS_UNKNOWN, "m2m"),
            ]
            for match in regex.findall(self.split_dialogues)
        ]

        return dialogues_list

    def get_dialogues_by_type(self, folder_w_dialogues: str, chunk_name: str):

        """
        Метод для получения диалогов исключительно типа "Менеджер и клиент" и "Разговор коллег с клиентом"
        и их сохранения
        :param folder_w_dialogues: папка с блоками для дневной аудио
        :param chunk_name: имя чанка/блока аудио текущего
        :return:
        """

        self.identified_dialogues = self.filter_dialogues()
        path_save_identified_dialogues = os.path.join(folder_w_dialogues, f'{chunk_name}_identified_dialogues.txt')
        if self.identified_dialogues:

            for dialog in self.identified_dialogues:

                logger.info(f"Найден диалог типа {dialog.get('type')}")
                logger.info(dialog)
                dialog['chunk_name'] = chunk_name

            with open(path_save_identified_dialogues, "w", encoding="utf-8") as f:
                json.dump(self.identified_dialogues, f, ensure_ascii=False, indent=4)

        else:
            logger.info(
                f"Диалоги не были найдены в {chunk_name}!"
            )
        return self.identified_dialogues


    def extract_dialogues(self, current_folder: str, employee, row_full_audio):

        """
        Метод для извлечения диалогов из каждого отдельного блока аудио

        :param current_folder: путь до текущего дневного аудио
        :param employee: объект Сотрудника
        :param row_full_audio: объект full_audio
        :return:
        """
        db_connection = DBConnection()
        METRIC_NAMES = {
            "Приветствие и прощание": "greeting_farewell_score",
            "Полнота ответа": "completeness_score",
            "Тон общения": "tone_score",
            "Открытость и готовность помочь": "openness_helpfulness_score",
            "Умение слушать": "listening_score",
            "Эмпатия": "empathy_score",
            "Грамотная речь": "speech_quality_score",
            "Время ответа": "response_time_score",
            "Итоговая оценка": "overall_score"
        }

        # try:

        folder_w_dialogues: str = os.path.join(current_folder, settings.FOLDER_W_DIALOGUES)
        transcription_names = self.get_transcriptions_names(folder_w_dialogues)

        for transcription_name in transcription_names:

            logger.info(
                f"Запуск анализа транскрибации {transcription_name} и поиска диалогов в ней определенного типа"
            )

            path_transcription = os.path.join(folder_w_dialogues, transcription_name)
            chunk_name, _ = transcription_name.split('_transcription')
            path_result = os.path.join(folder_w_dialogues, f'{chunk_name}_llm.txt')

            if os.path.exists(path_transcription):

                # проверяем пустой транскрипт, чтобы не отправлять пустые запросы
                if os.stat(path_transcription).st_size == 0:
                    logger.info(
                        f'Файл с транскрипцией {path_transcription} пуст!'
                    )
                    continue

                if not os.path.exists(path_result):

                    with open(path_transcription, "r", encoding="utf-8-sig") as f:
                        context = f.read()

                    # проверяем длину текста, если она небольшая, то смысл отправлять на анализ модели нет
                    if len(context) < settings.MIN_CONTENT_LENGTH:
                        logger.info(
                            f'Файл {path_transcription} слишком короткий ({len(context)} символов). Пропускаем.'
                        )
                        continue

                    status, result = self.request_model(context=context)
                    self.split_dialogues = result

                    if status == 429:
                        logger.info(
                            f"Слишком длинный текст: {self.context}"
                        )
                        continue

                    # cохраняем файл с разбитыми диалогами
                    with open(path_result, "w", encoding="utf-8-sig") as f:
                        f.write(self.split_dialogues)

                    # выделяем диалоги определенных типов
                    _ = self.get_dialogues_by_type(folder_w_dialogues, chunk_name)
                    status_get_scores = self.get_scores(folder_w_dialogues)

                    if status_get_scores == 500:
                        logger.error(
                            f'Ошибка при попытке получить оценки для {path_transcription}!'
                        )
                        continue

                    # TODO
                    # список словарей с диалогами для сохранения с диалогами
                    # self.identified_dialogues
                    # TODO
                    # тут записываем в базу
                    # создание записи диалога, зная сотрудника и дневную запись
                    
                    for dialog in self.identified_dialogues:
                        logger.info(f'dialog - {dialog}')
                        record_start_date = datetime.fromisoformat(dialog['chunk_name'].split('_')[3])
                        metrics = {METRIC_NAMES[key]: value for key, value in dialog['scores'].items()}
                        data_for_save_to_db = {
                            "employee_id": employee.id,
                            "conversation_type": dialog['type'],
                            "conversation": dialog['text'],
                            "filename": row_full_audio.full_audio_filename,
                            "recording_start_date": record_start_date,
                            "recording_end_date": record_start_date,
                            "audio_data_for_analysis_id": row_full_audio.id,
                            **metrics
                        }
                        db_connection.create_dialog(data_for_save_to_db)

                else:
                    logger.info(
                        f'Анализ LLM для {path_transcription} уже проводился!'
                    )
            else:
                logger.info(
                    f'Транскрибта для {path_transcription} не существует!'
                )

        return

        # except Exception as e:
        #     logger.error(
        #         f'Ошибка при анализе транскрибций {e}'
        #     )
        #     return 500

    @staticmethod
    def parse_scores(scores_dialog: str) -> dict[str, float]:

        """
        Парсит оценки из текста модели в словарь.
        :param scores_dialog: текст с оценками диалога
        :return: Возвращает {название критерия: оценка}.
        """
        pattern = r"### (.*?): ([0-9]+(?:[.,][0-9]+)?)/5"
        scores = {}
        for match in re.finditer(pattern, scores_dialog):
            key = match.group(1).strip()
            value = float(match.group(2).replace(",", "."))  # поддержка запятой и точки
            scores[key] = value
        return scores


    def get_scores(self, folder_w_dialogues: str):

        """
        Метод для получения оценок от LLM, анализа качества общения персонала с клиентом

        :param folder_w_dialogues: папка с блоками аудио
        :return:
        """

        try:
            for dialog in self.identified_dialogues:
                chunk_name = dialog['chunk_name']
                if dialog["type"] == "m2c":
                    context = dialog["text"]
                    status, scores_dialog = self.request_model(context=context,
                                                               prompt=prompts.PROMPT_TO_SCORE_DIALOGS,
                                                               get_scores=True)

                    if status == 429:
                        logger.info(
                            f"Слишком длинный текст: {self.context}"
                        )
                        continue

                    dialog["scores_dialog"] = scores_dialog
                    logger.info(f"Диалог:\n{dialog['text']}")
                    logger.info(f"Оценка диалога:\n{dialog['scores_dialog']}")
                    dialog["scores"] = self.parse_scores(scores_dialog)
                    logger.info(f"Оценки диалога:\n{dialog['scores']}")
                else:
                    dialog["scores_dialog"] = []
                    dialog["scores"] = []

            # chunk_name будет у всех одинаковый
            path_save_scores_dialogues = os.path.join(folder_w_dialogues, f"{chunk_name}_scores_dialogues.txt")

            with open(path_save_scores_dialogues, "w", encoding="utf-8") as f:
                json.dump(self.identified_dialogues, f, ensure_ascii=False, indent=4)

            return 200

        except Exception as e:
            logger.error(
                f'Ошибка при попытке выставления оценки диалогу {e}'
            )
            return 500

