from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database.db import (
    get_all_students, create_student, delete_student,
    get_student_by_id, get_student_transactions, get_student_purchases,
)
from app.routes.auth import require_user, require_admin
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get('/students')
def students_page(request: Request, user: dict = Depends(require_user)):
    students = get_all_students()
    return templates.TemplateResponse(
        request, 'students/list.html', {'students': students, 'user': user}
    )


@router.get('/students/add')
def add_student_page(request: Request, user: dict = Depends(require_admin)):
    return templates.TemplateResponse(
        request, 'students/create_student.html', {'user': user}
    )


@router.get('/students/{student_id}')
def student_detail(request: Request, student_id: int, user: dict = Depends(require_user)):
    student = get_student_by_id(student_id)
    if not student:
        return RedirectResponse('/students', status_code=303)
    transactions = get_student_transactions(student_id)
    purchases = get_student_purchases(student_id)
    return templates.TemplateResponse(
        request, 'students/detail.html',
        {'student': student, 'transactions': transactions,
         'purchases': purchases, 'user': user}
    )


@router.post('/student/add')
def add_student(
    name: str = Form(...),
    class_name: str = Form(...),
    user: dict = Depends(require_admin),
):
    create_student(name, class_name)
    return RedirectResponse('/students', status_code=303)


@router.post('/student/delete')
def remove_student(
    student_id: int = Form(...),
    user: dict = Depends(require_admin),
):
    delete_student(student_id)
    return RedirectResponse('/students', status_code=303)
