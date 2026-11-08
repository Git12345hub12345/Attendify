from database import AttendifyDatabase

db = AttendifyDatabase('./attendify_db/attendify.db')
students = db.get_all_students()

print(f"Total students in database: {len(students)}")
print("\nStudent Details:")
print("-" * 80)

for student_id, student in students.items():
    print(f"ID: {student_id}")
    print(f"Name: {student['name']}")
    print(f"Email: {student.get('email', 'N/A')}")
    print(f"Department: {student.get('department', 'N/A')}")
    print(f"Year: {student.get('year', 'N/A')}")
    print(f"Phone: {student.get('phone', 'N/A')}")
    print(f"Image Path: {student.get('image_path', 'N/A')}")
    print("-" * 80)
