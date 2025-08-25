import random
from typing import Optional
import uuid

from datetime import datetime
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models.dialogs import Dialog, ConversationType, Phrase, Dictionary
from app.ml.utils import get_url_db
from app.ml.logger import logger

class DBConnection:

    def __init__(self):
        sqlalchemy_database_url = get_url_db()
        engine = create_engine(sqlalchemy_database_url)

        self.session_local = sessionmaker(expire_on_commit=False,
                                         autocommit=False,
                                         autoflush=False,
                                         bind=engine)

    def get_all_rows(self, models):

        """
        Метод на получение всех данных из конкретной таблицы
        """

        session = self.session_local()
        all_rows = session.query(models).all()
        session.close()

        return all_rows

    def get_filtered_rows(
        self,
        session: Session,
        models,
        order_by: Optional[str] = None,
        **filters,
        ):

        """
        Метод на получение отфильтрованных данных из конкретной таблицы
        """
        query = select(models)
        logger.info(f'Фильтры - {filters}')
        
        # Применяем фильтры
        for filter_key, value in filters.items():
            if value is None:
                continue
                
            # Разделяем ключ на поле и оператор
            parts = filter_key.split('__')
            field_name = parts[0]
            operator = 'eq' if len(parts) == 1 else parts[1]

            if not hasattr(models, field_name):
                logger.warning(f"Поле {field_name} не найдено в модели {models}")
                continue

            field = getattr(models, field_name)
            
            # Выбираем оператор
            if operator == 'gte':
                query = query.where(field >= value)
                logger.debug(f"Добавлено условие: {field} >= {value}")
            elif operator == 'lte':
                query = query.where(field <= value)
                logger.debug(f"Добавлено условие: {field} <= {value}")
            elif operator == 'eq':
                query = query.where(field == value)
                logger.debug(f"Добавлено условие: {field} == {value}")
            else:
                raise ValueError(f"Неизвестный оператор: {operator}")

        # Применяем сортировку
        if order_by:
            if order_by.startswith('-'):
                field_name = order_by[1:]
                if hasattr(models, field_name):
                    query = query.order_by(getattr(models, field_name).desc())
                    logger.debug(f"Добавлена сортировка по {field_name} DESC")
            else:
                if hasattr(models, order_by):
                    query = query.order_by(getattr(models, order_by))
                    logger.debug(f"Добавлена сортировка по {order_by} ASC")
        
        # Логируем итоговый SQL-запрос для отладки
        try:
            logger.debug(f"Итоговый SQL: {query.compile(bind=session.get_bind())}")
        except:
            logger.debug("Не удалось скомпилировать SQL для логирования")
        
        result = session.execute(query)
        return result.scalars().all()

    def get_by_date_range(
        self,
        models,
        start_date: datetime, 
        end_date: datetime
    ):
        """Получить записи в диапазоне дат"""
        logger.info(f'Дата начала {start_date} Дата конца {end_date}')
        
        # Убедимся, что даты имеют правильный формат
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            logger.error("Даты должны быть объектами datetime")
            return []
        
        session = self.session_local()
        try:
            return self.get_filtered_rows(
                session,
                models,
                order_by="-creation_date",
                date__gte=start_date,
                date__lte=end_date,
            )
        finally:
            session.close()

    def get_by_attribute(self, model, field_name: str, value):
        """
        Метод для получения одной записи в рамках одной таблицы
        """
        session = self.session_local()
        field: InstrumentedAttribute = getattr(model, field_name)
        row = session.query(model).filter(field == value).first()
        session.close()
        return row

    def update_row(self, model, filter_field: str, filter_value, **updates):

        """
        Метод для обновления записи

        :param model: Модель
        :param filter_field: Имя поля для фильтрации
        :param filter_value: значение для поля field_name
        """

        session = self.session_local()
        field: InstrumentedAttribute = getattr(model, filter_field)
        row = session.query(model).filter(field == filter_value).first()
        if row:
            for update_field, value in updates.items():
                setattr(row, update_field, value)
            session.commit()
            session.close()
            return True
        return False

    def create_fake_dialog(self, employee, audio_data_for_analysis):

        """
        Метод для создания записи с диалогом

        :param employee: запись из таблицы сотрудников
        :param audio_data_for_analysis: запись из таблицы с дневными аудио
        :return:
        """

        # M2M = "m2m"  # manager to manager
        # M2C = "m2c"  # manager to customer
        # UNKNOWN = "unknown"

        def generate_dialog_metrics() -> dict:

            METRIC_NAMES = [
                "greeting_farewell_score",
                "completeness_score",
                "tone_score",
                "openness_helpfulness_score",
                "listening_score",
                "empathy_score",
                "speech_quality_score",
                "response_time_score",
                "overall_score",
            ]

            out = dict()
            for metric in METRIC_NAMES:
                out[metric] = round(random.uniform(1, 5), 2)

            return out

        def generate_dialog(employee_id: uuid.UUID,
                            audio_data_for_analysis_id: uuid.UUID) -> dict:

            """Генерирует данные диалога"""
            start_time = datetime.now()
            end_time = start_time

            metrics = generate_dialog_metrics()

            return {
                "employee_id": employee_id,
                "conversation_type": random.choice(list(ConversationType)),
                "conversation": "Добрый день, пока",
                "filename": f"recording_{start_time.strftime('%Y%m%d_%H%M%S')}_{employee_id}.wav",
                "recording_start_date": start_time,
                "recording_end_date": end_time,
                "audio_data_for_analysis_id": audio_data_for_analysis_id,
                **metrics
            }

        dialog_data = generate_dialog(employee.id, audio_data_for_analysis.id)
        dialog = Dialog(**dialog_data)
        session = self.session_local()
        session.add(dialog)
        session.commit()
        session.close()

    def create_dialog(self, dialog_data):

        """
        Метод для создания записи с диалогом

        :param employee: запись из таблицы сотрудников
        :param audio_data_for_analysis: запись из таблицы с дневными аудио
        :return:
        """
  
        dialog = Dialog(**dialog_data)
        session = self.session_local()
        session.add(dialog)
        session.commit()
        session.close()

    def create_general_dict_phrases(self):
        """
        Метод для получения всех словарей, для поиска тригерных фраз
        """

        general_dict_phrases = dict()
        all_rows_phrases = self.get_all_rows(Phrase)
        for row_phrase in all_rows_phrases:
            dictionary_id = row_phrase.dictionary_id
            dictionary = self.get_by_attribute(Dictionary, 'id', dictionary_id)
            general_dict_phrases[row_phrase.normal_form] = [row_phrase.phrase, dictionary.description]

        return general_dict_phrases