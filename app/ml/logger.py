import os

from loguru import logger
from datetime import datetime

from app.core.config import settings

date = datetime.now().date().strftime('%d_%m_%Y')
hour, minute = datetime.now().time().hour, datetime.now().time().minute

logger.add(os.path.join(settings.LOGGER_FOLDER, date, f"main_{hour}_{minute}.log"),
           format= "|| {time:YYYY-MMM-D} || {time: HH:mm} || {time: Z} || - {level} - {message}",
           enqueue=True,
           level='DEBUG',
           rotation='10 MB',
           compression='zip')

