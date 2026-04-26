from fastapi import APIRouter, Cookie, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from database.db import (
    get_connection,
    get_user_by_credentials,
    get_user_by_id,
    hash_password,
)

# ─── настройки ────────────────────────────────────────────────────────────────

SECRET_KEY = "CHANGE_ME_IN_PRODUCTION_use_secrets_token_hex_32"
SESSION_COOKIE = "session_token"
SESSION_MAX_AGE = 60 * 60 * 8   # 8 часов

serializer = URLSafeTimedSerializer(SECRET_KEY)
templates = Jinja2Templates(directory="templates")
router = APIRouter()

# ─── исключение-редирект ───────────────────────────────────────────────────────

class _RedirectException(Exception):
    def __init__(self, url: str):
        self.url = url

def _redirect(url: str) -> _RedirectException:
    return _RedirectException(url)

# ─── логи входов ──────────────────────────────────────────────────────────────

def _ensure_login_log_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    NOT NULL,
            success    INTEGER NOT NULL DEFAULT 0,
            ip_address TEXT,
            user_id    INTEGER,
            role       TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

def log_login_attempt(
    username: str,
    success: bool,
    ip: str,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
):
    _ensure_login_log_table()
    conn = get_connection()
    conn.execute(
        "INSERT INTO login_log (username, success, ip_address, user_id, role) VALUES (?, ?, ?, ?, ?)",
        (username, int(success), ip, user_id, role),
    )
    conn.commit()
    conn.close()

# ─── сессия ───────────────────────────────────────────────────────────────────

def create_session_token(user_id: int, role: str) -> str:
    """Кодирует user_id + role в подписанный токен."""
    return serializer.dumps({"user_id": user_id, "role": role})

def decode_session_token(token: str) -> Optional[dict]:
    """Возвращает {"user_id": ..., "role": ...} или None."""
    try:
        return serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

# ─── получение текущего пользователя ─────────────────────────────────────────

