"""
Migration script to convert existing JSON/pickle data to SQLite database
Run this once to migrate your existing data
"""

import os
import json
import pickle
from database import AttendifyDatabase
import csv
from datetime import datetime


def migrate_students(db):
    """Migrate students from JSON/pickle files to SQL"""
    students_dir = "./attendify_db/students"
    migrated = 0
    
    if not os.path.exists(students_dir):
        print("No students directory found")
        return 0
    
    print("\nMigrating students...")
    for filename in os.listdir(students_dir):
        if filename.endswith('.json'):
            student_id = filename[:-5]
            
            try:
                # Load JSON data
                with open(os.path.join(students_dir, filename), 'r') as f:
                    student_data = json.load(f)
                
                # Load face encoding from pickle file
                encoding_file = f"./attendify_db/students/{student_id}.pickle"
                if os.path.exists(encoding_file):
                    with open(encoding_file, 'rb') as f:
                        face_encoding = pickle.load(f)
                        student_data['face_encoding'] = face_encoding.tolist()
                else:
                    print(f"  Warning: No face encoding found for {student_id}")
                    continue
                
                # Add to database
                if db.add_student(student_data):
                    migrated += 1
                    print(f"  ✓ Migrated student: {student_id} - {student_data.get('name', 'Unknown')}")
                else:
                    print(f"  ✗ Failed to migrate student: {student_id}")
                    
            except Exception as e:
                print(f"  ✗ Error migrating student {student_id}: {e}")
    
    return migrated


def migrate_courses(db):
    """Migrate courses from JSON files to SQL"""
    courses_dir = "./attendify_db/courses"
    migrated = 0
    
    if not os.path.exists(courses_dir):
        print("No courses directory found")
        return 0
    
    print("\nMigrating courses...")
    for filename in os.listdir(courses_dir):
        if filename.endswith('.json'):
            course_id = filename[:-5]
            
            try:
                # Load JSON data
                with open(os.path.join(courses_dir, filename), 'r') as f:
                    course_data = json.load(f)
                
                # Add to database
                if db.add_course(course_data):
                    migrated += 1
                    print(f"  ✓ Migrated course: {course_id} - {course_data.get('course_name', 'Unknown')}")
                else:
                    print(f"  ✗ Failed to migrate course: {course_id}")
                    
            except Exception as e:
                print(f"  ✗ Error migrating course {course_id}: {e}")
    
    return migrated


def migrate_attendance(db):
    """Migrate attendance from CSV files to SQL"""
    attendance_dir = "./attendify_db/attendance"
    migrated = 0
    
    if not os.path.exists(attendance_dir):
        print("No attendance directory found")
        return 0
    
    print("\nMigrating attendance records...")
    for filename in os.listdir(attendance_dir):
        if filename.endswith('.csv'):
            try:
                # Parse filename: COURSEID_YYYY-MM-DD.csv
                parts = filename[:-4].split('_')
                if len(parts) >= 2:
                    course_id = '_'.join(parts[:-1])
                    date = parts[-1]
                else:
                    print(f"  Warning: Skipping invalid filename: {filename}")
                    continue
                
                # Read CSV file
                filepath = os.path.join(attendance_dir, filename)
                with open(filepath, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        student_id = row.get('Student ID', row.get('student_id', ''))
                        time = row.get('Time', row.get('time', ''))
                        status = row.get('Status', row.get('status', 'Present'))
                        
                        if student_id and time:
                            if db.mark_attendance(student_id, course_id, date, time, status):
                                migrated += 1
                
                print(f"  ✓ Migrated attendance from: {filename}")
                
            except Exception as e:
                print(f"  ✗ Error migrating attendance from {filename}: {e}")
    
    return migrated


def main():
    """Main migration function"""
    print("="*60)
    print("Attendify Database Migration Tool")
    print("Converting JSON/pickle/CSV data to SQLite")
    print("="*60)
    
    # Check if database already exists
    db_path = './attendify_db/attendify.db'
    if os.path.exists(db_path):
        response = input(f"\nDatabase already exists at {db_path}. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return
        os.remove(db_path)
        print("Existing database removed.")
    
    # Create database
    print("\nCreating new database...")
    db = AttendifyDatabase(db_path)
    print("✓ Database created successfully")
    
    # Migrate data
    students_count = migrate_students(db)
    courses_count = migrate_courses(db)
    attendance_count = migrate_attendance(db)
    
    # Summary
    print("\n" + "="*60)
    print("Migration Summary:")
    print(f"  Students migrated:   {students_count}")
    print(f"  Courses migrated:    {courses_count}")
    print(f"  Attendance records:  {attendance_count}")
    print("="*60)
    
    if students_count > 0 or courses_count > 0:
        print("\n✓ Migration completed successfully!")
        print(f"\nDatabase location: {db_path}")
        print("\nYou can now use the SQL-based Attendify application.")
        print("Your original files are still intact as backup.")
    else:
        print("\n⚠ No data was migrated. Check if data files exist.")
    
    db.close()


if __name__ == "__main__":
    main()
