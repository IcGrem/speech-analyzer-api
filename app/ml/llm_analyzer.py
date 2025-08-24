import re
import time
import os

from openai import OpenAI, RateLimitError
from json.decoder import JSONDecodeError

from app.core.config import settings
from app.ml import prompts
from app.ml.logger import logger

class LLMAnalyzer:

    def __init__(self):
        self.model_type = settings.OPENAI_MODEL_TYPE

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY,
                             base_url=settings.OPENAI_BASE_URL)

        self.context = None
        self.prompt = None


    def create_prompt(self) -> str:

        """
        Метод для генерации промта для модели

        :return: возвращает промт
        """

        self.prompt = self.context

        return self.prompt


    def request_model(self) -> str|int:
        """
        Метод отправки запроса

        :return: возвращает ответ от модели в виде текста, либо код ошибки, если при запросе что-то случилось
        """

        prompt = prompts.PROMPT_TO_EXTRACT_DIALOGS + self.create_prompt()

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

                return completion.choices[0].message.content

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

                path_transcription = os.path.join(folder_w_dialogues, f'{transcription_name}')
                name_txt_llm, _ = transcription_name.split('_transcription')
                path_result = os.path.join(folder_w_dialogues, f'{name_txt_llm}_llm.txt')

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

                        with open(path_result, "w", encoding="utf-8-sig") as f:
                            f.write(result)

                    else:
                        logger.info(
                            f'Анализ LLM для {path_transcription} уже проводился!'
                        )
                else:
                    logger.info(
                        f'Транскрибта для {path_transcription} не существует!'
                    )
        except:
            logger.error(
                'Ошибка при анализе транскрибций'
            )
            return 501
