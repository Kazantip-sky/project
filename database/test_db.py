from db import init_db, create_student, get_all_students

init_db()
create_student('Артем', '10А')
create_student('Мадина', '10В')

students = get_all_students()
for s in students:
    print(s['name'], s['coins'])