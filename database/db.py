import sqlite3

DB_PATH = 'database.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript('''
                        CREATE TABLE IF NOT EXISTS students (
                            id      INTEGER PRIMARY KEY AUTOINCREMENT,
                            name    TEXT    NOT NULL,
                            coins   INTEGER DEFAULT 0,
                            class   TEXT
                        );
                        ALTER TABLE students ADD COLUMN created_by INTEGER;
                        CREATE TABLE IF NOT EXISTS transactions (
                            id         INTEGER PRIMARY KEY AUTOINCREMENT,
                            student_id INTEGER NOT NULL,
                            amount     INTEGER NOT NULL,
                            reason     TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (student_id) REFERENCES students(id)
                        );
                        ALTER TABLE transactions ADD COLUMN created_by INTEGER;
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
                            class_name TEXT NOT NULL,      
                            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
                            UNIQUE(teacher_id, class_name)
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
    ''')
    conn.commit()
    conn.close()

def create_student(name, class_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO students (name, class) VALUES(?, ?)',
        (name, class_name)
    )
    conn.commit()
    conn.close()

def create_user(username, password, role, full_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)', 
        (username, password, role, full_name)
    )
    conn.commit()
    conn.close()

def assign_teacher_to_class(teacher_id, class_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO teacher_classes (teacher_id, class_name) VALUES (?, ?)',
        (teacher_id, class_name)
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

def add_coins_by_teacher(teacher_id, student_id, amount, reason):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 1 FROM students s
        JOIN teacher_classes tc ON s.class = tc.class_name
        WHERE s.id = ? AND tc.teacher_id = ?
    ''', 
    (student_id, teacher_id))
    
    if cursor.fetchone():
        cursor.execute(
            'UPDATE students SET coins = coins + ? WHERE id = ?',
            (amount, student_id)
        )
        cursor.execute('''
            INSERT INTO transactions (student_id, amount, reason, created_by)
            VALUES (?, ?, ?, ?)
        ''', 
        (student_id, amount, reason, teacher_id))
        conn.commit()
        print("Монеты начислены!")
    else:
        print("У вас нет прав на начисление монет этому ученику")
    
    conn.close()

def delete_student(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()

def delete_teacher(teacher_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = &', (teacher_id))
    conn.commit()
    conn.close()

def add_shop_category(name, description=None, sort_order=0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shop_categories (name, description, sort_order) VALUES (?, ?, ?)', 
        (name, description, sort_order))
    conn.commit()
    conn.close()
    
def add_shop_item(name, price, description=None, category_id=None, quantity=-1, image_url = None, created_by=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shop_items (name, description, price, category_id, quantity, image_url, created_by)VALUES (?, ?, ?, ?, ?, ?, ?)',
        (name, description, price, category_id, quantity, image_url, created_by))
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id