import hashlib
import sqlite3

DB_PATH = 'database.db'


# ── utils ─────────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """SHA-256 хэш пароля. Для продакшена используйте bcrypt/argon2."""
    return hashlib.sha256(plain.encode()).hexdigest()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── init ──────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Создаем таблицы (если не существуют)
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS students (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            coins      INTEGER DEFAULT 0,
            id_group   INTEGER,          
            attendance TEXT,          
            login      TEXT,              
            password   TEXT,             
            created_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            amount     INTEGER NOT NULL,
            reason     TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        );
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            role       TEXT NOT NULL,
            full_name  TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    
        CREATE TABLE IF NOT EXISTS teacher_classes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            group_id   INTEGER NOT NULL,
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(teacher_id, group_id)
        );
        CREATE TABLE IF NOT EXISTS shop_categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT,
            sort_order  INTEGER DEFAULT 0,
            is_active   BOOLEAN DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS shop_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT,
            price       INTEGER NOT NULL,
            category_id INTEGER,
            quantity    INTEGER DEFAULT -1,
            image_url   TEXT,
            is_active   BOOLEAN DEFAULT 1,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by  INTEGER,
            FOREIGN KEY (category_id) REFERENCES shop_categories(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS purchases (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id   INTEGER NOT NULL,
            item_id      INTEGER NOT NULL,
            price_paid   INTEGER NOT NULL,
            purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (item_id) REFERENCES shop_items(id)
        );
    ''')

    # 2. Миграции (добавление колонок в старые таблицы)
    migrations = [
        'ALTER TABLE students ADD COLUMN login TEXT',
        'ALTER TABLE students ADD COLUMN password TEXT',
        'ALTER TABLE students ADD COLUMN created_by INTEGER',
        'ALTER TABLE transactions ADD COLUMN created_by INTEGER',
        # Колонка для прав учителей:
        'ALTER TABLE users ADD COLUMN can_add_students INTEGER DEFAULT 0' 
    ]

    for sql in migrations:
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception:
            pass # Колонка уже существует, пропускаем

    # 3. Заполнение магазина тестовыми товарами (если пусто)
    cursor.execute("SELECT COUNT(*) FROM shop_items")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("️ Магазин пуст. Заполняем тестовыми товарами...")
        try:
            cursor.executescript('''
                INSERT INTO shop_items (name, description, price, image_url, quantity, is_active, created_by)
                VALUES 
                    ('Уточка‑джентльмен',  'Стильная уточка в шляпе',  100,  '/static/images/duck_gentleman.jpg', -1, 1, 1),
                    ('Синяя уточка',       'Яркая синяя уточка',       75,   '/static/images/duck_blue.webp',     -1, 1, 1),
                    ('Уточка‑человек',     'Загадочная уточка',        120,  '/static/images/duck_human.jpg',     -1, 1, 1),
                    ('Классическая уточка','Обычная резиновая уточка', 50,   '/static/images/duck.jpg',           -1, 1, 1),
                    ('Антон',              'Антон не Чигур',           75,   '/static/images/anton.png',          -1, 1, 1),
                    ('Артур',              'Артур Микаэлян',           100,  '/static/images/artur.png',          -1, 1, 1),
                    ('Buggati',            'Буггага',                  5000, '/static/images/buggati.png',        -1, 1, 1),
                    ('Быков',              'Быков',                    1000, '/static/images/bykov.png',          -1, 1, 1),
                    ('Кузя',               'Кузя',                     500,  '/static/images/kuzy.png',           -1, 1, 1),
                    ('Lamborgini',         'Ламба',                    2500, '/static/images/lamba.png',          -1, 1, 1),
                    ('Лобанов',            'Лобанов',                  1000, '/static/images/lobanov.png',        -1, 1, 1),
                    ('Nissan_gtr',         'Ниссанчик',                2500, '/static/images/nissan_gtr.png',     -1, 1, 1),
                    ('Романенко',          'Романенко',                100,  '/static/images/romanenko.png',      -1, 1, 1),
                    ('Котость',            'Котость в майне',          0,    '/static/images/kotosti.jpg',        -1, 1, 1);
            ''')
            conn.commit()
            print("✅ Товары успешно добавлены в магазин.")
        except Exception as e:
            print("❌ Ошибка вставки товаров:", e)

    conn.close()


# ── auth ──────────────────────────────────────────────────────────────────────

def get_user_by_credentials(username: str, password: str) -> sqlite3.Row | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM users WHERE username = ?',
        (username,)
    )
    user = cursor.fetchone()
    conn.close()

    if not user:
        return None
    if user['password'] != hash_password(password):
        return None
    return user


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


# ── users / teachers ──────────────────────────────────────────────────────────

def create_user(username: str, password: str, role: str, full_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)',
        (username, password, role, full_name)
    )
    conn.commit()
    conn.close()


def get_all_teachers():
    conn = get_connection()
    cursor = conn.cursor()
    # Запрашиваем также колонку can_add_students
    cursor.execute(
        "SELECT id, username, full_name, created_at, can_add_students FROM users WHERE role = 'teacher'"
    )
    teachers = cursor.fetchall()
    conn.close()
    return teachers


def get_teacher_by_id(teacher_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, full_name, created_at FROM users WHERE id = ? AND role = 'teacher'",
        (teacher_id,)
    )
    teacher = cursor.fetchone()
    conn.close()
    return teacher


def get_teacher_groups(teacher_id: int):   
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT group_id FROM teacher_classes WHERE teacher_id = ?',
        (teacher_id,)
    )
    groups = cursor.fetchall()
    conn.close()
    return groups

def assign_teacher_to_group(teacher_id: int, group_id: int):   
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO teacher_classes (teacher_id, group_id) VALUES (?, ?)',
        (teacher_id, group_id)
    )
    conn.commit()
    conn.close()

def remove_teacher_from_group(teacher_id: int, group_id: int): 
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM teacher_classes WHERE teacher_id = ? AND group_id = ?',
        (teacher_id, group_id)
    )
    conn.commit()
    conn.close()


def delete_teacher(teacher_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (teacher_id,))
    conn.commit()
    conn.close()


# ── students ──────────────────────────────────────────────────────────────────

def create_student(name: str, group_id: int = None, login: str = None, password: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO students (name, id_group, login, password) VALUES (?, ?, ?, ?)',
        (name, group_id, login, password)
    )
    conn.commit()
    conn.close()


def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students') 
    students = cursor.fetchall()
    conn.close()
    return students


def get_student_by_id(student_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    return student


def delete_student(student_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()


def add_coins_by_teacher(teacher_id: int, student_id: int, amount: int, reason: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM students s
        JOIN teacher_classes tc ON s.id_group = tc.group_id
        WHERE s.id = ? AND tc.teacher_id = ?
    ''', (student_id, teacher_id))
    if cursor.fetchone():
        cursor.execute('UPDATE students SET coins = coins + ? WHERE id = ?', (amount, student_id))
        cursor.execute('''
            INSERT INTO transactions (student_id, amount, reason, created_by)
            VALUES (?, ?, ?, ?)
        ''', (student_id, amount, reason, teacher_id))
        conn.commit()
    conn.close()

