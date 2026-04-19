from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database.db import get_all_students, create_student, delete_student, get_student_by_id, get_student_transactions, get_student_purchases

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get('/students')
def students_page(request: Request):
    students = get_all_students()
    return templates.TemplateResponse(request, 'students/list.html', {'students': students})

@router.get('/students/add')
def add_student_page(request: Request):
    return templates.TemplateResponse(request, 'students/create_student.html', {})

@router.get('/students/{student_id}')
def student_detail(request: Request, student_id: int):
    student = get_student_by_id(student_id)
    if not student:
        return RedirectResponse('/students', status_code=303)
    transactions = get_student_transactions(student_id)
    purchases = get_student_purchases(student_id)
    return templates.TemplateResponse(request, 'students/detail.html', {
        'student': student,
        'transactions': transactions,
        'purchases': purchases,
    })

@router.post('/student/add')
def add_student(name: str = Form(...), class_name: str = Form(...)):
    create_student(name, class_name)
    return RedirectResponse('/students', status_code=303)

@router.post('/student/delete')      
def remove_student(student_id: int = Form(...)):
    delete_student(student_id)
    return RedirectResponse('/students', status_code=303)