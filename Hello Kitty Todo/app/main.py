from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from loguru import logger
import redis
from prometheus_client import make_asgi_app, Counter, Histogram
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
import sqlite3

from app.config import app_settings
from app.database import initialize_database, get_db_dependency
from app import crud, schemas, dependencies
from sqlalchemy.orm import Session

logger_instance = logging.getLogger(__name__)

REQUEST_COUNTER = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

redis_client_instance = None


@asynccontextmanager
async def app_lifespan(app_instance: FastAPI):
    try:
        initialize_database()
        logger.info("Приложение запущено")

        try:
            if "sqlite" in app_settings.database_url:
                db_path = app_settings.database_url.replace("sqlite:///", "")
                if not os.path.exists(db_path):
                    with open(db_path, 'w') as f:
                        pass
                    logger.info(f"Создан файл базы данных: {db_path}")

                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
                logger.info("SQLite база данных подключена успешно")
        except Exception as db_error:
            logger.error(f"Ошибка подключения к базе данных: {db_error}")

        global redis_client_instance
        redis_client_instance = redis.Redis(
            host=app_settings.redis_host,
            port=app_settings.redis_port,
            db=app_settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3
        )

        try:
            redis_client_instance.ping()
            logger.info("Redis подключен успешно")
        except redis.ConnectionError:
            logger.warning("Redis не доступен, работаем без кэша")
            redis_client_instance = None
            app_instance.dependency_overrides[get_db_dependency] = get_db_dependency
    except Exception as error:
        logger.error(f"Ошибка запуска: {error}")
        raise

    yield

    if redis_client_instance:
        redis_client_instance.close()
    logger.info("Приложение остановлено")


app_instance = FastAPI(
    title=app_settings.app_name,
    version=app_settings.api_version,
    debug=app_settings.debug_mode,
    lifespan=app_lifespan,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": "none",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
    }
)

os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)

app_instance.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="app/templates")

metrics_app = make_asgi_app()
app_instance.mount("/metrics", metrics_app)

app_instance.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app_instance.middleware("http")
async def collect_metrics_middleware(request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNTER.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

@app_instance.get("/")
async def read_root(request: Request):
    accept = request.headers.get("accept", "")

    if "text/html" in accept:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "app_settings": app_settings
        })

    return {
        "message": "🐱 Добро пожаловать в Hello Kitty Todo API! 🎀",
        "version": app_settings.api_version,
        "docs": "/docs",
        "health": "/health",
        "kitty_tip": "Будь милым и продуктивным! 🌸",
        "emoji": "🐱🎀🌸"
    }


@app_instance.get("/health")
async def health_check(request: Request):
    health_status = {
        "status": "healthy ❤️",
        "emoji": "🐱🎀🌸",
        "services": {},
        "kitty_message": "Всё работает отлично! 🎀",
        "timestamp": datetime.now().isoformat(),
        "version": app_settings.api_version
    }

    try:
        if redis_client_instance:
            redis_client_instance.ping()
            health_status["services"]["redis"] = {
                "status": "connected",
                "emoji": "🎀",
                "message": "Redis готов к работе!",
                "details": f"{app_settings.redis_host}:{app_settings.redis_port}"
            }
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "error",
            "emoji": "💔",
            "message": str(e)
        }
        health_status["status"] = "degraded ⚠️"

    try:
        if "sqlite" in app_settings.database_url:
            db_path = app_settings.database_url.replace("sqlite:///", "")

            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()

                health_status["services"]["database"] = {
                    "status": "connected",
                    "emoji": "💾",
                    "message": "База данных работает",
                    "details": f"SQLite: {db_path}"
                }
            else:
                health_status["services"]["database"] = {
                    "status": "file_not_found",
                    "emoji": "📁",
                    "message": f"Файл базы данных не найден: {db_path}",
                    "action": "Будет создан при первой записи"
                }
                health_status["status"] = "degraded ⚠️"
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "error",
            "emoji": "💾💔",
            "message": str(e)
        }
        health_status["status"] = "unhealthy 💔"

    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse("health.html", {
            "request": request,
            "health_status": health_status,
            "app_settings": app_settings,
            "datetime": datetime
        })

    return JSONResponse(content=health_status)


@app_instance.get("/kitty")
async def hello_kitty_page():
    return RedirectResponse(url="/")


@app_instance.get("/kitty/tasks-ui")
async def kitty_tasks_ui(request: Request):
    return templates.TemplateResponse("tasks-ui.html", {"request": request})