def get_student_transactions(student_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT amount, reason, created_at
        FROM transactions
        WHERE student_id = ?
        ORDER BY created_at DESC
    ''', (student_id,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions


def get_student_purchases(student_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT si.name, si.image_url, p.price_paid, p.purchased_at
        FROM purchases p
        JOIN shop_items si ON p.item_id = si.id
        WHERE p.student_id = ?
        ORDER BY p.purchased_at DESC
    ''', (student_id,))
    purchases = cursor.fetchall()
    conn.close()
    return purchases


# ── shop ──────────────────────────────────────────────────────────────────────

def add_shop_category(name: str, description: str = None, sort_order: int = 0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shop_categories (name, description, sort_order) VALUES (?, ?, ?)',
        (name, description, sort_order)
    )
    conn.commit()
    conn.close()


def add_shop_item(
    name: str,
    price: int,
    description: str = None,
    category_id: int = None,
    quantity: int = -1,
    image_url: str = None,
    created_by: int = None,
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shop_items (name, description, price, category_id, quantity, image_url, created_by) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (name, description, price, category_id, quantity, image_url, created_by)
    )
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id


def get_all_items():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            si.id,
            si.name,
            si.description,
            si.price,
            si.quantity,
            si.image_url,
            sc.name AS category_name
        FROM shop_items si
        LEFT JOIN shop_categories sc ON si.category_id = sc.id
        WHERE si.is_active = 1
        ORDER BY sc.sort_order, si.name
    ''')
    items = cursor.fetchall()
    conn.close()
    return items

def get_all_categories():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shop_categories ORDER BY sort_order")
    cats = cursor.fetchall()
    conn.close()
    return cats

def update_shop_item(item_id, name, price, description, category_id, quantity, image_url, is_active):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE shop_items
        SET name=?, price=?, description=?, category_id=?, quantity=?, image_url=?, is_active=?
        WHERE id=?
    """, (name, price, description, category_id, quantity, image_url, is_active, item_id))
    conn.commit()
    conn.close()

def delete_shop_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shop_items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_shop_item_by_id(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shop_items WHERE id=?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    return item

def search_items(search_term: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            si.id,
            si.name,
            si.description,
            si.price,
            si.quantity,
            si.image_url,
            sc.name AS category_name
        FROM shop_items si
        LEFT JOIN shop_categories sc ON si.category_id = sc.id
        WHERE si.is_active = 1
          AND (si.name LIKE ? OR si.description LIKE ?)
        ORDER BY sc.sort_order, si.name
    ''', (f'%{search_term}%', f'%{search_term}%'))
    items = cursor.fetchall()
    conn.close()
    return items

