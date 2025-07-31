from fastapi import HTTPException, status


class UserNotFoundError(HTTPException):
    """Пользователь не найден"""
    def __init__(self, detail: str = "Пользователь не найден"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class InvalidCredentialsError(HTTPException):
    """Неверные учетные данные"""
    def __init__(self, detail: str = "Неверные учетные данные"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class UserAlreadyExistsError(HTTPException):
    """Пользователь уже существует"""
    def __init__(self, detail: str = "Пользователь уже существует"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class SpeechAnalyzerException(HTTPException):
    """Базовое исключение для приложения"""
    pass


class AudioProcessingError(SpeechAnalyzerException):
    """Ошибка обработки аудио"""
    
    def __init__(self, detail: str = "Ошибка обработки аудио файла"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class FileValidationError(SpeechAnalyzerException):
    """Ошибка валидации файла"""
    
    def __init__(self, detail: str = "Некорректный формат файла"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class AnalysisNotFoundError(SpeechAnalyzerException):
    """Анализ не найден"""
    
    def __init__(self, detail: str = "Анализ не найден"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class DatabaseError(SpeechAnalyzerException):
    """Ошибка базы данных"""
    
    def __init__(self, detail: str = "Ошибка базы данных"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class DialogNotFoundError(SpeechAnalyzerException):
    """Диалог не найден"""
    
    def __init__(self, detail: str = "Диалог не найден"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )
