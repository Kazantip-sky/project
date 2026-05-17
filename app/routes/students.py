from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database.db import (
    get_all_students, create_student, delete_student,
    get_student_by_id, get_student_transactions, get_student_purchases,
)
from app.routes.auth import (
    require_user,
    require_admin,
    require_teacher_or_admin
)
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get('/students')
def students_page(request: Request, user: dict = Depends(require_user)):
    students = get_all_students()
    return templates.TemplateResponse(
        request, 'students/list.html', {'students': students, 'user': user}
    )


@router.get('/students/add')
def add_student_page(request: Request, user: dict = Depends(require_teacher_or_admin)):
    return templates.TemplateResponse(
        request, 'students/create_student.html', {'user': user}
    )


@router.get('/students/{student_id}')
def student_detail(request: Request, student_id: int, user: dict = Depends(require_user)):
    student = get_student_by_id(student_id)
    if user['role'] == 'student' and user['id'] != student_id:
        return RedirectResponse('/students', status_code=303)
    if not student:
        return RedirectResponse('/students', status_code=303)
    transactions = get_student_transactions(student_id)
    purchases = get_student_purchases(student_id)
    return templates.TemplateResponse(
        request, 'students/detail.html',
        {'student': student, 'transactions': transactions,
         'purchases': purchases, 'user': user}
    )

@router.get('/student-profile')
def student_profile(request: Request, user: dict = Depends(require_user)):
    student = get_student_by_id(user['id'])
    if not student:
        return RedirectResponse('/students', status_code=303)
    
    transactions = get_student_transactions(user['id'])
    purchases = get_student_purchases(user['id'])
    
    return templates.TemplateResponse(
        request,
        'students/student_profile.html',
        {
            'student': student,
            'transactions': transactions,
            'purchases': purchases,
            'user': user
        }
    )

@router.post('/student/add')
def add_student(
    name: str = Form(...),
    group_id: int = Form(...), 
    login: str = Form(None),     
    password: str = Form(None),  
    user: dict = Depends(require_teacher_or_admin),
):
    create_student(name, group_id, login, password)
    return RedirectResponse('/students', status_code=303)

@router.post('/student/delete')
def remove_student(
    student_id: int = Form(...),
    user: dict = Depends(require_teacher_or_admin),
):
    delete_student(student_id)
    return RedirectResponse('/students', status_code=303)
@router.post('/students/{student_id}/coins/add')
def add_coins(
    student_id: int,
    amount: int = Form(...),
    user: dict = Depends(require_user),
):
    if user['role'] not in ('admin', 'teacher'):
        return RedirectResponse('/students', status_code=303)

    from database.db import add_student_coins

    add_student_coins(student_id, amount)

    return RedirectResponse('/students', status_code=303)


@router.post('/students/{student_id}/coins/remove')
def remove_coins(
    student_id: int,
    amount: int = Form(...),
    user: dict = Depends(require_user),
):
    if user['role'] not in ('admin', 'teacher'):
        return RedirectResponse('/students', status_code=303)

    from database.db import remove_student_coins

    remove_student_coins(student_id, amount)

    return RedirectResponse('/students', status_code=303)
@router.post('/students/{student_id}/coins/manage')
def manage_student_coins(
    student_id: int,
    amount: int = Form(...),
    reason: str = Form(...),
    action: str = Form(...),
    user: dict = Depends(require_teacher_or_admin),
):

    from database.db import (
        add_student_transaction,
        add_student_coins,
        remove_student_coins,
    )

    if action == 'add':
        add_student_coins(student_id, amount)

        add_student_transaction(
            student_id=student_id,
            amount=amount,
            reason=reason,
            teacher_name=user['full_name']
        )

    elif action == 'remove':

        remove_student_coins(student_id, amount)

        add_student_transaction(
            student_id=student_id,
            amount=-amount,
            reason=reason,
            teacher_name=user['full_name']
        )

    return RedirectResponse(
        f'/students/{student_id}',
        status_code=303
    )