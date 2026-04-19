from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database.db import (
    get_connection,
    get_user_by_credentials,
    get_user_by_id,
    hash_password,
    init_db,
)

# ─── настройки ────────────────────────────────────────────────────────────────

SECRET_KEY = "CHANGE_ME_IN_PRODUCTION_use_secrets_token_hex_32"
SESSION_COOKIE = "session_token"
SESSION_MAX_AGE = 60 * 60 * 8  # 8 часов

serializer = URLSafeTimedSerializer(SECRET_KEY)
templates = Jinja2Templates(directory="templates")
router = APIRouter()


# ─── логи входов ──────────────────────────────────────────────────────────────

def _ensure_login_log_table():
    """Создаёт таблицу login_log если её нет."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    NOT NULL,
            success    INTEGER NOT NULL DEFAULT 0,
            ip_address TEXT,
            user_id    INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def log_login_attempt(username: str, success: bool, ip: str, user_id: Optional[int] = None):
    _ensure_login_log_table()
    conn = get_connection()
    conn.execute(
        "INSERT INTO login_log (username, success, ip_address, user_id) VALUES (?, ?, ?, ?)",
        (username, int(success), ip, user_id),
    )
    conn.commit()
    conn.close()


# ─── сессия ───────────────────────────────────────────────────────────────────

def create_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def decode_session_token(token: str) -> Optional[int]:
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


# ─── зависимости (Depends) ────────────────────────────────────────────────────

def get_current_user(session_token: str = Cookie(default=None)) -> Optional[dict]:
    """Возвращает словарь с данными пользователя или None."""
    if not session_token:
        return None
    user_id = decode_session_token(session_token)
    if not user_id:
        return None
    row = get_user_by_id(user_id)
    if not row:
        return None
    return dict(row)


def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Редирект на /login если не авторизован."""
    if not user:
        raise _redirect("/login")
    return user


def require_admin(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Редирект на /login (или /403) если не администратор."""
    if not user:
        raise _redirect("/login")
    if user.get("role") != "admin":
        raise _redirect("/403")
    return user


def require_teacher_or_admin(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Доступ только для teacher/admin."""
    if not user:
        raise _redirect("/login")
    if user.get("role") not in ("admin", "teacher"):
        raise _redirect("/403")
    return user


class _RedirectException(Exception):
    def __init__(self, url: str):
        self.url = url


def _redirect(url: str) -> _RedirectException:
    return _RedirectException(url)


# ─── маршруты авторизации ─────────────────────────────────────────────────────

@router.get("/login")
def login_page(request: Request, session_token: str = Cookie(default=None)):
    if session_token and decode_session_token(session_token):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    ip = request.client.host if request.client else "unknown"
    user = get_user_by_credentials(username, password)

    if not user:
        log_login_attempt(username, success=False, ip=ip)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Неверный логин или пароль"},
            status_code=401,
        )

    log_login_attempt(username, success=True, ip=ip, user_id=user["id"])
    token = create_session_token(user["id"])

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ─── страница 403 ─────────────────────────────────────────────────────────────

@router.get("/403")
def forbidden(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        request, "auth/403.html", {"user": user}, status_code=403
    )


# ─── администраторские маршруты ───────────────────────────────────────────────

@router.get("/admin")
def admin_dashboard(request: Request, user: dict = Depends(require_admin)):
    conn = get_connection()
    users = conn.execute(
        "SELECT id, username, role, full_name, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return templates.TemplateResponse(
        request,
        "auth/admin.html",
        {"user": user, "users": [dict(u) for u in users]},
    )


@router.get("/admin/login-log")
def admin_login_log(request: Request, user: dict = Depends(require_admin)):
    _ensure_login_log_table()
    conn = get_connection()
    logs = conn.execute("""
        SELECT ll.id, ll.username, ll.success, ll.ip_address, ll.created_at,
               u.full_name
        FROM login_log ll
        LEFT JOIN users u ON ll.user_id = u.id
        ORDER BY ll.created_at DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return templates.TemplateResponse(
        request,
        "auth/login_log.html",
        {"user": user, "logs": [dict(l) for l in logs]},
    )


@router.get("/admin/users/add")
def add_user_page(request: Request, user: dict = Depends(require_admin)):
    return templates.TemplateResponse(
        request, "auth/add_user.html", {"user": user, "error": None}
    )


@router.post("/admin/users/add")
def add_user_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    user: dict = Depends(require_admin),
):
    from database.db import create_user

    try:
        create_user(
            username=username,
            password=hash_password(password),
            role=role,
            full_name=full_name,
        )
        return RedirectResponse("/admin", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "auth/add_user.html",
            {"user": user, "error": f"Ошибка: {e}"},
        )


@router.post("/admin/users/delete")
def delete_user(
    user_id: int = Form(...),
    admin: dict = Depends(require_admin),
):
    if user_id == admin["id"]:
        return RedirectResponse("/admin", status_code=303)
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)
