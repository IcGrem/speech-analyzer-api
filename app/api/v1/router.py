from fastapi import APIRouter

from app.api.v1.endpoints import analysis, health, users, dialogs, scheduler, organizations, employees

api_router = APIRouter()

# Подключение эндпоинтов
api_router.include_router(health.router, prefix="/health", tags=["health"])
# api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(dialogs.router, prefix="/dialogs", tags=["dialogs"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])
