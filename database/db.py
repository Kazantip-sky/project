
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
                            name    TEXT    NOT FULL,
                            coins   INTEGER DEFAULT 0,
                            class   TEXT
                        );
                        CREATE TABLE IF NOT EXISTS transactions (
                            id         INTEGER PRIMARY KEY AUTOINCREMENT,
                            student_id INTEGER NOT FULL,
                            amount     INTEGER NOT FULL,
                            reason     TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (student_id) REFERENCES students(id)
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

def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students')
    students = cursor.fetchall()
    conn.close()
    return students

def add_coins(student_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE students SET coins = coins + ? WHERE id = ?',
        (amount, student_id)
    )
    conn.commit()
    conn.close()

def delete_student(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE id = ?', (student_id))
    conn.commit()
    conn.close()