def search_items_by_category(category_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT si.*, sc.name as category_name
        FROM shop_items si
        JOIN shop_categories sc ON si.category_id = sc.id
        WHERE sc.name = ? AND si.is_active = 1
    ''', (category_name,))
    items = cursor.fetchall()
    conn.close()
    return items


def buy_item(student_id: int, item_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        conn.execute('BEGIN IMMEDIATE')

        cursor.execute(
            'SELECT id, name, price, quantity, is_active FROM shop_items WHERE id = ?',
            (item_id,)
        )
        item = cursor.fetchone()

        if not item:
            return {'ok': False, 'error': 'Товар не найден'}
        if not item['is_active']:
            return {'ok': False, 'error': 'Товар недоступен'}
        if item['quantity'] == 0:
            return {'ok': False, 'error': 'Товар закончился'}

        cursor.execute('SELECT coins FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()

        if not student:
            return {'ok': False, 'error': 'Студент не найден'}
        if student['coins'] < item['price']:
            return {'ok': False, 'error': 'Недостаточно монет'}

        cursor.execute(
            'UPDATE students SET coins = coins - ? WHERE id = ?',
            (item['price'], student_id)
        )

        if item['quantity'] > 0:
            cursor.execute(
                'UPDATE shop_items SET quantity = quantity - 1 WHERE id = ?',
                (item_id,)
            )

        cursor.execute(
            'INSERT INTO transactions (student_id, amount, reason) VALUES (?, ?, ?)',
            (student_id, -item['price'], f'Покупка: {item["name"]}')
        )

        cursor.execute(
            'INSERT INTO purchases (student_id, item_id, price_paid) VALUES (?, ?, ?)',
            (student_id, item_id, item['price'])
        )

        conn.commit()
        return {'ok': True}

    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}
    finally:
        conn.close()

# Для админа – показать все товары (включая неактивные)
def get_all_items_admin():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT si.*, sc.name as category_name
        FROM shop_items si
        LEFT JOIN shop_categories sc ON si.category_id = sc.id
        ORDER BY si.is_active DESC, sc.sort_order, si.name
    """)
    items = cursor.fetchall()
    conn.close()
    return items

def toggle_teacher_student_rights(teacher_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    # Сначала узнаем текущее состояние
    cursor.execute("SELECT can_add_students FROM users WHERE id = ?", (teacher_id,))
    row = cursor.fetchone()
    
    if row:
        current_state = row['can_add_students']
        new_state = 1 if current_state == 0 else 0
        cursor.execute("UPDATE users SET can_add_students = ? WHERE id = ?", (new_state, teacher_id))
        conn.commit()
    conn.close()