from fastapi import APIRouter, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from database.db import get_all_items, buy_item
 
router = APIRouter()
templates = Jinja2Templates(directory='templates')
 
 
@router.get('/shop')
def shop_page(request: Request):
    """Список активных товаров магазина."""
    items = get_all_items()
    return templates.TemplateResponse(
        'shop/list.html',
        {'request': request, 'items': items}
    )
 
 
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
 