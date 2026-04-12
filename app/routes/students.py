from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database.db import get_all_students, create_student  # добавь импорты

router = APIRouter()
templates = Jinja2Templates(directory="templates")  # было: templates = None

@router.get('/students')
def students_page(request: Request):
    students = get_all_students()
    return templates.TemplateResponse(request, 'students/list.html', {'students': students})

@router.post('/student/add')
def add_student(name: str = Form(...), class_name: str = Form(...)):
    create_student(name, class_name)
    return RedirectResponse('/students', status_code=303)