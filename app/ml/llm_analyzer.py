import time
import os
import json

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

        if not settings.USE_PROXY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY,
                                 base_url=settings.OPENAI_BASE_URL)
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY,
                                 base_url=settings.OPENAI_BASE_URL,
                                 http_client=settings.PROXY_URL)

        self.context = ""
        self.split_dialogues = ""
        self.identified_dialogues = list()
        self.prompt = None


    def create_prompt(self) -> str:

        """
        Метод для генерации промта для модели

        :return: возвращает промт
        """

        self.prompt = prompts.PROMPT_TO_EXTRACT_DIALOGS + self.context

        return self.prompt


    def request_model(self) -> int:
        """
        Метод отправки запроса

        :return: возвращает ответ от модели в виде текста, либо код ошибки, если при запросе что-то случилось
        """

        prompt = self.create_prompt()
        self.split_dialogues = ""

        while True:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_type,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        },
                    ]
                )

                self.split_dialogues = completion.choices[0].message.content
                return 200

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
                    return 429
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

            with open(path_save_identified_dialogues, "w", encoding="utf-8") as f:
                json.dump(self.identified_dialogues, f, ensure_ascii=False, indent=4)

            for dialog in self.identified_dialogues:

                logger.info(f"Найден диалог типа {dialog.get('type')}")
                logger.info(dialog)

        else:
            logger.info(
                f"Диалоги не были найдены в {chunk_name}!"
            )
        return self.identified_dialogues


    def extract_dialogues(self, current_folder: str):

        """
        Метод для извлечения диалогов из каждого отдельного блока аудио

        :param current_folder: путь до текущего дневного аудио
        :return:
        """

        try:

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
                            self.context = f.read()

                        # проверяем длину текста, если она небольшая, то смысл отправлять на анализ модели нет
                        if len(self.context) < settings.MIN_CONTENT_LENGTH:
                            logger.info(
                                f'Файл {path_transcription} слишком короткий ({len(self.context)} символов). Пропускаем.'
                            )
                            continue

                        result = self.request_model()

                        if result == 429:
                            logger.info(
                                "Слишком длинный текст!"
                            )
                            continue

                        # cохраняем файл с разбитыми диалогами
                        with open(path_result, "w", encoding="utf-8-sig") as f:
                            f.write(self.split_dialogues)

                        # выделяем диалоги определенных типов
                        identified_dialogues = self.get_dialogues_by_type(folder_w_dialogues, chunk_name)

                    else:
                        logger.info(
                            f'Анализ LLM для {path_transcription} уже проводился!'
                        )
                else:
                    logger.info(
                        f'Транскрибта для {path_transcription} не существует!'
                    )
        except Exception as e:
            logger.error(
                f'Ошибка при анализе транскрибций {e}'
            )
            return 501
