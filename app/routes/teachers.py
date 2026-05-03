from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from database.db import (
    get_all_teachers,
    get_teacher_by_id,
    create_user,
    delete_teacher,
    assign_teacher_to_group,
    get_teacher_groups,
    remove_teacher_from_group,
    hash_password,
    toggle_teacher_student_rights,  # <-- Добавили
)

from app.routes.auth import require_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/teachers")
def teachers_page(request: Request, user: dict = Depends(require_admin)):
    teachers = get_all_teachers()
    return templates.TemplateResponse(
        request, "teachers/list.html", {"teachers": teachers, "user": user}
    )


@router.get("/teachers/add")
def add_teacher_page(request: Request, user: dict = Depends(require_admin)):
    return templates.TemplateResponse(
        request, "teachers/create_teacher.html", {"user": user}
    )


@router.post("/teachers/add")
def add_teacher(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    user: dict = Depends(require_admin),
):
    create_user(
        username=username,
        password=hash_password(password),
        role="teacher",
        full_name=full_name,
    )
    return RedirectResponse("/teachers", status_code=303)


@router.post("/teachers/{teacher_id}/assign-class")
def assign_class(
    teacher_id: int,
    group_id: int = Form(...),   
    user: dict = Depends(require_admin),
):
    assign_teacher_to_group(teacher_id, group_id)   # переименовано
    return RedirectResponse(f"/teachers/{teacher_id}", status_code=303)

@router.post("/teachers/{teacher_id}/remove-class")
def remove_class(
    teacher_id: int,
    group_id: int = Form(...), 
    user: dict = Depends(require_admin),
):
    remove_teacher_from_group(teacher_id, group_id)
    return RedirectResponse(f"/teachers/{teacher_id}", status_code=303)

@router.get("/teachers/{teacher_id}")
def teacher_detail(
    request: Request,
    teacher_id: int,
    user: dict = Depends(require_admin),
):
    teacher = get_teacher_by_id(teacher_id)
    if not teacher:
        return RedirectResponse("/teachers", status_code=303)
    groups = get_teacher_groups(teacher_id)   
    return templates.TemplateResponse(
        request,
        "teachers/detail.html",
        {"teacher": teacher, "groups": groups, "user": user},
    )


@router.post("/teachers/delete")
def remove_teacher(
    teacher_id: int = Form(...),
    user: dict = Depends(require_admin),
):
    delete_teacher(teacher_id)
    return RedirectResponse("/teachers", status_code=303)

@router.post("/teachers/{teacher_id}/toggle-rights")
def toggle_rights(
    teacher_id: int,
    user: dict = Depends(require_admin),
):
    toggle_teacher_student_rights(teacher_id)
    return RedirectResponse("/teachers", status_code=303)