def get_current_user(session_token: str = Cookie(default=None)) -> Optional[dict]:
    """
    Возвращает dict пользователя (из таблицы users ИЛИ students) или None.
    В словаре гарантированно есть поле 'role'.
    """
    if not session_token:
        return None
    data = decode_session_token(session_token)
    if not data:
        return None

    role    = data.get("role")
    user_id = data.get("user_id")

    if role == "student":
        conn = get_connection()
        row = conn.execute(
            "SELECT id, name, login AS username, coins, id_group FROM students WHERE id = ?",
            (user_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        user = dict(row)
        user["role"]      = "student"
        user["full_name"] = user.get("name", "")
        return user
    else:
        row = get_user_by_id(user_id)
        if not row:
            return None
        return dict(row)

# ─── зависимости (Depends) ────────────────────────────────────────────────────

def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise _redirect("/login")
    return user

def require_admin(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise _redirect("/login")
    if user.get("role") != "admin":
        raise _redirect("/403")
    return user

def require_teacher_or_admin(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise _redirect("/login")
    if user.get("role") not in ("admin", "teacher"):
        raise _redirect("/403")
    return user

def require_student(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise _redirect("/login")
    if user.get("role") != "student":
        raise _redirect("/403")
    return user

# ─── вспомогательная функция: установить куки и редиректнуть ─────────────────

def _make_session_response(user_id: int, role: str, redirect_url: str) -> RedirectResponse:
    token = create_session_token(user_id, role)
    response = RedirectResponse(redirect_url, status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response

# ─── GET /login ───────────────────────────────────────────────────────────────

@router.get("/login")
def login_page(request: Request, session_token: str = Cookie(default=None)):
    if session_token and decode_session_token(session_token):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        request, "auth/login.html",
        {"error": None, "active_tab": "student"}
    )

# ─── POST /login/student ──────────────────────────────────────────────────────

@router.post("/login/student")
def login_student(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    ip = request.client.host if request.client else "unknown"

    conn = get_connection()
    row = conn.execute(
        "SELECT id, name, username, password FROM students WHERE username = ?", 
        (username,)
    ).fetchone()
    conn.close()

    if not row or row["password"] != hash_password(password):
        log_login_attempt(username, success=False, ip=ip, role="student")
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Неверный логин или пароль", "active_tab": "student"},
            status_code=401,
        )

    log_login_attempt(username, success=True, ip=ip, user_id=row["id"], role="student")
    return _make_session_response(row["id"], "student", "/shop")

# ─── POST /login/teacher ──────────────────────────────────────────────────────

@router.post("/login/teacher")
def login_teacher(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    ip = request.client.host if request.client else "unknown"
    user = get_user_by_credentials(username, password)

    if not user or user["role"] not in ("teacher",):
        log_login_attempt(username, success=False, ip=ip, role="teacher")
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Неверный логин или пароль учителя", "active_tab": "teacher"},
            status_code=401,
        )

    log_login_attempt(username, success=True, ip=ip, user_id=user["id"], role="teacher")
    return _make_session_response(user["id"], user["role"], "/students")

# ─── POST /login/admin ────────────────────────────────────────────────────────

@router.post("/login/admin")
def login_admin(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    ip = request.client.host if request.client else "unknown"
    user = get_user_by_credentials(username, password)

    if not user or user["role"] != "admin":
        log_login_attempt(username, success=False, ip=ip, role="admin")
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Неверный логин или пароль администратора", "active_tab": "admin"},
            status_code=401,
        )

    log_login_attempt(username, success=True, ip=ip, user_id=user["id"], role="admin")
    return _make_session_response(user["id"], user["role"], "/admin")

# ─── GET /logout ──────────────────────────────────────────────────────────────

@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response

# ─── GET /403 ─────────────────────────────────────────────────────────────────

@router.get("/403")
def forbidden(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        request, "auth/403.html", {"user": user}, status_code=403
    )

# ─── GET/POST /admin ──────────────────────────────────────────────────────────

@router.get("/admin")
def admin_dashboard(request: Request, user: dict = Depends(require_admin)):
    conn = get_connection()
    users = conn.execute(
        "SELECT id, username, role, full_name, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return templates.TemplateResponse(
        request, "auth/admin.html",
        {"user": user, "users": [dict(u) for u in users]},
    )

@router.get("/admin/login-log")
def admin_login_log(request: Request, user: dict = Depends(require_admin)):
    _ensure_login_log_table()
    conn = get_connection()
    logs = conn.execute("""
        SELECT ll.id, ll.username, ll.success, ll.ip_address, ll.created_at,
               ll.role, u.full_name
        FROM login_log ll
        LEFT JOIN users u ON ll.user_id = u.id
        ORDER BY ll.created_at DESC
        LIMIT 500
    """).fetchall()
    conn.close()
    return templates.TemplateResponse(
        request, "auth/login_log.html",
        {"user": user, "logs": [dict(l) for l in logs]},
    )

# ─── Управление пользователями (teachers/admins) ──────────────────────────────

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
            request, "auth/add_user.html",
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

# ─── Управление логином/паролем студентов (только admin) ─────────────────────

@router.get("/admin/students/{student_id}/set-credentials")
def set_student_credentials_page(
    request: Request,
    student_id: int,
    user: dict = Depends(require_admin),
):
    conn = get_connection()
    student = conn.execute(
        "SELECT id, name, login FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    conn.close()
    if not student:
        return RedirectResponse("/students", status_code=303)
    return templates.TemplateResponse(
        request, "auth/set_student_credentials.html",
        {"user": user, "student": dict(student), "error": None, "success": None},
    )

@router.post("/admin/students/{student_id}/set-credentials")
def set_student_credentials(
    request: Request,
    student_id: int,
    login: str = Form(...),
    password: str = Form(...),
    user: dict = Depends(require_admin),
):
    conn = get_connection()
    # Проверить: логин уже занят другим студентом?
    existing = conn.execute(
        "SELECT id FROM students WHERE login = ? AND id != ?", (login, student_id)
    ).fetchone()
    if existing:
        student = conn.execute(
            "SELECT id, name, login FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        conn.close()
        return templates.TemplateResponse(
            request, "auth/set_student_credentials.html",
            {"user": user, "student": dict(student),
             "error": "Этот логин уже занят другим студентом", "success": None},
        )

    conn.execute(
        "UPDATE students SET login = ?, password = ? WHERE id = ?",
        (login, hash_password(password), student_id),
    )
    conn.commit()
    student = conn.execute(
        "SELECT id, name, login FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    conn.close()
    return templates.TemplateResponse(
        request, "auth/set_student_credentials.html",
        {"user": user, "student": dict(student),
         "error": None, "success": f"Логин и пароль для {student['name']} обновлены!"},
    )
