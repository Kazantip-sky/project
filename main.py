from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database.db import init_db, get_connection, hash_password, create_user
from app.routes.auth import router as auth_router, get_current_user, _RedirectException
from app.routes.students import router as students_router
from app.routes.teachers import router as teachers_router

<<<<<<< HEAD


app = FastAPI()
=======
# ── если у тебя есть shop router, подключи его аналогично ─────────────────────
# from app.routes.shop import router as shop_router
>>>>>>> acc7bd5a1e07e081da96d2d1f510d6c040ece55f

app = FastAPI(title="School Coins")
templates = Jinja2Templates(directory="templates")


# ─── глобальный обработчик редиректов из Depends ──────────────────────────────

@app.exception_handler(_RedirectException)
async def redirect_exception_handler(request: Request, exc: _RedirectException):
    return RedirectResponse(exc.url, status_code=302)


# ─── подключение роутеров ─────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(teachers_router)
# app.include_router(shop_router)


# ─── статика (если есть папка static/) ───────────────────────────────────────

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass


# ─── главная страница ─────────────────────────────────────────────────────────

@app.get("/")
def index(request: Request):
    user = get_current_user(request.cookies.get("session_token"))
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("shop/index.html", {"request": request, "user": user})



# ─── инициализация БД при старте ──────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    init_db()
    _ensure_login_log_table()
    _seed_admin()


def _ensure_login_log_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 0,
            ip_address TEXT,
            user_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def _seed_admin():
    """Создаёт администратора admin/admin123 если пользователей нет."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    if count == 0:
        create_user(
            username="admin",
            password=hash_password("admin123"),
            role="admin",
            full_name="Администратор",
        )
        print("✅  Создан администратор: admin / admin123 — СМЕНИТЕ ПАРОЛЬ!")