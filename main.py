from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates

import sys
import os

# Добавляем путь к проекту для корректных импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import (
    init_db,
    get_connection,
    create_user,
    hash_password
)
from app.routes.students import router as students_router
from app.routes.shop import router as shop_router
from app.routes.auth import router as auth_router, _ensure_login_log_table, _RedirectException, get_current_user
from app.routes.teachers import router as teachers_router

SECRET_KEY = "TheSecretSecretSecretSecretKey00"

app = FastAPI(title="School Coins")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

templates = Jinja2Templates(directory="templates")

# Обработчик редиректов из Depends
@app.exception_handler(_RedirectException)
async def redirect_exception_handler(request: Request, exc: _RedirectException):
    return RedirectResponse(exc.url, status_code=302)

# Подключение роутеров
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(teachers_router)
app.include_router(shop_router)

# Статика
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass

# Главная страница
@app.get("/")
def index(request: Request):
    user = get_current_user(request.cookies.get("session_token"))
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="shop/index.html",
        context={"user": user}
    )

# Инициализация БД при старте
@app.on_event("startup")
def on_startup():
    init_db()
    _ensure_login_log_table()
    _seed_admin()

def _seed_admin():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    
    # Если пользователей нет вообще - создаем админа
    if count == 0:
        create_user(
            username="admin",
            password=hash_password("admin123"),
            role="admin",        # <--- ИСПРАВЛЕНО: было user_role, должно быть role
            full_name="Администратор",
        )
        print("✅ Создан администратор: admin / admin123 — СМЕНИТЕ ПАРОЛЬ!")