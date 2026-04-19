from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from fastapi.responses import JSONResponse
from database.db import buy_item, get_all_students

router = APIRouter()
templates = None  

@router.get('/students')
def students_page(request: Request):
    students = get_all_students()
    return templates.TemplateResponse(request, 'students/list.html', {'students': students})
 
 
@router.post('/shop/buy')
def shop_buy(student_id: int = Form(...), item_id: int = Form(...)):
    result = buy_item(student_id=student_id, item_id=item_id)
 
    if result['ok']:
        return JSONResponse({'ok': True, 'message': 'Покупка успешна!'})
    else:
        return JSONResponse(
            {'ok': False, 'message': result['error']},
            status_code=400
        )
 