@app_instance.get("/tasks", response_model=schemas.TasksListResponseSchema)
def read_tasks_list(
        skip_param: int = 0,
        limit_param: int = 100,
        database_session: Session = Depends(get_db_dependency)
):
    try:
        cache_key = f"tasks:{skip_param}:{limit_param}"
        if redis_client_instance:
            try:
                cached_data = redis_client_instance.get(cache_key)
                if cached_data:
                    logger.info("Данные получены из кэша")
                    return eval(cached_data)
            except:
                pass

        tasks_list = crud.task_crud_instance.get_all_tasks(database_session, skip_param, limit_param)
        total_count = crud.task_crud_instance.count_tasks(database_session)

        converted_tasks = []
        for task in tasks_list:
            converted_tasks.append(schemas.TaskResponseSchema.from_orm(task))

        response_data = {
            "tasks": converted_tasks,
            "total": total_count,
            "emoji": "🐱🎀🌸",
            "theme": app_settings.theme.value if hasattr(app_settings.theme, 'value') else app_settings.theme,
            "message": "Вот твои кавайные задачи!"
        }

        if redis_client_instance:
            try:
                redis_client_instance.setex(cache_key, 300, str(response_data))
            except:
                pass

        return response_data
    except Exception as error:
        logger.error(f"Ошибка получения списка задач: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@app_instance.get("/tasks/{task_id}", response_model=schemas.TaskResponseSchema)
def read_single_task(
        task_instance: schemas.TaskResponseSchema = Depends(dependencies.get_task_by_id_dependency)
):
    return schemas.TaskResponseSchema.from_orm(task_instance)


@app_instance.post(
    "/tasks",
    response_model=schemas.TaskResponseSchema,
    status_code=status.HTTP_201_CREATED
)
def create_new_task(
        task_data: schemas.TaskCreateSchema,
        database_session: Session = Depends(get_db_dependency)
):
    try:
        task_dict = task_data.model_dump()
        created_task = crud.task_crud_instance.create_task(database_session, task_dict)

        if redis_client_instance:
            try:
                redis_client_instance.delete("tasks:*")
            except:
                pass

        return schemas.TaskResponseSchema.from_orm(created_task)
    except Exception as error:
        logger.error(f"Ошибка создания задачи: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать задачу"
        )


@app_instance.put("/tasks/{task_id}", response_model=schemas.TaskResponseSchema)
def update_task_completely(
        task_id: int,
        task_data: schemas.TaskUpdateSchema,
        database_session: Session = Depends(get_db_dependency),
        existing_task: schemas.TaskResponseSchema = Depends(dependencies.get_task_by_id_dependency)
):
    try:
        update_dict = task_data.model_dump(exclude_unset=True)
        updated_task = crud.task_crud_instance.update_task(database_session, existing_task, update_dict)

        if redis_client_instance:
            try:
                redis_client_instance.delete(f"task:{task_id}")
                redis_client_instance.delete("tasks:*")
            except:
                pass

        return schemas.TaskResponseSchema.from_orm(updated_task)
    except Exception as error:
        logger.error(f"Ошибка обновления задачи: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить задачу"
        )


@app_instance.patch("/tasks/{task_id}", response_model=schemas.TaskResponseSchema)
def partially_update_task(
        task_id: int,
        task_data: schemas.TaskUpdateSchema,
        database_session: Session = Depends(get_db_dependency),
        existing_task: schemas.TaskResponseSchema = Depends(dependencies.get_task_by_id_dependency)
):
    try:
        update_dict = task_data.model_dump(exclude_unset=True)
        updated_task = crud.task_crud_instance.update_task(database_session, existing_task, update_dict)

        if redis_client_instance:
            try:
                redis_client_instance.delete(f"task:{task_id}")
                redis_client_instance.delete("tasks:*")
            except:
                pass

        return schemas.TaskResponseSchema.from_orm(updated_task)
    except Exception as error:
        logger.error(f"Ошибка частичного обновления задачи: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить задачу"
        )


@app_instance.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_task(
        task_id: int,
        database_session: Session = Depends(get_db_dependency)
):
    try:
        delete_successful = crud.task_crud_instance.delete_task(database_session, task_id)
        if not delete_successful:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Задача с ID {task_id} не найдена"
            )

        if redis_client_instance:
            try:
                redis_client_instance.delete(f"task:{task_id}")
                redis_client_instance.delete("tasks:*")
            except:
                pass

        return None
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Ошибка удаления задачи: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить задачу"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app_instance",
        host="0.0.0.0",
        port=8000,
        reload=app_settings.debug_mode
    )