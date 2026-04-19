from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from database.db import init_db, get_all_items, buy_item, get_all_students
from app.routes.students import router as students_router
from app.routes.shop import router as shop_router

print(1)

app = FastAPI()

# Только одно объявление!
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(students_router)
app.include_router(shop_router)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return RedirectResponse("/students")

@app.get("/shop")
def shop_page(request: Request):
    students = get_all_students()
    student = students[0] if students else None
    return templates.TemplateResponse(request, "shop/index.html", {
        "items": get_all_items(),
        "student": student,     
        "message": None,          
        "message_type": None
    })

@app.post("/shop/buy")
def buy(request: Request, student_id: int = Form(...), item_id: int = Form(...)):
    result = buy_item(student_id, item_id)
    if result["ok"]:
        return RedirectResponse("/shop", status_code=303)
    else:
        return templates.TemplateResponse(request, "shop/index.html", {
            "items": get_all_items(),
            "student": None,
            "message": result["error"],
            "message_type": "error"
        })