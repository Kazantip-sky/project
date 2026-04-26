from urllib import request
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from fastapi.responses import JSONResponse
from database.db import buy_item, get_all_students, get_connection

from fastapi import Form, HTTPException
from database.db import (
    add_shop_category, add_shop_item, get_all_items, get_all_categories,
    update_shop_item, delete_shop_item, get_shop_item_by_id,
    get_student_purchases, get_student_by_id
)

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


# администрированиe категорий ----------------------------------------------------------------------

@router.get("/admin/categories")
def admin_categories(request: Request):
    if request.session.get("user_role") != "admin":
        return RedirectResponse("/login", status_code=303)
    categories = get_all_categories()
    return templates.TemplateResponse("shop/admin_categories.html", {
        "request": request,
        "categories": categories
    })

@router.post("/admin/categories/add")
def admin_add_category(name: str = Form(...), description: str = Form(None), sort_order: int = Form(0)):
    add_shop_category(name, description, sort_order)
    return RedirectResponse("/admin/categories", status_code=303)

@router.post("/admin/categories/delete/{cat_id}")
def admin_delete_category(cat_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE shop_items SET category_id = NULL WHERE category_id = ?", (cat_id,))
    cursor.execute("DELETE FROM shop_categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin/categories", status_code=303)

# управлениe товарами ----------------------------------------------------------------------

@router.get("/admin/items")
def admin_items(request: Request):
    if request.session.get("user_role") != "admin":
        return RedirectResponse("/login", status_code=303)
    items = get_all_items()          
    categories = get_all_categories()
    return templates.TemplateResponse("shop/admin_items.html", {
        "request": request,
        "items": items,
        "categories": categories
    })

@router.post("/admin/items/add")
def admin_add_item(
    name: str = Form(...),
    price: int = Form(...),
    description: str = Form(None),
    category_id: int = Form(None),
    quantity: int = Form(-1),
    image_url: str = Form(None),
    is_active: bool = Form(True)
):
    add_shop_item(
        name=name,
        price=price,
        description=description,
        category_id=category_id,
        quantity=quantity,
        image_url=image_url,
        created_by=request.session.get("user_id")
    )
    return RedirectResponse("/admin/items", status_code=303)

@router.get("/admin/items/edit/{item_id}")
def admin_edit_item_form(request: Request, item_id: int):
    if request.session.get("user_role") != "admin":
        return RedirectResponse("/login", status_code=303)
    item = get_shop_item_by_id(item_id)
    categories = get_all_categories()
    return templates.TemplateResponse("shop/admin_item_edit.html", {
        "request": request,
        "item": item,
        "categories": categories
    })

@router.post("/admin/items/edit/{item_id}")
def admin_edit_item(
    item_id: int,
    name: str = Form(...),
    price: int = Form(...),
    description: str = Form(None),
    category_id: int = Form(None),
    quantity: int = Form(-1),
    image_url: str = Form(None),
    is_active: bool = Form(True)
):
    update_shop_item(item_id, name, price, description, category_id, quantity, image_url, is_active)
    return RedirectResponse("/admin/items", status_code=303)

@router.post("/admin/items/delete/{item_id}")
def admin_delete_item(item_id: int):
    delete_shop_item(item_id)
    return RedirectResponse("/admin/items", status_code=303)

# История покупок студента (личный кабинет) ----------------------------------------------------------------------

@router.get("/profile/purchases")
def student_purchases(request: Request):
    student_id = request.session.get("student_id")
    if not student_id:
        return RedirectResponse("/login", status_code=303)
    purchases = get_student_purchases(student_id)
    student = get_student_by_id(student_id)
    return templates.TemplateResponse("shop/purchases.html", {
        "request": request,
        "purchases": purchases,
        "student": student
    })

# история покупок конкретного студента(Для учителя или админа) ----------------------------------------------------------------------

@router.get("/students/{student_id}/purchases")
def student_purchases_for_teacher(request: Request, student_id: int):
    user_role = request.session.get("user_role")
    if user_role not in ("admin", "teacher"):
        return RedirectResponse("/login", status_code=303)
    if user_role == "teacher":
        teacher_id = request.session.get("user_id")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM students s
            JOIN teacher_classes tc ON s.id_group = tc.group_id
            WHERE s.id = ? AND tc.teacher_id = ?
        """, (student_id, teacher_id))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse({"error": "Доступ запрещён"}, status_code=403)
        conn.close()
    purchases = get_student_purchases(student_id)
    student = get_student_by_id(student_id)
    return templates.TemplateResponse("shop/purchases.html", {
        "request": request,
        "purchases": purchases,
        "student": student,
        "back_url": f"/students"
    })