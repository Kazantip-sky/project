from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# database
from database.db import init_db, get_all_items, buy_item, get_all_students

# routers
from app.routes.students import router as students_router

app = FastAPI()

# шаблоны и статика
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# подключаем роуты
app.include_router(students_router)


# 🔥 ИНИЦИАЛИЗАЦИЯ БАЗЫ
@app.on_event("startup")
def startup():
    init_db()


# ─────────────────────────────
# 📚 STUDENTS (если нет root)
# ─────────────────────────────
@app.get("/")
def root():
    return RedirectResponse("/students")


# ─────────────────────────────
# 🛒 SHOP
# ─────────────────────────────
@app.get("/shop")
def shop_page(request: Request):
    items = get_all_items()

    # временный студент (пока без авторизации)
    students = get_all_students()
    student = students[0] if students else None

    return templates.TemplateResponse("shop/index.html", {
        "request": request,
        "items": items,
        "student": student,
        "categories": []  # пока пусто
    })


@app.post("/shop/buy")
def buy(request: Request,
        student_id: int = Form(...),
        item_id: int = Form(...)):

    result = buy_item(student_id, item_id)

    if result["ok"]:
        return RedirectResponse("/shop", status_code=303)
    else:
        return templates.TemplateResponse("shop/index.html", {
            "request": request,
            "items": get_all_items(),
            "student": None,
            "message": result["error"],
            "message_type": "error"
        })