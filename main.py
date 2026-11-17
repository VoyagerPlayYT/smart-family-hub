import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="Smart Home & Family Task Hub")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "family_hub.db")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            assignee TEXT NOT NULL DEFAULT 'Семья',
            category TEXT NOT NULL DEFAULT 'Дом',
            priority TEXT NOT NULL DEFAULT 'Обычный',
            status TEXT NOT NULL DEFAULT 'todo',
            due_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS shopping_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Продукты',
            quantity TEXT DEFAULT '1 шт',
            is_completed INTEGER DEFAULT 0,
            added_by TEXT DEFAULT 'Семья',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Первичные уютные семейные данные
    cur.execute("SELECT COUNT(*) FROM tasks")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO tasks (title, assignee, category, priority, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("Полить комнатные растения и орхидеи", "Мама", "Уют", "Обычный", "done", "Сегодня"),
            ("Купить фильтр для питьевой воды Аквафор", "Папа", "Дом", "Высокий", "todo", "Завтра"),
            ("Сделать резервную копию семейного фотоархива", "Я", "IT & Сервер", "Высокий", "in_progress", "На этой неделе"),
            ("Составить список меню на выходные", "Семья", "Питание", "Обычный", "todo", "Суббота"),
            ("Оплатить коммунальные услуги и интернет", "Папа", "Финансы", "Высокий", "done", "15 число")
        ])

    cur.execute("SELECT COUNT(*) FROM shopping_items")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO shopping_items (name, category, quantity, is_completed, added_by)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("Молоко цельное 3.2%", "Продукты", "2 бутылки", 1, "Мама"),
            ("Хлеб зерновой / Багет", "Продукты", "1 шт", 1, "Я"),
            ("Сыр Пармезан или Тильзитер", "Продукты", "300 г", 0, "Мама"),
            ("Оливковое масло Extra Virgin", "Продукты", "1 бут", 0, "Папа"),
            ("Батарейки АА для пультов", "Для дома", "Упаковка 4 шт", 0, "Папа"),
            ("Витамин C и чай с мятой", "Аптека", "1 уп", 0, "Семья")
        ])

    conn.commit()
    conn.close()


init_db()


# Models
class TaskCreate(BaseModel):
    title: str
    assignee: str = "Семья"
    category: str = "Дом"
    priority: str = "Обычный"
    due_date: Optional[str] = "Скоро"


class StatusUpdate(BaseModel):
    status: str


class ShoppingItemCreate(BaseModel):
    name: str
    category: str = "Продукты"
    quantity: str = "1 шт"
    added_by: str = "Семья"


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# API: Tasks
@app.get("/api/tasks")
async def list_tasks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks ORDER BY id DESC")
    tasks = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"tasks": tasks}


@app.post("/api/tasks")
async def create_task(data: TaskCreate):
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="Название задачи обязательно")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (title, assignee, category, priority, status, due_date)
        VALUES (?, ?, ?, ?, 'todo', ?)
    """, (data.title, data.assignee, data.category, data.priority, data.due_date))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"status": "ok", "id": new_id}


@app.patch("/api/tasks/{task_id}/status")
async def update_task_status(task_id: int, data: StatusUpdate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = ? WHERE id = ?", (data.status, task_id))
    conn.commit()
    conn.close()
    return {"status": "updated"}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


# API: Shopping
@app.get("/api/shopping")
async def list_shopping():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shopping_items ORDER BY is_completed ASC, id DESC")
    items = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"items": items}


@app.post("/api/shopping")
async def create_shopping(data: ShoppingItemCreate):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Название товара обязательно")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shopping_items (name, category, quantity, is_completed, added_by)
        VALUES (?, ?, ?, 0, ?)
    """, (data.name, data.category, data.quantity, data.added_by))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"status": "ok", "id": new_id}


@app.patch("/api/shopping/{item_id}/toggle")
async def toggle_shopping_item(item_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE shopping_items SET is_completed = 1 - is_completed WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "toggled"}


@app.post("/api/shopping/clear-completed")
async def clear_completed_shopping():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM shopping_items WHERE is_completed = 1")
    conn.commit()
    conn.close()
    return {"status": "cleared"}


@app.delete("/api/shopping/{item_id}")
async def delete_shopping(item_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM shopping_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


# API: Stats
@app.get("/api/stats")
async def get_hub_stats():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'done'")
    done_tasks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM shopping_items WHERE is_completed = 0")
    pending_shopping = cur.fetchone()[0]

    conn.close()
    return {
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "pending_shopping": pending_shopping,
        "completion_rate": int((done_tasks / total_tasks * 100)) if total_tasks > 0 else 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=False)
