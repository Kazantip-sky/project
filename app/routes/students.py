from fastapi import APIRouter, Form, Request
from fastapi.templating import Jinja2Templates
from database.db import create_student, get_all_students
from fastapi.responses import RedirectResponse

router = APIRouter()
templates = Jinja2Templates(directory='templates')

@router.get('/students')
def students_page(request: Request):
    students = get_all_students()
    return templates.TemplateResponse('students/list.html',{'request': request, 'students': students})

@router.post('/student/add')
def add_student(name: str = Form(...), class_name: str = Form(...)):
    create_student(name, class_name)
    return RedirectResponse('/students', status_code=303)