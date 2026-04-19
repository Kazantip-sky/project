from fastapi import APIRouter, Form, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database.db import get_user_by_credentials, get_user_by_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── helpers ──────────────────────────────────────────────────────────────────

def get_current_user(request: Request) -> dict | None:
    """Возвращает текущего пользователя из сессии или None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def require_login(request: Request) -> dict:
    """Dependency: редиректит на /login если пользователь не авторизован."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return dict(user)


def require_admin(request: Request) -> dict:
    """Dependency: только для администраторов."""
    user = require_login(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return user


def require_teacher(request: Request) -> dict:
    """Dependency: для учителей и администраторов."""
    user = require_login(request)
    if user["role"] not in ("admin", "teacher"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return user


# ── routes ───────────────────────────────────────────────────────────────────

@router.get("/login")
def login_page(request: Request):
    # Если уже залогинен — на главную
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = get_user_by_credentials(username, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Неверный логин или пароль"},
            status_code=401,
        )

    request.session["user_id"] = user["id"]
    request.session["role"] = user["role"]
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/logout")
def logout_get(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)