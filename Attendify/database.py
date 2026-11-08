"""
Database module for Attendify - SQLite implementation
Handles all database operations for students, courses, and attendance
"""

import sqlite3
import json
import pickle
import os
from datetime import datetime
import numpy as np


class AttendifyDatabase:
    def __init__(self, db_path='./attendify_db/attendify.db'):
        """Initialize database connection and create tables"""
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()
        
        self.create_tables()
        
    def create_tables(self):
        """Create all necessary tables"""
        
        # Students table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                department TEXT,
                year TEXT,
                phone TEXT,
                face_encoding BLOB NOT NULL,
                image_path TEXT,
                registration_date TEXT,
                anti_spoofing_verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Courses table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                instructor TEXT,
                schedule TEXT,
                room TEXT,
                semester TEXT,
                year TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Attendance table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT DEFAULT 'Present',
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (course_id) REFERENCES courses(course_id),
                UNIQUE(student_id, course_id, date)
            )
        ''')
        
        # Create indexes for better performance
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_attendance_date 
            ON attendance(date)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_attendance_course 
            ON attendance(course_id)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_attendance_student 
            ON attendance(student_id)
        ''')
        
        self.conn.commit()
    
    # ==================== STUDENT OPERATIONS ====================
    
    def add_student(self, student_data):
        """Add a new student to the database"""
        try:
            # Convert face encoding to binary
            face_encoding = np.array(student_data['face_encoding'])
            face_encoding_blob = pickle.dumps(face_encoding)
            
            self.cursor.execute('''
                INSERT INTO students 
                (student_id, name, email, department, year, phone, 
                 face_encoding, image_path, registration_date, anti_spoofing_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                student_data['student_id'],
                student_data['name'],
                student_data.get('email', ''),
                student_data.get('department', ''),
                student_data.get('year', ''),
                student_data.get('phone', ''),
                face_encoding_blob,
                student_data.get('image_path', ''),
                student_data.get('registration_date', datetime.now().isoformat()),
                1 if student_data.get('anti_spoofing_verified', False) else 0
            ))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Student ID already exists
        except Exception as e:
            print(f"Error adding student: {e}")
            return False
    
    def get_student(self, student_id):
        """Get student by ID"""
        self.cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
        row = self.cursor.fetchone()
        
        if row:
            student_data = dict(row)
            # Convert face encoding from binary
            student_data['face_encoding'] = pickle.loads(student_data['face_encoding'])
            return student_data
        return None
    
    def get_all_students(self):
        """Get all students"""
        self.cursor.execute('SELECT * FROM students ORDER BY name')
        rows = self.cursor.fetchall()
        
        students = {}
        for row in rows:
            student_data = dict(row)
            # Convert face encoding from binary
            student_data['face_encoding'] = pickle.loads(student_data['face_encoding'])
            students[student_data['student_id']] = student_data
        
        return students
    
    def update_student(self, student_id, student_data):
        """Update student information"""
        try:
            # Convert face encoding to binary if present
            if 'face_encoding' in student_data:
                face_encoding = np.array(student_data['face_encoding'])
                face_encoding_blob = pickle.dumps(face_encoding)
            else:
                face_encoding_blob = None
            
            if face_encoding_blob:
                self.cursor.execute('''
                    UPDATE students 
                    SET name=?, email=?, department=?, year=?, phone=?, 
                        face_encoding=?, image_path=?, updated_at=CURRENT_TIMESTAMP
                    WHERE student_id=?
                ''', (
                    student_data['name'],
                    student_data.get('email', ''),
                    student_data.get('department', ''),
                    student_data.get('year', ''),
                    student_data.get('phone', ''),
                    face_encoding_blob,
                    student_data.get('image_path', ''),
                    student_id
                ))
            else:
                self.cursor.execute('''
                    UPDATE students 
                    SET name=?, email=?, department=?, year=?, phone=?, 
                        image_path=?, updated_at=CURRENT_TIMESTAMP
                    WHERE student_id=?
                ''', (
                    student_data['name'],
                    student_data.get('email', ''),
                    student_data.get('department', ''),
                    student_data.get('year', ''),
                    student_data.get('phone', ''),
                    student_data.get('image_path', ''),
                    student_id
                ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating student: {e}")
            return False
    
    def delete_student(self, student_id):
        """Delete a student"""
        try:
            self.cursor.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting student: {e}")
            return False
    
    # ==================== COURSE OPERATIONS ====================
    
    def add_course(self, course_data):
        """Add a new course"""
        try:
            self.cursor.execute('''
                INSERT INTO courses 
                (course_id, course_name, instructor, schedule, room, semester, year)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                course_data['course_id'],
                course_data['course_name'],
                course_data.get('instructor', ''),
                course_data.get('schedule', ''),
                course_data.get('room', ''),
                course_data.get('semester', ''),
                course_data.get('year', '')
            ))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Course ID already exists
        except Exception as e:
            print(f"Error adding course: {e}")
            return False
    
    def get_course(self, course_id):
        """Get course by ID"""
        self.cursor.execute('SELECT * FROM courses WHERE course_id = ?', (course_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_courses(self):
        """Get all courses"""
        self.cursor.execute('SELECT * FROM courses ORDER BY course_id')
        rows = self.cursor.fetchall()
        
        courses = {}
        for row in rows:
            course_data = dict(row)
            courses[course_data['course_id']] = course_data
        
        return courses
    
    def update_course(self, course_id, course_data):
        """Update course information"""
        try:
            self.cursor.execute('''
                UPDATE courses 
                SET course_name=?, instructor=?, schedule=?, room=?, 
                    semester=?, year=?, updated_at=CURRENT_TIMESTAMP
                WHERE course_id=?
            ''', (
                course_data['course_name'],
                course_data.get('instructor', ''),
                course_data.get('schedule', ''),
                course_data.get('room', ''),
                course_data.get('semester', ''),
                course_data.get('year', ''),
                course_id
            ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating course: {e}")
            return False
    
    def delete_course(self, course_id):
        """Delete a course"""
        try:
            self.cursor.execute('DELETE FROM courses WHERE course_id = ?', (course_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting course: {e}")
            return False
    
    # ==================== ATTENDANCE OPERATIONS ====================
    
    def mark_attendance(self, student_id, course_id, date, time, status='Present', confidence=None):
        """Mark attendance for a student"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO attendance 
                (student_id, course_id, date, time, status, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, course_id, date, time, status, confidence))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error marking attendance: {e}")
            return False
    
    def get_attendance_by_date(self, course_id, date):
        """Get attendance for a specific course and date"""
        self.cursor.execute('''
            SELECT a.*, s.name, s.email, s.department
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.course_id = ? AND a.date = ?
            ORDER BY a.time
        ''', (course_id, date))
        
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_attendance_by_student(self, student_id, course_id=None):
        """Get attendance history for a student"""
        if course_id:
            self.cursor.execute('''
                SELECT * FROM attendance 
                WHERE student_id = ? AND course_id = ?
                ORDER BY date DESC, time DESC
            ''', (student_id, course_id))
        else:
            self.cursor.execute('''
                SELECT * FROM attendance 
                WHERE student_id = ?
                ORDER BY date DESC, time DESC
            ''', (student_id,))
        
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_attendance_report(self, course_id, start_date, end_date):
        """Generate attendance report for a course within date range"""
        self.cursor.execute('''
            SELECT 
                s.student_id,
                s.name,
                s.email,
                s.department,
                COUNT(a.id) as total_present,
                GROUP_CONCAT(a.date || ' ' || a.time) as attendance_dates
            FROM students s
            LEFT JOIN attendance a ON s.student_id = a.student_id 
                AND a.course_id = ? 
                AND a.date BETWEEN ? AND ?
            GROUP BY s.student_id
            ORDER BY s.name
        ''', (course_id, start_date, end_date))
        
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def check_attendance_exists(self, student_id, course_id, date):
        """Check if attendance already marked for today"""
        self.cursor.execute('''
            SELECT id FROM attendance 
            WHERE student_id = ? AND course_id = ? AND date = ?
        ''', (student_id, course_id, date))
        
        return self.cursor.fetchone() is not None
    
    # ==================== UTILITY OPERATIONS ====================
    
    def close(self):
        """Close database connection"""
        self.conn.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.conn.close()
        except:
            pass
