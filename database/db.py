



def create():
    open()
    cursor.execute('''PRAGMA foreign_keys=on''')

    do('''CREATE TABLE transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT FULL,
        amount INTEGER,
        reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES student(id)
        );'''
    )

    do('''SELECT student.name, transactions.amount, transactions.reascon
        FROM transactions
        JOIN students ON transactions.student_id = students.id;'''
    )
    
    close()