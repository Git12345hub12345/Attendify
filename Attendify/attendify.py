import os
import datetime
import pickle
import json
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import face_recognition
import pandas as pd
import sys
import importlib.util
import numpy as np
from database import AttendifyDatabase
from modern_theme import ModernTheme, StyledButton, StyledFrame, StyleUtils

# Import anti-spoofing functionality (optional)
ANTI_SPOOFING_AVAILABLE = False
test_spoofing = None

try:
    silent_face_path = os.path.join(os.getcwd(), 'Silent-Face-Anti-Spoofing')
    if os.path.exists(silent_face_path):
        sys.path.insert(0, silent_face_path)
        
        spec = importlib.util.spec_from_file_location("anti_spoof_test", 
                                                     os.path.join(silent_face_path, "test.py"))
        anti_spoof_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(anti_spoof_module)
        test_spoofing = anti_spoof_module.test
        ANTI_SPOOFING_AVAILABLE = True
        print("Anti-spoofing module loaded successfully")
    else:
        print("Silent-Face-Anti-Spoofing directory not found")
except Exception as e:
    print(f"Anti-spoofing module not available: {e}")
    ANTI_SPOOFING_AVAILABLE = False
    test_spoofing = None


class AttendifyWithAntiSpoofing:
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.title("Attendify - Smart Attendance with Anti-Spoofing")
    
    # Make window full screen
        self.main_window.state('zoomed')  # For Windows
    # Alternative for cross-platform: self.main_window.attributes('-fullscreen', True)
    
        self.main_window.configure(bg=ModernTheme.BACKGROUND)
    
    # Initialize directories
        self.setup_directories()
    
    # Initialize SQL database
        self.db = AttendifyDatabase('./attendify_db/attendify.db')
    
    # Initialize data structures (loaded from database)
        self.students_db = {}
        self.courses_db = {}
        self.current_course = None
    
    # Initialize webcam
        self.cap = None
        self.webcam_active = False
        self.selected_camera_index = 0
        self.available_cameras = []
        self.most_recent_capture_arr = None
    
    # Anti-spoofing is always enabled if available
        self.anti_spoofing_enabled = ANTI_SPOOFING_AVAILABLE
        self.model_dir = './Silent-Face-Anti-Spoofing/resources/anti_spoof_models'
    
    # Automatic attendance marking
        self.auto_attendance_enabled = False
        self.last_attendance_time = {}  # Track last attendance time per student to avoid duplicates
        self.attendance_cooldown = 10  # Seconds between automatic attendance marks for same student
    
    # Setup GUI
        self.setup_gui()
    
    # Load existing data
        self.load_data()
        
    def setup_directories(self):
        """Create necessary directories"""
        directories = [
            './attendify_db/students',
            './attendify_db/courses', 
            './attendify_db/attendance',
            './attendify_db/reports',
            './attendify_db/student_images'
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
    def detect_cameras(self):
        """Detect available cameras with optimized checking"""
        available = []
        max_cameras_to_check = 3
        
        for i in range(max_cameras_to_check):
            try:
                # Use CAP_DSHOW on Windows for faster detection
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        available.append(i)
                    cap.release()
            except:
                continue
        
        return available if available else [0]
    
    def initialize_cameras(self):
        """Initialize camera list after GUI is ready"""
        try:
            self.available_cameras = self.detect_cameras()
            camera_options = [f"Camera {i}" for i in self.available_cameras]
            self.camera_dropdown['values'] = camera_options
            if camera_options:
                self.camera_var.set(camera_options[0])
            self.update_status(f"Detected {len(self.available_cameras)} camera(s)")
        except Exception as e:
            self.update_status(f"Camera detection error: {str(e)}")
                
    def setup_gui(self):
        """Setup the main GUI interface"""
        self.create_header()
        self.create_left_panel()
        self.create_center_panel()
        self.create_right_panel()
        
        # Initialize webcam label with placeholder
        self.webcam_label.configure(text="Camera Preview\n640×480 (4:3)\nClick 'Start Camera'", 
                                   fg='white', font=('Arial', 11))
        
        # Detect cameras after GUI is created
        self.main_window.after(500, self.initialize_cameras)
        
    def create_header(self):
        """Create modern header with enhanced styling"""
        # Main header frame with primary color
        header_frame = StyledFrame(self.main_window, bg=ModernTheme.PRIMARY)
        header_frame.pack(fill='x', padx=0, pady=0)
        
        # Inner container for content
        header_content = tk.Frame(header_frame, bg=ModernTheme.PRIMARY)
        header_content.pack(fill='x', padx=ModernTheme.PADDING_LARGE, 
                           pady=ModernTheme.PADDING_LARGE)
        
        # Title with modern typography
        title_text = "Attendify"
        if not self.anti_spoofing_enabled:
            title_text += " (Anti-Spoofing Disabled)"
        
        title_label = tk.Label(
            header_content,
            text=title_text,
            font=ModernTheme.FONT_TITLE,
            fg="white",
            bg=ModernTheme.PRIMARY
        )
        title_label.pack(side='left')
        
        # Subtitle
        subtitle = tk.Label(
            header_content,
            text="Smart Attendance System",
            font=ModernTheme.FONT_BODY,
            fg="white",
            bg=ModernTheme.PRIMARY
        )
        subtitle.pack(side='left', padx=(ModernTheme.PADDING_MEDIUM, 0))
        
    def create_left_panel(self):
        """Create modern left panel with styled controls"""
        # Main panel with background color
        left_frame = StyledFrame(
            self.main_window,
            bg=ModernTheme.BACKGROUND,
            width=280
        )
        left_frame.pack(side='left', fill='y', padx=ModernTheme.PADDING_MEDIUM, 
                       pady=ModernTheme.PADDING_MEDIUM)
        left_frame.pack_propagate(False)
        
        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(left_frame, bg=ModernTheme.BACKGROUND, highlightthickness=0)
        scrollbar = tk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=ModernTheme.BACKGROUND)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Course Management Section
        course_card = StyleUtils.create_card(scrollable_frame, title="Course Management")
        course_card.pack(fill='x', pady=(0, ModernTheme.PADDING_SMALL))
        
        # Course selection
        course_inner = tk.Frame(course_card, bg=ModernTheme.SURFACE)
        course_inner.pack(fill='x', padx=ModernTheme.PADDING_SMALL, 
                         pady=ModernTheme.PADDING_SMALL)
        
        tk.Label(course_inner, text="Select Course:", 
                font=ModernTheme.FONT_BODY, bg=ModernTheme.SURFACE).pack(anchor='w', pady=(0, 3))
        
        self.course_var = tk.StringVar()
        self.course_combo = ttk.Combobox(course_inner, textvariable=self.course_var, width=25)
        self.course_combo.pack(fill='x', pady=(0, ModernTheme.PADDING_SMALL))
        self.course_combo.bind('<<ComboboxSelected>>', self.on_course_select)
        
        # Styled buttons
        StyledButton(course_inner, text="Add New Course", 
                    command=self.add_course, style="primary", width=20).pack(fill='x', pady=2)
        
        StyledButton(course_inner, text="Edit Course", 
                    command=self.edit_course, style="neutral", width=20).pack(fill='x', pady=2)
        
        # Student Management Section
        student_card = StyleUtils.create_card(scrollable_frame, title="Student Management")
        student_card.pack(fill='x', pady=(0, ModernTheme.PADDING_SMALL))
        
        student_inner = tk.Frame(student_card, bg=ModernTheme.SURFACE)
        student_inner.pack(fill='x', padx=ModernTheme.PADDING_SMALL, 
                          pady=ModernTheme.PADDING_SMALL)
        
        StyledButton(student_inner, text="Register Student", 
                    command=self.register_student, style="secondary", width=20).pack(fill='x', pady=2)
        
        StyledButton(student_inner, text="View Students", 
                    command=self.view_students, style="neutral", width=20).pack(fill='x', pady=2)
        
        StyledButton(student_inner, text="Edit Student Details", 
                    command=self.open_edit_student_selection, 
                    style="neutral", width=20).pack(fill='x', pady=2)
        
        # Attendance Section
        attendance_card = StyleUtils.create_card(scrollable_frame, title="Attendance")
        attendance_card.pack(fill='x', pady=(0, ModernTheme.PADDING_SMALL))
        
        attendance_inner = tk.Frame(attendance_card, bg=ModernTheme.SURFACE)
        attendance_inner.pack(fill='x', padx=ModernTheme.PADDING_SMALL, 
                             pady=ModernTheme.PADDING_SMALL)
        
        # Current course indicator
        self.current_course_label = tk.Label(
            attendance_inner,
            text="No course selected",
            font=ModernTheme.FONT_BODY,
            bg=ModernTheme.SURFACE,
            fg=ModernTheme.ACCENT
        )
        self.current_course_label.pack(pady=(0, 3))
        
        # Auto attendance toggle
        self.auto_attendance_btn = StyledButton(
            attendance_inner,
            text="Enable Auto Attendance",
            command=self.toggle_auto_attendance,
            style="primary",
            width=20
        )
        self.auto_attendance_btn.pack(fill='x', pady=2)
        
        # Manual attendance button
        self.mark_attendance_btn = StyledButton(
            attendance_inner,
            text="Mark Attendance",
            command=self.mark_attendance,
            style="secondary",
            width=20
        )
        self.mark_attendance_btn.pack(fill='x', pady=2)
        
        # Repair button
        StyledButton(attendance_inner, text="Repair Data Files", 
                    command=self.repair_attendance_files,
                    style="danger", width=20).pack(fill='x', pady=2)
        
        # Reports Section
        reports_card = StyleUtils.create_card(scrollable_frame, title="Reports")
        reports_card.pack(fill='x', pady=(0, ModernTheme.PADDING_SMALL))
        
        reports_inner = tk.Frame(reports_card, bg=ModernTheme.SURFACE)
        reports_inner.pack(fill='x', padx=ModernTheme.PADDING_SMALL, 
                          pady=ModernTheme.PADDING_SMALL)
        
        StyledButton(reports_inner, text="Generate Report", 
                    command=self.generate_report, style="neutral", width=20).pack(fill='x', pady=2)
        
        StyledButton(reports_inner, text="Export Data", 
                    command=self.export_data, style="neutral", width=20).pack(fill='x', pady=2)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
    def create_center_panel(self):
        """Create modern center panel with enhanced camera display"""
        center_frame = StyledFrame(self.main_window, bg=ModernTheme.BACKGROUND)
        center_frame.pack(side='left', fill='both', expand=True, 
                         padx=ModernTheme.PADDING_MEDIUM)
        
        # Camera section header
        header = StyleUtils.create_section_header(center_frame, "Camera Feed")
        header.pack(pady=(ModernTheme.PADDING_MEDIUM, ModernTheme.PADDING_SMALL))
        
        # Camera container with elevated card style
        camera_card = StyledFrame(center_frame, elevated=True, bg=ModernTheme.SURFACE)
        camera_card.pack(pady=ModernTheme.PADDING_MEDIUM)
        
        # Camera display area
        camera_container = tk.Frame(camera_card, bg='black', width=640, height=480)
        camera_container.pack(padx=ModernTheme.PADDING_MEDIUM, 
                             pady=ModernTheme.PADDING_MEDIUM)
        camera_container.pack_propagate(False)
        
        self.webcam_label = tk.Label(camera_container, bg='black')
        self.webcam_label.place(x=0, y=0, width=640, height=480)
        
        # Camera controls in a styled container
        controls_card = StyledFrame(center_frame, elevated=True, bg=ModernTheme.SURFACE)
        controls_card.pack(pady=ModernTheme.PADDING_MEDIUM)
        
        controls_inner = tk.Frame(controls_card, bg=ModernTheme.SURFACE)
        controls_inner.pack(padx=ModernTheme.PADDING_LARGE, 
                           pady=ModernTheme.PADDING_MEDIUM)
        
        # Camera selection
        tk.Label(controls_inner, text="Camera:", 
                font=ModernTheme.FONT_BUTTON, 
                bg=ModernTheme.SURFACE).pack(side='left', padx=(0, 5))
        
        self.camera_var = tk.StringVar(value="Camera 0")
        self.camera_dropdown = ttk.Combobox(
            controls_inner,
            textvariable=self.camera_var,
            values=["Detecting cameras..."],
            state='readonly',
            width=15
        )
        self.camera_dropdown.pack(side='left', padx=5)
        self.camera_dropdown.bind('<<ComboboxSelected>>', self.on_camera_change)
        
        # Camera control buttons
        self.start_camera_btn = StyledButton(
            controls_inner,
            text="Start Camera",
            command=self.start_camera,
            style="secondary"
        )
        self.start_camera_btn.pack(side='left', padx=5)
        
        self.stop_camera_btn = StyledButton(
            controls_inner,
            text="Stop Camera",
            command=self.stop_camera,
            style="danger",
            state='disabled'
        )
        self.stop_camera_btn.pack(side='left', padx=5)
        
        # Camera status badge
        self.camera_status_label = StyleUtils.create_status_badge(
            center_frame,
            "Camera: Stopped",
            "error"
        )
        self.camera_status_label.pack(pady=ModernTheme.PADDING_MEDIUM)
        
    def create_right_panel(self):
        """Create modern right panel with improved status display"""
        right_frame = StyledFrame(
            self.main_window,
            bg=ModernTheme.BACKGROUND,
            width=280
        )
        right_frame.pack(side='right', fill='y', 
                        padx=ModernTheme.PADDING_MEDIUM, 
                        pady=ModernTheme.PADDING_MEDIUM)
        right_frame.pack_propagate(False)
        
        # Status card
        status_card = StyleUtils.create_card(right_frame, title="System Status")
        status_card.pack(fill='both', expand=True)
        
        # Status text area with modern styling
        status_inner = tk.Frame(status_card, bg=ModernTheme.SURFACE)
        status_inner.pack(fill='both', expand=True, 
                         padx=ModernTheme.PADDING_MEDIUM, 
                         pady=ModernTheme.PADDING_MEDIUM)
        
        self.status_text = tk.Text(
            status_inner,
            wrap='word',
            font=ModernTheme.FONT_BODY,
            bg=ModernTheme.SURFACE,
            fg=ModernTheme.TEXT_PRIMARY,
            relief='flat',
            borderwidth=0
        )
        self.status_text.pack(fill='both', expand=True)
        
        # Clear button
        StyledButton(
            status_inner,
            text="Clear Status",
            command=self.clear_status,
            style="neutral",
            width=15
        ).pack(fill='x', pady=(ModernTheme.PADDING_MEDIUM, 0))
        
        # Initial status message
        status_msg = ("Attendify initialized with Anti-Spoofing protection." 
                     if self.anti_spoofing_enabled 
                     else "Attendify initialized. Anti-spoofing disabled.")
        self.update_status(status_msg)
        
    def start_camera(self):
        """Start webcam"""
        if not self.webcam_active:
            try:
                # Release any existing camera
                if self.cap:
                    self.cap.release()
                
                # Try to open the selected camera
                self.cap = cv2.VideoCapture(self.selected_camera_index, cv2.CAP_DSHOW)
                
                if self.cap.isOpened():
                    # Set camera properties
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    
                    # Test if camera actually works
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None and test_frame.size > 0:
                        self.webcam_active = True
                        self.update_status(f"Camera {self.selected_camera_index} started")
                        self.camera_status_label.configure(text=f"Camera {self.selected_camera_index}: Active", 
                                                          bg=ModernTheme.SUCCESS)
                        self.start_camera_btn.configure(state='disabled')
                        self.stop_camera_btn.configure(state='normal')
                        self.camera_dropdown.configure(state='disabled')
                        
                        # Clear the label text
                        self.webcam_label.configure(text="")
                        
                        # Start processing
                        self.process_webcam()
                        return
                    else:
                        self.cap.release()
                        self.cap = None
                        self.update_status(f"Error: Camera {self.selected_camera_index} not responding")
                        messagebox.showerror("Camera Error", f"Camera {self.selected_camera_index} is not responding.")
                else:
                    self.update_status(f"Error: Could not open Camera {self.selected_camera_index}")
                    messagebox.showerror("Camera Error", f"Could not open Camera {self.selected_camera_index}.")
                    
            except Exception as e:
                self.update_status(f"Camera error: {str(e)}")
                messagebox.showerror("Camera Error", f"Camera initialization failed: {str(e)}")
                
    def stop_camera(self):
        """Stop webcam"""
        self.webcam_active = False
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Clear the image and show placeholder text
        self.webcam_label.configure(image='', bg='black')
        self.webcam_label.configure(text="Camera Stopped\n640×480 Preview\nClick 'Start Camera'", 
                                   fg='white', font=ModernTheme.FONT_BODY)
        
        self.update_status("Camera stopped")
        self.camera_status_label.configure(text="Camera: Stopped", bg=ModernTheme.ERROR)
        self.start_camera_btn.configure(state='normal')
        self.stop_camera_btn.configure(state='disabled')
        self.camera_dropdown.configure(state='readonly')
        
        # Clear the image reference to prevent memory issues
        if hasattr(self.webcam_label, 'imgtk'):
            delattr(self.webcam_label, 'imgtk')
            
    def process_webcam(self):
        """Process webcam frames with 480x360 display and automatic attendance"""
        if self.webcam_active and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    self.most_recent_capture_arr = frame.copy()
                    
                    # Automatic attendance marking if enabled
                    if self.auto_attendance_enabled and self.current_course:
                        self.auto_mark_attendance(frame)
                    
                    # Convert and resize to 480x360
                    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(img_rgb)
                    img_pil = img_pil.resize((640, 480), Image.Resampling.LANCZOS)
                    
                    imgtk = ImageTk.PhotoImage(image=img_pil)
                    
                    # Keep a reference to prevent garbage collection
                    self.webcam_label.imgtk = imgtk
                    self.webcam_label.configure(image=imgtk, text="")
                    
            except Exception as e:
                self.update_status(f"Frame processing error: {str(e)}")
                
            # Schedule next update
            self.main_window.after(30, self.process_webcam)
    
    def on_camera_change(self, event=None):
        """Handle camera selection change"""
        selected = self.camera_var.get()
        try:
            self.selected_camera_index = int(selected.split()[-1])
            self.update_status(f"Camera {self.selected_camera_index} selected")
        except:
            self.selected_camera_index = 0
    
    def toggle_auto_attendance(self):
        """Toggle automatic attendance marking on/off"""
        self.auto_attendance_enabled = not self.auto_attendance_enabled
        
        if self.auto_attendance_enabled:
            self.auto_attendance_btn.configure(text="Disable Auto Attendance")
            self.auto_attendance_btn.normal_bg = ModernTheme.ACCENT
            self.auto_attendance_btn.hover_bg = "#d33b2c"
            self.auto_attendance_btn.configure(bg=ModernTheme.ACCENT)
            self.update_status("Auto attendance enabled - faces will be detected automatically")
            # Clear the cooldown tracker when enabling
            self.last_attendance_time = {}
        else:
            self.auto_attendance_btn.configure(text="Enable Auto Attendance")
            self.auto_attendance_btn.normal_bg = ModernTheme.PRIMARY
            self.auto_attendance_btn.hover_bg = ModernTheme.PRIMARY_DARK
            self.auto_attendance_btn.configure(bg=ModernTheme.PRIMARY)
            self.update_status("Auto attendance disabled")
    
    def auto_mark_attendance(self, frame):
        """Automatically detect and mark attendance from camera frame"""
        try:
            import time
            
            # Anti-spoofing check if enabled
            if self.anti_spoofing_enabled:
                try:
                    if test_spoofing:
                        spoof_label = test_spoofing(
                            image=frame,
                            model_dir=self.model_dir,
                            device_id=0
                        )
                        
                        if spoof_label != 1:
                            # Spoof detected - skip this frame silently
                            return
                except Exception:
                    # If anti-spoofing fails, continue without it
                    pass
            
            # Face recognition
            face_encodings = face_recognition.face_encodings(frame)
            
            if len(face_encodings) == 0:
                # No face detected - skip silently
                return
                
            if len(face_encodings) > 1:
                # Multiple faces - skip silently
                return
                
            # Compare with registered students
            current_encoding = face_encodings[0]
            best_match = None
            best_distance = float('inf')
            best_student_id = None
            
            for student_id, student_data in self.students_db.items():
                if 'face_encoding' in student_data and student_data['face_encoding'] is not None:
                    # Convert stored encoding to numpy array if it's a list
                    if isinstance(student_data['face_encoding'], list):
                        stored_encoding = np.array(student_data['face_encoding'])
                    else:
                        stored_encoding = student_data['face_encoding']
                        
                    distance = face_recognition.face_distance([stored_encoding], current_encoding)[0]
                    
                    # Use a stricter threshold for better accuracy
                    if distance < 0.5 and distance < best_distance:
                        best_distance = distance
                        best_match = student_data
                        best_student_id = student_id
                        
            if best_match and best_student_id:
                student_id = best_student_id
                current_time = time.time()
                
                # Check cooldown - don't mark attendance if recently marked
                if student_id in self.last_attendance_time:
                    time_since_last = current_time - self.last_attendance_time[student_id]
                    if time_since_last < self.attendance_cooldown:
                        # Still in cooldown period
                        return
                
                # Use the correct student data from database
                student_data = self.students_db[student_id]
                
                # Mark attendance
                status = self.record_attendance(student_data)
                
                if status is not None:  # Successfully marked (not already marked today)
                    # Update last attendance time
                    self.last_attendance_time[student_id] = current_time
                    
                    security_msg = " (Anti-Spoofing Verified)" if self.anti_spoofing_enabled else ""
                    self.update_status(f"✓ Auto-marked: {student_data['name']} - {status}{security_msg}")
                    
        except Exception as e:
            # Silently handle errors in auto attendance to not disrupt camera feed
            pass
            
    def mark_attendance(self):
        """Mark attendance with anti-spoofing protection"""
        if not self.current_course:
            messagebox.showwarning("Warning", "Please select a course first.")
            return
            
        if not self.webcam_active:
            messagebox.showwarning("Warning", "Please start the camera first.")
            return
            
        if self.most_recent_capture_arr is None:
            messagebox.showwarning("Warning", "No camera feed available.")
            return
            
        try:
            # Anti-spoofing check if enabled
            if self.anti_spoofing_enabled:
                self.update_status("Checking for spoofing...")
                
                try:
                    if test_spoofing:
                        frame = self.most_recent_capture_arr.copy()
                        spoof_label = test_spoofing(
                            image=frame,
                            model_dir=self.model_dir,
                            device_id=0
                        )
                        
                        if spoof_label != 1:
                            self.update_status("SPOOFING DETECTED! Fake face rejected.")
                            messagebox.showerror("Security Alert", "SPOOFING DETECTED!\n\nFake face detected!")
                            return
                            
                        self.update_status("Real face verified. Processing attendance...")
                except Exception as spoof_error:
                    self.update_status(f"Anti-spoofing error: {str(spoof_error)}")
                    # Continue without anti-spoofing if there's an error
                    self.update_status("Proceeding without anti-spoofing verification...")
            else:
                self.update_status("Processing without anti-spoofing check...")
            
            # Face recognition
            frame = self.most_recent_capture_arr
            face_encodings = face_recognition.face_encodings(frame)
            
            if len(face_encodings) == 0:
                self.update_status("No face detected.")
                messagebox.showwarning("Warning", "No face detected. Please position face clearly.")
                return
                
            if len(face_encodings) > 1:
                self.update_status("Multiple faces detected.")
                messagebox.showwarning("Warning", "Multiple faces detected. Please ensure only one person is in frame.")
                return
                
            # Compare with registered students
            current_encoding = face_encodings[0]
            best_match = None
            best_distance = float('inf')
            
            for student_id, student_data in self.students_db.items():
                if 'face_encoding' in student_data:
                    stored_encoding = np.array(student_data['face_encoding'])
                    distance = face_recognition.face_distance([stored_encoding], current_encoding)[0]
                    
                    if distance < 0.6 and distance < best_distance:
                        best_distance = distance
                        best_match = student_data
                        
            if best_match:
                status = self.record_attendance(best_match)
                security_msg = " (Verified with Anti-Spoofing)" if self.anti_spoofing_enabled else ""
                status_msg = f"\nStatus: {status}" if status else ""
                self.update_status(f"Attendance marked for {best_match['name']}{security_msg} - {status if status else 'Present'}")
                messagebox.showinfo("Success", f"Attendance Marked!\n\nStudent: {best_match['name']}\nID: {best_match['student_id']}{status_msg}{security_msg}")
            else:
                self.update_status("Student not recognized.")
                messagebox.showwarning("Warning", "Student not recognized. Please register first.")
                
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Attendance marking failed: {str(e)}")
            
    def register_student(self):
        """Register new student with anti-spoofing verification"""
        if not self.webcam_active:
            messagebox.showwarning("Warning", "Please start the camera first.")
            return
            
        dialog = SimpleStudentDialog(self.main_window, self)
        self.main_window.wait_window(dialog.dialog)
        if dialog.result:
            student_data = dialog.result
            
            try:
                student_id = student_data['student_id']
                
                # Save to SQL database
                if self.db.add_student(student_data):
                    self.students_db[student_id] = student_data
                    
                    security_msg = " with Anti-Spoofing verification" if self.anti_spoofing_enabled else ""
                    self.update_status(f"Student {student_id} - {student_data['name']} registered{security_msg}.")
                    messagebox.showinfo("Success", f"Student {student_data['name']} registered successfully{security_msg}!")
                else:
                    messagebox.showerror("Error", f"Student ID {student_id} already exists!")
                    self.update_status(f"Registration failed: Student ID already exists")
                
            except Exception as e:
                messagebox.showerror("Error", f"Registration failed: {str(e)}")
                self.update_status(f"Registration failed: {str(e)}")
                
    def add_course(self):
        """Add a new course"""
        dialog = SimpleCourseDialog(self.main_window)
        self.main_window.wait_window(dialog.dialog)
        if dialog.result:
            course_data = dialog.result
            course_id = course_data['course_id']
            
            # Save to SQL database
            if self.db.add_course(course_data):
                self.courses_db[course_id] = course_data
                self.update_course_combo()
                self.update_status(f"Course {course_id} - {course_data['course_name']} added successfully.")
            else:
                messagebox.showerror("Error", f"Course ID {course_id} already exists!")
    
    def edit_course(self):
        """Edit the currently selected course"""
        if not self.current_course:
            messagebox.showwarning("Warning", "Please select a course to edit.")
            return
        
        # Get current course data
        course_data = self.courses_db[self.current_course].copy()
        
        # Open dialog with existing data
        dialog = SimpleCourseDialog(self.main_window, edit_mode=True, course_data=course_data)
        self.main_window.wait_window(dialog.dialog)
        
        if dialog.result:
            updated_data = dialog.result
            course_id = updated_data['course_id']
            
            # If course ID changed, handle in database
            if course_id != self.current_course:
                # Add new course and delete old one
                self.db.add_course(updated_data)
                self.db.delete_course(self.current_course)
                del self.courses_db[self.current_course]
            else:
                # Update existing course
                self.db.update_course(course_id, updated_data)
            
            # Update local cache
            self.courses_db[course_id] = updated_data
            self.current_course = course_id
            self.update_course_combo()
            
            # Update the current course label
            course_name = updated_data['course_name']
            self.current_course_label.configure(text=f"Current: {course_name}", fg=ModernTheme.SUCCESS)
            
            self.update_status(f"Course {course_id} - {course_name} updated successfully.")
            
    def load_data(self):
        """Load existing data from SQL database"""
        # Load courses from database
        self.courses_db = self.db.get_all_courses()
        
        # Load students from database
        self.students_db = self.db.get_all_students()
        
        self.update_course_combo()
        
    def update_course_combo(self):
        """Update course dropdown"""
        course_list = [f"{cid} - {data['course_name']}" for cid, data in self.courses_db.items()]
        self.course_combo['values'] = course_list
        
    def on_course_select(self, event=None):
        """Handle course selection"""
        selection = self.course_var.get()
        if selection:
            course_id = selection.split(' - ')[0]
            self.current_course = course_id
            course_name = self.courses_db[course_id]['course_name']
            self.current_course_label.configure(text=f"Current: {course_name}", fg=ModernTheme.SUCCESS)
            self.update_status(f"Selected course: {course_name}")
            
    def record_attendance(self, student_data):
        """Record attendance with late detection"""
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        current_time = now.time()
        
        # Check if already marked today
        if self.db.check_attendance_exists(student_data['student_id'], self.current_course, date_str):
            messagebox.showinfo("Info", f"{student_data['name']} already marked attendance today.")
            return None
        
        # Check if student is late based on course schedule
        status = 'Present'
        course_data = self.courses_db[self.current_course]
        schedule = course_data.get('schedule', '')
        
        # Parse schedule to get start time
        if schedule:
            try:
                # Schedule format: "Mon, Wed, Fri 09:00-10:30"
                parts = schedule.split()
                if len(parts) >= 2:
                    time_range = parts[-1]
                    if '-' in time_range:
                        start_time_str = time_range.split('-')[0]
                        # Parse start time (format: HH:MM)
                        start_hour, start_min = map(int, start_time_str.split(':'))
                        course_start_time = datetime.time(start_hour, start_min)
                        
                        # Add 15 minute grace period
                        grace_period = datetime.timedelta(minutes=15)
                        late_threshold = (datetime.datetime.combine(datetime.date.today(), course_start_time) + grace_period).time()
                        
                        # Check if current time is after the late threshold
                        if current_time > late_threshold:
                            status = 'Late'
            except Exception as e:
                self.update_status(f"Could not parse schedule for late detection: {str(e)}")
        
        # Save to SQL database
        if self.db.mark_attendance(student_data['student_id'], self.current_course, date_str, time_str, status):
            self.update_status(f"Attendance marked for {student_data['name']} - Status: {status}")
            return status
        else:
            self.update_status(f"Error saving attendance")
            messagebox.showerror("Error", "Failed to save attendance")
            return None
            
    def view_students(self):
        """View all students with modern styling"""
        self.load_data()
        
        if not self.students_db:
            messagebox.showinfo("Info", "No students registered yet.")
            return
            
        students_window = tk.Toplevel(self.main_window)
        students_window.title("Registered Students")
        students_window.geometry("900x600")
        students_window.configure(bg=ModernTheme.BACKGROUND)
        
        # Main container
        main_container = StyledFrame(students_window, bg=ModernTheme.BACKGROUND)
        main_container.pack(fill='both', expand=True, padx=ModernTheme.PADDING_LARGE, 
                           pady=ModernTheme.PADDING_LARGE)
        
        # Title
        title = tk.Label(
            main_container,
            text="Registered Students",
            font=ModernTheme.FONT_TITLE,
            bg=ModernTheme.BACKGROUND,
            fg=ModernTheme.TEXT_PRIMARY
        )
        title.pack(pady=(0, ModernTheme.PADDING_LARGE))
        
        # Card for table
        table_card = StyledFrame(main_container, elevated=True, bg=ModernTheme.SURFACE)
        table_card.pack(fill='both', expand=True)
        
        # Table frame
        table_inner = tk.Frame(table_card, bg=ModernTheme.SURFACE)
        table_inner.pack(fill='both', expand=True, padx=ModernTheme.PADDING_MEDIUM, 
                        pady=ModernTheme.PADDING_MEDIUM)
        
        # Configure treeview style
        style = ttk.Style()
        style.configure("Modern.Treeview", 
                       background=ModernTheme.SURFACE,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       fieldbackground=ModernTheme.SURFACE,
                       font=ModernTheme.FONT_BODY)
        style.configure("Modern.Treeview.Heading",
                       font=ModernTheme.FONT_SUBHEADING,
                       background=ModernTheme.SURFACE_DARK,
                       foreground=ModernTheme.TEXT_PRIMARY)
        
        columns = ('ID', 'Name', 'Email', 'Program', 'Semester', 'Phone')
        tree = ttk.Treeview(table_inner, columns=columns, show='headings', 
                           height=15, style="Modern.Treeview")
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
            
        for student_id, student_data in self.students_db.items():
            tree.insert('', 'end', values=(
                student_data['student_id'],
                student_data['name'],
                student_data['email'],
                student_data['department'],
                student_data['year'],
                student_data.get('phone', 'N/A')
            ))
        
        scrollbar = ttk.Scrollbar(table_inner, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Button frame
        button_frame = tk.Frame(main_container, bg=ModernTheme.BACKGROUND)
        button_frame.pack(pady=(ModernTheme.PADDING_LARGE, 0))
        
        StyledButton(button_frame, text="Close", command=students_window.destroy,
                    style="neutral").pack()

    def open_edit_student_selection(self):
        """Open student selection dialog for editing"""
        # Reload data to ensure we have latest students
        self.load_data()
        
        if not self.students_db:
            messagebox.showinfo("Info", "No students registered yet.")
            return
        
        # Open student selection dialog
        selection_dialog = StudentSelectionDialog(self.main_window, self.db)
        self.main_window.wait_window(selection_dialog.dialog)
        
        # Check if a student was selected
        if selection_dialog.result:
            selected_student_id = selection_dialog.result
            
            # Get the student data
            student_data = self.db.get_student(selected_student_id)
            
            if student_data:
                # Open edit dialog with selected student data - PASS self as main_app
                edit_dialog = EditStudentDialog(
                    self.main_window, 
                    self.db, 
                    student_data, 
                    self.anti_spoofing_enabled,
                    main_app=self  # This is the important change
                )
                self.main_window.wait_window(edit_dialog.dialog)
                
                # If student was updated, reload local cache
                if edit_dialog.result and edit_dialog.result.get('updated'):
                    self.load_data()
                    self.update_status(f"Student {selected_student_id} profile updated successfully.")
            else:
                messagebox.showerror("Error", f"Could not find student with ID: {selected_student_id}")

    def repair_attendance_files(self):
        """Repair corrupted attendance CSV files"""
        try:
            attendance_dir = "./attendify_db/attendance"
            repaired_count = 0
            
            for filename in os.listdir(attendance_dir):
                if filename.endswith('.csv'):
                    filepath = os.path.join(attendance_dir, filename)
                    try:
                        # Try reading normally first
                        pd.read_csv(filepath)
                    except (pd.errors.ParserError, pd.errors.EmptyDataError):
                        try:
                            # Read with error handling
                            df = pd.read_csv(filepath, on_bad_lines='skip', engine='python')
                            
                            # If data is readable, save it back with consistent columns
                            if not df.empty:
                                # Check expected columns
                                expected_columns = ['student_id', 'student_name', 'course_id', 
                                                  'course_name', 'date', 'time', 'timestamp', 
                                                  'status', 'anti_spoofing']
                                
                                # Add missing columns with default values
                                for col in expected_columns:
                                    if col not in df.columns:
                                        if col == 'anti_spoofing':
                                            df[col] = False
                                        elif col == 'status':
                                            df[col] = 'Present'
                                        else:
                                            df[col] = ''
                                
                                # Reorder columns
                                df = df[expected_columns]
                                
                                # Save repaired file
                                df.to_csv(filepath, index=False)
                                repaired_count += 1
                                self.update_status(f"Repaired: {filename}")
                        except Exception as e:
                            self.update_status(f"Could not repair {filename}: {str(e)}")
            
            if repaired_count > 0:
                messagebox.showinfo("Repair Complete", 
                                  f"Successfully repaired {repaired_count} attendance file(s).")
            else:
                messagebox.showinfo("No Repair Needed", "All attendance files are in good condition.")
                
        except Exception as e:
            messagebox.showerror("Repair Error", f"Failed to repair files: {str(e)}")

    def generate_report(self):
        """Generate attendance report with spreadsheet view from SQL database"""
        if not self.current_course:
            messagebox.showwarning("Warning", "Please select a course first.")
            return
            
        # Simple report for last 7 days
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=7)
        
        try:
            # Query attendance records from database
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            # Get attendance records from database
            attendance_records = []
            current_date = start_date
            
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                records = self.db.get_attendance_by_date(self.current_course, date_str)
                attendance_records.extend(records)
                current_date += datetime.timedelta(days=1)
            
            if not attendance_records:
                messagebox.showinfo("Info", "No attendance records found for the last 7 days.")
                return
            
            # Convert to DataFrame for display
            df_data = []
            for record in attendance_records:
                df_data.append({
                    'student_id': record['student_id'],
                    'student_name': record['name'],
                    'date': record['date'],
                    'time': record['time'],
                    'status': record['status'],
                    'anti_spoofing': False  # Not stored in current schema
                })
            
            combined_df = pd.DataFrame(df_data)
            
            # Save report to CSV
            report_file = f"./attendify_db/reports/{self.current_course}_report_{datetime.date.today().strftime('%Y%m%d')}.csv"
            combined_df.to_csv(report_file, index=False)
            
            unique_students = combined_df['student_id'].nunique()
            total_attendances = len(combined_df)
            anti_spoofing_count = 0  # Not tracked in current schema
            
            # Count status types
            present_count = len(combined_df[combined_df['status'] == 'Present'])
            late_count = len(combined_df[combined_df['status'] == 'Late'])
            
            # Show spreadsheet view
            self.show_report_spreadsheet(combined_df, unique_students, total_attendances, 
                                        anti_spoofing_count, present_count, late_count, report_file)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
            print(f"Report generation error: {e}")
    
    def show_report_spreadsheet(self, df, unique_students, total_attendances, 
                                anti_spoofing_count, present_count, late_count, report_file):
        """Display attendance report in a modern spreadsheet view"""
        report_window = tk.Toplevel(self.main_window)
        report_window.title(f"Attendance Report - {self.courses_db[self.current_course]['course_name']}")
        report_window.geometry("1100x700")
        report_window.configure(bg=ModernTheme.BACKGROUND)
        
        # Main container
        main_container = StyledFrame(report_window, bg=ModernTheme.BACKGROUND)
        main_container.pack(fill='both', expand=True, padx=ModernTheme.PADDING_LARGE, 
                           pady=ModernTheme.PADDING_LARGE)
        
        # Title
        title = tk.Label(
            main_container,
            text=f"Attendance Report - {self.courses_db[self.current_course]['course_name']}",
            font=ModernTheme.FONT_TITLE,
            bg=ModernTheme.BACKGROUND,
            fg=ModernTheme.TEXT_PRIMARY
        )
        title.pack(pady=(0, ModernTheme.PADDING_LARGE))
        
        # Summary card
        summary_card = StyledFrame(main_container, elevated=True, bg=ModernTheme.SURFACE)
        summary_card.pack(fill='x', pady=(0, ModernTheme.PADDING_MEDIUM))
        
        summary_inner = tk.Frame(summary_card, bg=ModernTheme.SURFACE)
        summary_inner.pack(fill='x', padx=ModernTheme.PADDING_LARGE, 
                          pady=ModernTheme.PADDING_MEDIUM)
        
        tk.Label(summary_inner, text="Report Summary", font=ModernTheme.FONT_HEADING, 
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(pady=(0, ModernTheme.PADDING_SMALL))
        
        summary_grid = tk.Frame(summary_inner, bg=ModernTheme.SURFACE)
        summary_grid.pack()
        
        # Create summary grid
        summary_data = [
            ("Course:", self.courses_db[self.current_course]['course_name']),
            ("Period:", "Last 7 days"),
            ("Unique Students:", str(unique_students)),
            ("Total Attendances:", str(total_attendances)),
            ("Present:", str(present_count)),
            ("Late:", str(late_count)),
            ("Anti-Spoofing Verified:", str(anti_spoofing_count))
        ]
        
        for i, (label, value) in enumerate(summary_data):
            tk.Label(summary_grid, text=label, font=ModernTheme.FONT_SUBHEADING, 
                    bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_SECONDARY,
                    anchor='e').grid(row=i, column=0, sticky='e', padx=(0, 10), pady=3)
            tk.Label(summary_grid, text=value, font=ModernTheme.FONT_BODY, 
                    bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY,
                    anchor='w').grid(row=i, column=1, sticky='w', pady=3)
        
        # Records section
        records_label = tk.Label(main_container, text="Attendance Records", 
                                font=ModernTheme.FONT_HEADING,
                                bg=ModernTheme.BACKGROUND, fg=ModernTheme.TEXT_PRIMARY)
        records_label.pack(pady=(ModernTheme.PADDING_MEDIUM, ModernTheme.PADDING_SMALL))
        
        # Table card
        table_card = StyledFrame(main_container, elevated=True, bg=ModernTheme.SURFACE)
        table_card.pack(fill='both', expand=True)
        
        table_inner = tk.Frame(table_card, bg=ModernTheme.SURFACE)
        table_inner.pack(fill='both', expand=True, padx=ModernTheme.PADDING_MEDIUM, 
                        pady=ModernTheme.PADDING_MEDIUM)
        
        # Configure treeview style
        style = ttk.Style()
        style.configure("Report.Treeview", 
                       background=ModernTheme.SURFACE,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       fieldbackground=ModernTheme.SURFACE,
                       font=ModernTheme.FONT_BODY)
        style.configure("Report.Treeview.Heading",
                       font=ModernTheme.FONT_SUBHEADING,
                       background=ModernTheme.SURFACE_DARK,
                       foreground=ModernTheme.TEXT_PRIMARY)
        
        # Define columns
        columns = ('Student ID', 'Student Name', 'Date', 'Time', 'Status', 'Anti-Spoofing')
        tree = ttk.Treeview(table_inner, columns=columns, show='headings', 
                           height=15, style="Report.Treeview")
        
        # Configure column headings and widths
        tree.heading('Student ID', text='Student ID')
        tree.heading('Student Name', text='Student Name')
        tree.heading('Date', text='Date')
        tree.heading('Time', text='Time')
        tree.heading('Status', text='Status')
        tree.heading('Anti-Spoofing', text='Anti-Spoofing')
        
        tree.column('Student ID', width=100)
        tree.column('Student Name', width=200)
        tree.column('Date', width=120)
        tree.column('Time', width=100)
        tree.column('Status', width=100)
        tree.column('Anti-Spoofing', width=120)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(table_inner, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(table_inner, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for tree and scrollbars
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_inner.grid_rowconfigure(0, weight=1)
        table_inner.grid_columnconfigure(0, weight=1)
        
        # Insert data into treeview with color coding
        for index, row in df.iterrows():
            status = row.get('status', 'Present')
            anti_spoof = 'Yes' if row.get('anti_spoofing', False) else 'No'
            
            values = (
                row.get('student_id', ''),
                row.get('student_name', ''),
                row.get('date', ''),
                row.get('time', ''),
                status,
                anti_spoof
            )
            
            # Add tag based on status
            tag = 'late' if status == 'Late' else 'present'
            tree.insert('', 'end', values=values, tags=(tag,))
        
        # Configure tags for color coding
        tree.tag_configure('present', background='#d4edda')  # Light green
        tree.tag_configure('late', background='#fff3cd')      # Light yellow
        
        # Buttons at bottom
        button_frame = tk.Frame(main_container, bg=ModernTheme.BACKGROUND)
        button_frame.pack(pady=(ModernTheme.PADDING_LARGE, 0))
        
        StyledButton(button_frame, text="Export to CSV", 
                    command=lambda: self.update_status(f"Report saved to: {report_file}"),
                    style="primary").pack(side='left', padx=5)
        
        StyledButton(button_frame, text="Close", command=report_window.destroy,
                    style="neutral").pack(side='left', padx=5)
        
        self.update_status(f"Report generated with {total_attendances} records")
            
    def export_data(self):
        """Export attendance data from SQL database"""
        if not self.current_course:
            messagebox.showwarning("Warning", "Please select a course first.")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Attendance Data"
        )
        
        if filename:
            try:
                # Get all attendance records for the current course from database
                # Use a wide date range to get all records
                start_date = "2000-01-01"  # Far past date
                end_date = datetime.date.today().strftime("%Y-%m-%d")
                
                # Query database for all attendance records
                attendance_records = []
                # Get all dates with attendance
                self.db.cursor.execute('''
                    SELECT DISTINCT date FROM attendance 
                    WHERE course_id = ? 
                    ORDER BY date
                ''', (self.current_course,))
                
                dates = [row[0] for row in self.db.cursor.fetchall()]
                
                for date_str in dates:
                    records = self.db.get_attendance_by_date(self.current_course, date_str)
                    attendance_records.extend(records)
                
                if not attendance_records:
                    messagebox.showinfo("Info", "No attendance data found.")
                    return
                
                # Convert to DataFrame
                df_data = []
                for record in attendance_records:
                    df_data.append({
                        'student_id': record['student_id'],
                        'student_name': record['name'],
                        'email': record['email'],
                        'department': record['department'],
                        'date': record['date'],
                        'time': record['time'],
                        'status': record['status']
                    })
                
                combined_df = pd.DataFrame(df_data)
                combined_df.to_csv(filename, index=False)
                
                messagebox.showinfo("Success", f"Data exported to {filename}\n\nTotal records: {len(df_data)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {str(e)}")
                print(f"Export error: {e}")
                
    def update_status(self, message):
        """Update status display"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        
    def clear_status(self):
        """Clear status display"""
        self.status_text.delete(1.0, tk.END)
        
    def start(self):
        """Start the application"""
        self.main_window.mainloop()
        
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
        if hasattr(self, 'db'):
            self.db.close()


class SimpleStudentDialog:
    def __init__(self, parent, main_app):
        self.result = None
        self.main_app = main_app
        self.captured_image = None
        self.face_encoding = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Register New Student")
        self.dialog.geometry("750x1000")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        
    def create_widgets(self):
        # Create a main container with scrollbar if needed
        main_container = tk.Frame(self.dialog)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title at the top
        tk.Label(main_container, text="Student Registration", 
                font=('Arial', 22, 'bold')).pack(pady=(0, 15))
        
        # Create two columns frame
        content_frame = tk.Frame(main_container)
        content_frame.pack(fill='both', expand=True)
        
        # Left column - Form
        left_frame = tk.Frame(content_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 15))
        
        tk.Label(left_frame, text="Student Information", 
                font=('Arial', 18, 'bold')).pack(pady=(0, 15), anchor='w')
        
        # Create a frame for form fields
        form_frame = tk.Frame(left_frame)
        form_frame.pack(fill='both', expand=True)
        
        # Student ID
        tk.Label(form_frame, text="Student ID:", 
                font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky='w', pady=8)
        self.student_id_entry = tk.Entry(form_frame, width=40)
        self.student_id_entry.grid(row=0, column=1, pady=8, padx=(10, 0))
        
        # Full Name
        tk.Label(form_frame, text="Full Name:", 
                font=('Arial', 14, 'bold')).grid(row=1, column=0, sticky='w', pady=8)
        self.name_entry = tk.Entry(form_frame, width=40)
        self.name_entry.grid(row=1, column=1, pady=8, padx=(10, 0))
        
        # Email
        tk.Label(form_frame, text="Email:", 
                font=('Arial', 14, 'bold')).grid(row=2, column=0, sticky='w', pady=8)
        self.email_entry = tk.Entry(form_frame, width=40)
        self.email_entry.grid(row=2, column=1, pady=8, padx=(10, 0))
        
        # Course (auto-filled from selected course)
        tk.Label(form_frame, text="Course:", 
                font=('Arial', 14, 'bold')).grid(row=3, column=0, sticky='w', pady=8)
        self.department_entry = tk.Entry(form_frame, width=40)
        self.department_entry.grid(row=3, column=1, pady=8, padx=(10, 0))
        
        # Auto-fill with selected course
        if self.main_app.current_course:
            course_name = self.main_app.courses_db[self.main_app.current_course]['course_name']
            self.department_entry.insert(0, course_name)
            self.department_entry.configure(state='readonly')
        else:
            self.department_entry.insert(0, "No course selected")
            self.department_entry.configure(state='readonly')
        
        # Semester
        tk.Label(form_frame, text="Semester:", 
                font=('Arial', 14, 'bold')).grid(row=4, column=0, sticky='w', pady=8)
        self.year_var = tk.StringVar(value="1")
        year_combo = ttk.Combobox(form_frame, textvariable=self.year_var, 
                                 values=["1", "2", "3", "4", "5", "6", "7", "8"], 
                                 width=38, state='readonly')
        year_combo.grid(row=4, column=1, pady=8, padx=(10, 0))
        
        # Phone
        tk.Label(form_frame, text="Phone:", 
                font=('Arial', 14, 'bold')).grid(row=5, column=0, sticky='w', pady=8)
        self.phone_entry = tk.Entry(form_frame, width=40)
        self.phone_entry.grid(row=5, column=1, pady=8, padx=(10, 0))
        
        # Add some vertical spacing
        tk.Label(form_frame, text="").grid(row=6, column=0, columnspan=2, pady=10)
        
        # Right column - Image capture
        right_frame = tk.Frame(content_frame)
        right_frame.pack(side='right', fill='both', padx=(15, 0))
        
        tk.Label(right_frame, text="Face Capture", 
                font=('Arial', 18, 'bold')).pack(pady=(0, 15))
        
        # Live preview from main camera
        tk.Label(right_frame, text="Live Camera Preview", 
                font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        
        # Fixed-size container for live preview
        live_preview_container = tk.Frame(right_frame, bg='lightgray', width=200, height=150)
        live_preview_container.pack(pady=5)
        live_preview_container.pack_propagate(False)
        
        self.live_preview_label = tk.Label(live_preview_container, bg='lightgray')
        self.live_preview_label.place(x=0, y=0, width=200, height=150)
        self.live_preview_label.configure(text="Live Camera Preview", font=('Arial', 10))
        
        # Captured image preview
        tk.Label(right_frame, text="Captured Image", 
                font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        
        # Fixed-size container for captured image
        image_container = tk.Frame(right_frame, bg='lightblue', width=200, height=150)
        image_container.pack(pady=5)
        image_container.pack_propagate(False)
        
        self.image_label = tk.Label(image_container, bg='lightblue')
        self.image_label.place(x=0, y=0, width=200, height=150)
        self.image_label.configure(text="No image captured", font=('Arial', 12))
        
        # Start live preview
        self.update_live_preview()
        
        # Capture button frame
        capture_frame = tk.Frame(right_frame)
        capture_frame.pack(pady=15)
        
        self.capture_btn = tk.Button(capture_frame, text="Capture Face", 
                                    command=self.capture_face,
                                    bg='#3498db', fg='white', width=20, height=2,
                                    font=('Arial', 12, 'bold'))
        self.capture_btn.pack(pady=5)
        
        # Retake button
        self.retake_btn = tk.Button(capture_frame, text="Retake Photo", 
                                   command=self.retake_photo,
                                   bg='#f39c12', fg='white', width=20, height=2,
                                   font=('Arial', 12, 'bold'), state='disabled')
        self.retake_btn.pack(pady=5)
        
        # Status label
        self.status_label = tk.Label(right_frame, text="Position face in camera and click Capture", 
                                    font=('Arial', 10), wraplength=250, justify='center',
                                    bg='#f0f0f0', relief='solid', bd=1)
        self.status_label.pack(pady=10, fill='x', padx=5)
        
        # Buttons frame at the BOTTOM
        button_frame = tk.Frame(main_container)
        button_frame.pack(pady=10, fill='x')
        
        self.register_btn = tk.Button(button_frame, text="Register Student", 
                    command=self.register,
                    bg='#2ecc71', fg='black', width=20, height=2,
                    font=('Arial', 12, 'bold'), state='disabled')
        self.register_btn.pack(side='left', padx=(0, 10))
        
        tk.Button(button_frame, text="Cancel", command=self.cancel,
                 bg='#95a5a6', fg='white', width=20, height=2,
                 font=('Arial', 12, 'bold')).pack(side='left')
    
    def update_live_preview(self):
        """Update live preview from main camera"""
        if not hasattr(self, 'dialog') or not self.dialog.winfo_exists():
            return
            
        try:
            if (self.main_app.webcam_active and 
                hasattr(self.main_app, 'most_recent_capture_arr') and 
                self.main_app.most_recent_capture_arr is not None):
                
                # Get current frame from main app
                frame = self.main_app.most_recent_capture_arr.copy()
                
                # Convert and resize for preview
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb)
                img_pil = img_pil.resize((200, 150), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                img_tk = ImageTk.PhotoImage(img_pil)
                
                # Update live preview
                self.live_preview_label.configure(image=img_tk, text="")
                self.live_preview_label.image = img_tk
                
            else:
                # Show camera not active message
                if hasattr(self, 'live_preview_label') and self.live_preview_label.winfo_exists():
                    self.live_preview_label.configure(
                        image="", 
                        text="Camera not active", 
                        font=('Arial', 9),
                        bg='lightcoral'
                    )
                    self.live_preview_label.image = None
                
        except Exception as e:
            print(f"Error updating live preview: {e}")
        
        # Schedule next update
        try:
            if hasattr(self, 'dialog') and self.dialog.winfo_exists():
                self.dialog.after(100, self.update_live_preview)
        except:
            pass
    
    def capture_face(self):
        """Capture face from camera with anti-spoofing check"""
        try:
            # Check if main app camera is active
            if not self.main_app.webcam_active:
                messagebox.showerror("Error", "Camera not active. Please start the camera first.")
                return
            
            if not hasattr(self.main_app, 'most_recent_capture_arr') or self.main_app.most_recent_capture_arr is None:
                messagebox.showerror("Error", "No camera feed available.")
                return
            
            # Update status
            self.status_label.configure(text="Processing face capture...")
            self.dialog.update()
            
            # Capture the current frame
            frame = self.main_app.most_recent_capture_arr.copy()
            
            # Anti-spoofing check if enabled
            if self.main_app.anti_spoofing_enabled:
                self.status_label.configure(text="Verifying real face...")
                self.dialog.update()
                
                try:
                    if test_spoofing:
                        spoof_label = test_spoofing(
                            image=frame,
                            model_dir=self.main_app.model_dir,
                            device_id=0
                        )
                        
                        if spoof_label != 1:
                            self.status_label.configure(text="SPOOFING DETECTED! Please use real face.")
                            messagebox.showerror("Security Alert", "SPOOFING DETECTED!\n\nFake face detected during registration!")
                            return
                except Exception as spoof_error:
                    self.status_label.configure(text="Anti-spoofing error. Proceeding without verification.")
                    print(f"Anti-spoofing error: {spoof_error}")
            
            # Check for face in the image
            face_encodings = face_recognition.face_encodings(frame)
            
            if len(face_encodings) == 0:
                self.status_label.configure(text="No face detected. Please position face clearly.")
                messagebox.showerror("Error", "No face detected. Please position your face clearly.")
                return
            
            if len(face_encodings) > 1:
                self.status_label.configure(text="Multiple faces detected. Please ensure only one face.")
                messagebox.showwarning("Warning", "Multiple faces detected. Please ensure only one face is visible.")
                return
            
            # Store the captured image and face encoding
            self.captured_image = frame
            self.face_encoding = face_encodings[0]
            
            # Display the captured image
            self.display_captured_image(frame)
            
            # Update UI
            self.status_label.configure(text="✅ Face captured successfully!")
            self.capture_btn.configure(state='disabled')
            self.retake_btn.configure(state='normal')
            self.register_btn.configure(state='normal')
            
        except Exception as e:
            error_msg = f"Failed to capture face: {str(e)}"
            self.status_label.configure(text="❌ Capture failed. Please try again.")
            messagebox.showerror("Error", error_msg)
            print(f"Capture error: {e}")
    
    def display_captured_image(self, frame):
        """Display the captured image in the preview"""
        try:
            # Convert and resize image
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_pil = img_pil.resize((200, 150), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            img_tk = ImageTk.PhotoImage(img_pil)
            
            # Update captured image label
            self.image_label.configure(image=img_tk, text="", bg='lightgreen')
            self.image_label.image = img_tk
            
        except Exception as e:
            print(f"Error displaying captured image: {e}")
            messagebox.showerror("Display Error", f"Could not display captured image: {str(e)}")
    
    def retake_photo(self):
        """Reset for retaking photo"""
        self.captured_image = None
        self.face_encoding = None
        
        # Reset captured image display
        self.image_label.configure(image="", text="No image captured", bg='lightblue')
        self.image_label.image = None
        
        # Update UI
        self.status_label.configure(text="Position face in camera and click Capture")
        self.capture_btn.configure(state='normal')
        self.retake_btn.configure(state='disabled')
        self.register_btn.configure(state='disabled')
    
    def save_student_image(self, student_id):
        """Save the captured image to file"""
        if self.captured_image is not None:
            try:
                images_dir = "./attendify_db/student_images"
                if not os.path.exists(images_dir):
                    os.makedirs(images_dir)
                
                image_path = f"{images_dir}/{student_id}.jpg"
                cv2.imwrite(image_path, self.captured_image)
                return image_path
            except Exception as e:
                print(f"Error saving image: {e}")
                return None
        return None
                 
    def register(self):
        # Validate form inputs
        if not all([self.student_id_entry.get(), self.name_entry.get(), 
                   self.email_entry.get(), self.department_entry.get()]):
            messagebox.showerror("Error", "Please fill in all required fields.")
            return
        
        # Check if image is captured
        if self.captured_image is None or self.face_encoding is None:
            messagebox.showerror("Error", "Please capture a face image first.")
            return
        
        # Save student image
        student_id = self.student_id_entry.get()
        image_path = self.save_student_image(student_id)
            
        self.result = {
            'student_id': student_id,
            'name': self.name_entry.get(),
            'email': self.email_entry.get(),
            'department': self.department_entry.get(),
            'year': self.year_var.get(),
            'phone': self.phone_entry.get(),
            'face_encoding': self.face_encoding.tolist() if self.face_encoding is not None else None,
            'image_path': image_path,
            'registration_date': datetime.datetime.now().isoformat(),
            'anti_spoofing_verified': self.main_app.anti_spoofing_enabled
        }
        
        # Cleanup images before closing
        if hasattr(self, 'live_preview_label'):
            self.live_preview_label.image = None
        if hasattr(self, 'image_label'):
            self.image_label.image = None
            
        self.dialog.destroy()
        
    def cancel(self):
        """Cancel registration and cleanup"""
        if hasattr(self, 'live_preview_label'):
            self.live_preview_label.image = None
        if hasattr(self, 'image_label'):
            self.image_label.image = None
        self.dialog.destroy()


class SimpleCourseDialog:
    def __init__(self, parent, edit_mode=False, course_data=None):
        self.result = None
        self.edit_mode = edit_mode
        self.course_data = course_data
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Course" if edit_mode else "Add New Course")
        self.dialog.geometry("450x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        
        # Pre-fill data if in edit mode
        if self.edit_mode and self.course_data:
            self.populate_fields()
        
    def populate_fields(self):
        """Populate form fields with existing course data"""
        self.course_id_entry.insert(0, self.course_data.get('course_id', ''))
        self.course_name_entry.insert(0, self.course_data.get('course_name', ''))
        self.instructor_entry.insert(0, self.course_data.get('instructor', ''))
        self.department_entry.insert(0, self.course_data.get('department', ''))
        self.room_entry.insert(0, self.course_data.get('room', ''))
        
        # Parse schedule to set days and times
        schedule = self.course_data.get('schedule', '')
        if schedule:
            # Parse schedule like "Mon, Wed, Fri 09:00-10:30"
            parts = schedule.split()
            if len(parts) >= 2:
                # Parse days
                days_str = ' '.join(parts[:-1]).replace(',', '')
                day_map = {
                    'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday',
                    'Thu': 'Thursday', 'Fri': 'Friday', 'Sat': 'Saturday', 'Sun': 'Sunday'
                }
                for short, full in day_map.items():
                    if short in days_str:
                        self.days_vars[full].set(True)
                
                # Parse times
                time_range = parts[-1]
                if '-' in time_range:
                    start_time, end_time = time_range.split('-')
                    if ':' in start_time:
                        start_hour, start_min = start_time.split(':')
                        self.start_hour_var.set(start_hour)
                        self.start_minute_var.set(start_min)
                    if ':' in end_time:
                        end_hour, end_min = end_time.split(':')
                        self.end_hour_var.set(end_hour)
                        self.end_minute_var.set(end_min)
        
    def create_widgets(self):
        self.dialog.configure(bg=ModernTheme.BACKGROUND)
        
        main_container = StyledFrame(self.dialog, bg=ModernTheme.BACKGROUND)
        main_container.pack(fill='both', expand=True, padx=ModernTheme.PADDING_LARGE, 
                           pady=ModernTheme.PADDING_LARGE)
        
        # Title
        title_text = "Edit Course" if self.edit_mode else "Add New Course"
        title = tk.Label(
            main_container,
            text=title_text,
            font=ModernTheme.FONT_TITLE,
            bg=ModernTheme.BACKGROUND,
            fg=ModernTheme.TEXT_PRIMARY
        )
        title.pack(pady=(0, ModernTheme.PADDING_LARGE))
        
        # Form card
        form_card = StyledFrame(main_container, elevated=True, bg=ModernTheme.SURFACE)
        form_card.pack(fill='both', expand=True)
        
        form_inner = tk.Frame(form_card, bg=ModernTheme.SURFACE)
        form_inner.pack(fill='both', expand=True, padx=ModernTheme.PADDING_LARGE, 
                       pady=ModernTheme.PADDING_MEDIUM)
        
        # Course ID
        tk.Label(form_inner, text="Course ID:", font=ModernTheme.FONT_SUBHEADING,
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 3))
        self.course_id_entry = tk.Entry(form_inner, width=30, font=ModernTheme.FONT_BODY)
        StyleUtils.style_entry(self.course_id_entry)
        self.course_id_entry.pack(pady=(0, ModernTheme.PADDING_SMALL), fill='x')
        
        # Course Name
        tk.Label(form_inner, text="Course Name:", font=ModernTheme.FONT_SUBHEADING,
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 3))
        self.course_name_entry = tk.Entry(form_inner, width=30, font=ModernTheme.FONT_BODY)
        StyleUtils.style_entry(self.course_name_entry)
        self.course_name_entry.pack(pady=(0, ModernTheme.PADDING_SMALL), fill='x')
        
        # Instructor
        tk.Label(form_inner, text="Instructor:", font=ModernTheme.FONT_SUBHEADING,
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 3))
        self.instructor_entry = tk.Entry(form_inner, width=30, font=ModernTheme.FONT_BODY)
        StyleUtils.style_entry(self.instructor_entry)
        self.instructor_entry.pack(pady=(0, ModernTheme.PADDING_SMALL), fill='x')
        
        # Program
        tk.Label(form_inner, text="Program:", font=ModernTheme.FONT_SUBHEADING,
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 3))
        self.department_entry = tk.Entry(form_inner, width=30, font=ModernTheme.FONT_BODY)
        StyleUtils.style_entry(self.department_entry)
        self.department_entry.pack(pady=(0, ModernTheme.PADDING_SMALL), fill='x')
        
        # Days of Week
        tk.Label(form_inner, text="Days of Week:", font=ModernTheme.FONT_SUBHEADING,
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(anchor='w', pady=(ModernTheme.PADDING_SMALL, 3))
        days_frame = tk.Frame(form_inner, bg=ModernTheme.SURFACE)
        days_frame.pack(pady=(0, ModernTheme.PADDING_SMALL), fill='x')
        
        self.days_vars = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for i, day in enumerate(days):
            var = tk.BooleanVar()
            self.days_vars[day] = var
            cb = tk.Checkbutton(days_frame, text=day[:3], variable=var, 
                              bg=ModernTheme.SURFACE, font=ModernTheme.FONT_BODY)
            cb.grid(row=i//4, column=i%4, sticky='w', padx=5)
        
        # Start Time
        tk.Label(form_inner, text="Start Time:", font=ModernTheme.FONT_SUBHEADING,
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(anchor='w', pady=(ModernTheme.PADDING_SMALL, 3))
        start_time_frame = tk.Frame(form_inner, bg=ModernTheme.SURFACE)
        start_time_frame.pack(pady=(0, ModernTheme.PADDING_SMALL))
        
        self.start_hour_var = tk.StringVar(value="09")
        self.start_minute_var = tk.StringVar(value="00")
        
        tk.Label(start_time_frame, text="Hour:", bg=ModernTheme.SURFACE, 
                font=ModernTheme.FONT_BODY).pack(side='left')
        start_hour_combo = ttk.Combobox(start_time_frame, textvariable=self.start_hour_var, 
                                       values=[f"{i:02d}" for i in range(24)], width=5)
        start_hour_combo.pack(side='left', padx=5)
        
        tk.Label(start_time_frame, text="Minute:", bg=ModernTheme.SURFACE,
                font=ModernTheme.FONT_BODY).pack(side='left', padx=(10, 0))
        start_minute_combo = ttk.Combobox(start_time_frame, textvariable=self.start_minute_var,
                                         values=[f"{i:02d}" for i in range(0, 60, 15)], width=5)
        start_minute_combo.pack(side='left', padx=5)
        
        # End Time
        tk.Label(form_inner, text="End Time:", font=ModernTheme.FONT_SUBHEADING,
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(anchor='w', pady=(ModernTheme.PADDING_SMALL, 3))
        end_time_frame = tk.Frame(form_inner, bg=ModernTheme.SURFACE)
        end_time_frame.pack(pady=(0, ModernTheme.PADDING_SMALL))
        
        self.end_hour_var = tk.StringVar(value="10")
        self.end_minute_var = tk.StringVar(value="30")
        
        tk.Label(end_time_frame, text="Hour:", bg=ModernTheme.SURFACE,
                font=ModernTheme.FONT_BODY).pack(side='left')
        end_hour_combo = ttk.Combobox(end_time_frame, textvariable=self.end_hour_var,
                                     values=[f"{i:02d}" for i in range(24)], width=5)
        end_hour_combo.pack(side='left', padx=5)
        
        tk.Label(end_time_frame, text="Minute:", bg=ModernTheme.SURFACE,
                font=ModernTheme.FONT_BODY).pack(side='left', padx=(10, 0))
        end_minute_combo = ttk.Combobox(end_time_frame, textvariable=self.end_minute_var,
                                       values=[f"{i:02d}" for i in range(0, 60, 15)], width=5)
        end_minute_combo.pack(side='left', padx=5)
        
        # Room
        tk.Label(form_inner, text="Room:", font=ModernTheme.FONT_SUBHEADING,
                bg=ModernTheme.SURFACE, fg=ModernTheme.TEXT_PRIMARY).pack(anchor='w', pady=(ModernTheme.PADDING_SMALL, 3))
        self.room_entry = tk.Entry(form_inner, width=30, font=ModernTheme.FONT_BODY)
        StyleUtils.style_entry(self.room_entry)
        self.room_entry.pack(pady=(0, ModernTheme.PADDING_SMALL), fill='x')
        
        # Buttons
        button_frame = tk.Frame(main_container, bg=ModernTheme.BACKGROUND)
        button_frame.pack(pady=(ModernTheme.PADDING_LARGE, 0))
        
        button_text = "Update Course" if self.edit_mode else "Add Course"
        StyledButton(button_frame, text=button_text, command=self.add_course,
                    style="primary").pack(side='left', padx=5)
        StyledButton(button_frame, text="Cancel", command=self.cancel,
                    style="neutral").pack(side='left', padx=5)
                 
    def add_course(self):
        if not all([self.course_id_entry.get(), self.course_name_entry.get(), 
                   self.instructor_entry.get(), self.department_entry.get()]):
            messagebox.showerror("Error", "Please fill in all required fields.")
            return
        
        # Get selected days
        selected_days = [day for day, var in self.days_vars.items() if var.get()]
        if not selected_days:
            messagebox.showerror("Error", "Please select at least one day.")
            return
        
        # Validate time
        try:
            start_time = f"{self.start_hour_var.get()}:{self.start_minute_var.get()}"
            end_time = f"{self.end_hour_var.get()}:{self.end_minute_var.get()}"
            
            # Check if end time is after start time
            start_minutes = int(self.start_hour_var.get()) * 60 + int(self.start_minute_var.get())
            end_minutes = int(self.end_hour_var.get()) * 60 + int(self.end_minute_var.get())
            
            if end_minutes <= start_minutes:
                messagebox.showerror("Error", "End time must be after start time.")
                return
                
        except ValueError:
            messagebox.showerror("Error", "Invalid time format.")
            return
        
        # Create schedule string
        days_short = [day[:3] for day in selected_days]
        schedule = f"{', '.join(days_short)} {start_time}-{end_time}"
            
        self.result = {
            'course_id': self.course_id_entry.get(),
            'course_name': self.course_name_entry.get(),
            'instructor': self.instructor_entry.get(),
            'department': self.department_entry.get(),
            'days': selected_days,
            'start_time': start_time,
            'end_time': end_time,
            'schedule': schedule,
            'room': self.room_entry.get() or 'TBD'
        }
        
        self.dialog.destroy()
        
    def cancel(self):
        self.dialog.destroy()


class StudentSelectionDialog:
    """Dialog for selecting a student to edit"""
    
    def __init__(self, parent, database):
        self.result = None
        self.database = database
        self.selected_student = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Student to Edit")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        self.load_students()
        
    def create_widgets(self):
        """Create the dialog UI elements"""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        tk.Label(main_frame, text="Select Student to Edit", 
                font=('Arial', 16, 'bold')).pack(pady=(0, 15))
        
        # Treeview frame with scrollbar
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True, pady=10)
        
        # Create Treeview with columns
        columns = ('ID', 'Name', 'Department')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure column headings
        self.tree.heading('ID', text='Student ID')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Department', text='Department')
        
        # Configure column widths
        self.tree.column('ID', width=150)
        self.tree.column('Name', width=250)
        self.tree.column('Department', width=250)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_student_selected)
        
        # Buttons frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=15)
        
        self.edit_btn = tk.Button(button_frame, text="Edit", 
                                  command=self.on_confirm,
                                  bg='#3498db', fg='white', width=15, height=2,
                                  font=('Arial', 11, 'bold'), state='disabled')
        self.edit_btn.pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Cancel", 
                 command=self.on_cancel,
                 bg='#95a5a6', fg='white', width=15, height=2,
                 font=('Arial', 11, 'bold')).pack(side='left', padx=10)
        
    def load_students(self):
        """Load all students from database and populate the Treeview"""
        try:
            students = self.database.get_all_students()
            
            if not students:
                # Show message if no students
                self.tree.insert('', 'end', values=('No students', 'registered', 'yet'))
                return
            
            # Populate tree with student data
            for student_id, student_data in students.items():
                self.tree.insert('', 'end', values=(
                    student_data.get('student_id', ''),
                    student_data.get('name', ''),
                    student_data.get('department', '')
                ))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load students: {str(e)}")
            
    def on_student_selected(self, event):
        """Handle student selection from Treeview"""
        selection = self.tree.selection()
        if selection:
            # Get selected item
            item = self.tree.item(selection[0])
            values = item['values']
            
            # Check if it's a valid student (not the "No students" message)
            if values and values[0] != 'No students':
                self.selected_student = values[0]  # Store student ID
                self.edit_btn.configure(state='normal')
            else:
                self.selected_student = None
                self.edit_btn.configure(state='disabled')
        else:
            self.selected_student = None
            self.edit_btn.configure(state='disabled')
            
    def on_confirm(self):
        """Handle Edit button click"""
        if self.selected_student:
            self.result = self.selected_student
            self.dialog.destroy()    
    def on_delete(self):
        """Handle delete button click - delete student from database"""
        try:
            student_id = self.student_data.get('student_id', '')
            student_name = self.student_data.get('name', '')
            
            # Confirm deletion with user
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to delete this student?\n\n"
                f"Student ID: {student_id}\n"
                f"Name: {student_name}\n\n"
                f"This action cannot be undone. All attendance records for this student will also be deleted.",
                icon='warning'
            )
            
            if not confirm:
                return
            
            # Delete student from database
            success = self.database.delete_student(student_id)
            
            if success:
                # Delete student image file if exists
                image_path = self.student_data.get('image_path', '')
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Error deleting image file: {e}")
                
                # Also delete any temporary new image if exists
                if self.new_image_path and os.path.exists(self.new_image_path):
                    try:
                        os.remove(self.new_image_path)
                    except Exception as e:
                        print(f"Error deleting temporary image: {e}")
                
                # Show success message
                messagebox.showinfo(
                    "Success",
                    f"Student deleted successfully!\n\nStudent ID: {student_id}\nName: {student_name}"
                )
                
                # Refresh View Students window if open
                self.refresh_view_students_window()
                
                # Set result and close dialog
                self.result = {
                    'student_id': student_id,
                    'deleted': True
                }
                self.dialog.destroy()
            else:
                messagebox.showerror(
                    "Error",
                    "Failed to delete student. The student may not exist in the database."
                )
                
        except Exception as e:
            error_msg = f"Failed to delete student: {str(e)}"
            messagebox.showerror("Database Error", error_msg)
            print(f"Delete error: {e}")


            
    def on_cancel(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()


class EditStudentDialog:
    """Dialog for editing existing student information"""
    
    def __init__(self, parent, database, student_data, anti_spoofing_enabled, main_app=None):
        self.result = None
        self.database = database
        self.student_data = student_data
        self.anti_spoofing_enabled = anti_spoofing_enabled
        self.main_app = main_app  # Store reference to main application
        self.new_face_encoding = None
        self.new_image_path = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Student Profile")
        self.dialog.geometry("750x900")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        self.populate_fields()
        
    def create_widgets(self):
        """Create the dialog UI elements"""
        # Main container
        main_container = tk.Frame(self.dialog)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(main_container, text="Edit Student Profile", 
                font=('Arial', 22, 'bold')).pack(pady=(0, 15))
        
        # Create two columns frame
        content_frame = tk.Frame(main_container)
        content_frame.pack(fill='both', expand=True)
        
        # Left column - Form
        left_frame = tk.Frame(content_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 15))
        
        tk.Label(left_frame, text="Student Information", 
                font=('Arial', 18, 'bold')).pack(pady=(0, 15), anchor='w')
        
        # Create a frame for form fields
        form_frame = tk.Frame(left_frame)
        form_frame.pack(fill='both', expand=True)
        
        # Student ID (read-only)
        tk.Label(form_frame, text="Student ID:", 
                font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky='w', pady=8)
        self.student_id_label = tk.Label(form_frame, text="", 
                                         font=('Arial', 14), 
                                         bg='#e0e0e0', relief='solid', bd=1,
                                         anchor='w', padx=5)
        self.student_id_label.grid(row=0, column=1, pady=8, padx=(10, 0), sticky='ew')
        
        # Full Name
        tk.Label(form_frame, text="Full Name:", 
                font=('Arial', 14, 'bold')).grid(row=1, column=0, sticky='w', pady=8)
        self.name_entry = tk.Entry(form_frame, width=40)
        self.name_entry.grid(row=1, column=1, pady=8, padx=(10, 0))
        
        # Email
        tk.Label(form_frame, text="Email:", 
                font=('Arial', 14, 'bold')).grid(row=2, column=0, sticky='w', pady=8)
        self.email_entry = tk.Entry(form_frame, width=40)
        self.email_entry.grid(row=2, column=1, pady=8, padx=(10, 0))
        
        # Department
        tk.Label(form_frame, text="Department:", 
                font=('Arial', 14, 'bold')).grid(row=3, column=0, sticky='w', pady=8)
        self.department_entry = tk.Entry(form_frame, width=40)
        self.department_entry.grid(row=3, column=1, pady=8, padx=(10, 0))
        
        # Year/Semester
        tk.Label(form_frame, text="Year:", 
                font=('Arial', 14, 'bold')).grid(row=4, column=0, sticky='w', pady=8)
        self.year_entry = tk.Entry(form_frame, width=40)
        self.year_entry.grid(row=4, column=1, pady=8, padx=(10, 0))
        
        # Phone
        tk.Label(form_frame, text="Phone:", 
                font=('Arial', 14, 'bold')).grid(row=5, column=0, sticky='w', pady=8)
        self.phone_entry = tk.Entry(form_frame, width=40)
        self.phone_entry.grid(row=5, column=1, pady=8, padx=(10, 0))
        
        # Right column - Face photo
        right_frame = tk.Frame(content_frame)
        right_frame.pack(side='right', fill='both', padx=(15, 0))
        
        tk.Label(right_frame, text="Face Photo", 
                font=('Arial', 18, 'bold')).pack(pady=(0, 15))
        
        # Current face photo display
        tk.Label(right_frame, text="Current Photo", 
                font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        
        # Fixed-size container for face photo
        photo_container = tk.Frame(right_frame, bg='lightgray', width=200, height=150)
        photo_container.pack(pady=5)
        photo_container.pack_propagate(False)
        
        self.photo_label = tk.Label(photo_container, bg='lightgray')
        self.photo_label.place(x=0, y=0, width=200, height=150)
        self.photo_label.configure(text="No photo available", font=('Arial', 10))
        
        # Re-capture button
        tk.Button(right_frame, text="Re-capture Face", 
                 command=self.on_recapture_face,
                 bg='#f39c12', fg='white', width=20, height=2,
                 font=('Arial', 12, 'bold')).pack(pady=15)
        
        # Status label
        self.status_label = tk.Label(right_frame, text="", 
                                    font=('Arial', 9), wraplength=200, justify='center',
                                    bg='#f0f0f0', relief='solid', bd=1)
        self.status_label.pack(pady=10, fill='x', padx=5)
        
        # Buttons frame at the bottom
        button_frame = tk.Frame(main_container)
        button_frame.pack(pady=15, fill='x')
        
        self.save_button = tk.Button(button_frame, text="Save Changes", 
                 command=self.on_save,
                 bg='#2ecc71', fg='white', width=20, height=2,
                 font=('Arial', 12, 'bold'))
        self.save_button.pack(side='left', padx=(0, 10))
        
        tk.Button(button_frame, text="Delete Student", 
                 command=self.on_delete,
                 bg='#e74c3c', fg='white', width=20, height=2,
                 font=('Arial', 12, 'bold')).pack(side='left', padx=(0, 10))
        
        tk.Button(button_frame, text="Cancel", 
                 command=self.on_cancel,
                 bg='#95a5a6', fg='white', width=20, height=2,
                 font=('Arial', 12, 'bold')).pack(side='left')
        
        # Validation error label
        self.validation_error_label = tk.Label(main_container, text="", 
                                              font=('Arial', 10), fg='red',
                                              wraplength=700, justify='left')
        self.validation_error_label.pack(pady=(5, 0))
        
        # Add field change listeners for real-time validation
        self.name_entry.bind('<KeyRelease>', self.on_field_change)
        self.email_entry.bind('<KeyRelease>', self.on_field_change)
        self.department_entry.bind('<KeyRelease>', self.on_field_change)
        self.year_entry.bind('<KeyRelease>', self.on_field_change)
        self.phone_entry.bind('<KeyRelease>', self.on_field_change)
    
    def populate_fields(self):
        """Fill form fields with existing student data"""
        # Set student ID (read-only)
        self.student_id_label.configure(text=self.student_data.get('student_id', ''))
        
        # Fill editable fields
        self.name_entry.insert(0, self.student_data.get('name', ''))
        self.email_entry.insert(0, self.student_data.get('email', ''))
        self.department_entry.insert(0, self.student_data.get('department', ''))
        self.year_entry.insert(0, str(self.student_data.get('year', '')))
        self.phone_entry.insert(0, self.student_data.get('phone', ''))
        
        # Load and display current face photo if available
        image_path = self.student_data.get('image_path', '')
        if image_path and os.path.exists(image_path):
            try:
                # Load image using OpenCV
                img = cv2.imread(image_path)
                if img is not None:
                    # Convert BGR to RGB
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(img_rgb)
                    img_pil = img_pil.resize((200, 150), Image.Resampling.LANCZOS)
                    
                    # Convert to PhotoImage
                    img_tk = ImageTk.PhotoImage(img_pil)
                    
                    # Update photo label
                    self.photo_label.configure(image=img_tk, text="", bg='white')
                    self.photo_label.image = img_tk
                else:
                    self.photo_label.configure(text="Photo not found", bg='lightcoral')
            except Exception as e:
                print(f"Error loading photo: {e}")
                self.photo_label.configure(text="Error loading photo", bg='lightcoral')
        else:
            self.photo_label.configure(text="No photo available", bg='lightgray')
        
        # Trigger initial validation
        self.update_validation_state()
    
    def on_field_change(self, event=None):
        """Handle field change events for real-time validation"""
        self.update_validation_state()
    
    def update_validation_state(self):
        """Update validation state and enable/disable save button"""
        is_valid, errors = self.validate_fields()
        
        if is_valid:
            # Enable save button and clear error message
            self.save_button.configure(state='normal')
            self.validation_error_label.configure(text="")
        else:
            # Disable save button and show error messages
            self.save_button.configure(state='disabled')
            error_text = "Validation errors:\n• " + "\n• ".join(errors)
            self.validation_error_label.configure(text=error_text)
    
    def validate_email(self, email):
        """Validate email format using regex
        
        Args:
            email: Email string to validate
            
        Returns:
            bool: True if email is valid, False otherwise
        """
        import re
        if not email or not email.strip():
            return False
        
        email = email.strip()
        
        # Additional checks
        if '..' in email:
            return False
        
        # Check that we have exactly one @
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        
        # Check local part
        if not local or local.startswith('.') or local.endswith('.'):
            return False
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*$', local):
            return False
        
        # Check domain part - must have at least one dot and end with TLD
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$', domain):
            return False
        if domain.startswith('.') or domain.endswith('.'):
            return False
        
        return True
    
    def validate_fields(self):
        """Validate all form fields
        
        Returns:
            tuple: (is_valid: bool, error_messages: list)
        """
        errors = []
        
        # Get field values
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        department = self.department_entry.get().strip()
        year = self.year_entry.get().strip()
        phone = self.phone_entry.get().strip()
        
        # Validate name (not empty, alphanumeric and spaces)
        if not name:
            errors.append("Name is required")
        
        # Validate email (not empty and valid format)
        if not email:
            errors.append("Email is required")
        elif not self.validate_email(email):
            errors.append("Email format is invalid (e.g., user@example.com)")
        
        # Validate department (not empty)
        if not department:
            errors.append("Department is required")
        
        # Validate year (not empty and numeric)
        if not year:
            errors.append("Year is required")
        else:
            try:
                year_int = int(year)
                if year_int < 1 or year_int > 10:
                    errors.append("Year must be between 1 and 10")
            except ValueError:
                errors.append("Year must be a numeric value")
        
        # Validate phone (not empty and numeric characters)
        if not phone:
            errors.append("Phone is required")
        elif not phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            errors.append("Phone must contain only numeric characters (and optional +, -, spaces, parentheses)")
        
        return (len(errors) == 0, errors)
    
    def on_recapture_face(self):
        """Handle face re-capture button click - opens camera for new face capture"""
        try:
            # Use stored main_app reference
            main_app = self.main_app
            
            if not main_app:
                messagebox.showerror("Error", "Could not access main application.")
                return
            
            # Check if camera is active
            if not main_app.webcam_active:
                messagebox.showerror("Error", "Camera not active. Please start the camera first.")
                return
            
            if not hasattr(main_app, 'most_recent_capture_arr') or main_app.most_recent_capture_arr is None:
                messagebox.showerror("Error", "No camera feed available.")
                return
            
            # Update status
            self.status_label.configure(text="Processing face capture...")
            self.dialog.update()
            
            # Capture the current frame
            frame = main_app.most_recent_capture_arr.copy()
            
            # Anti-spoofing check if enabled
            if self.anti_spoofing_enabled:
                self.status_label.configure(text="Verifying real face...")
                self.dialog.update()
                
                try:
                    if test_spoofing:
                        spoof_label = test_spoofing(
                            image=frame,
                            model_dir=main_app.model_dir,
                            device_id=0
                        )
                        
                        if spoof_label != 1:
                            self.status_label.configure(text="SPOOFING DETECTED! Please use real face.")
                            messagebox.showerror("Security Alert", "SPOOFING DETECTED!\n\nFake face detected!")
                            return
                except Exception as spoof_error:
                    self.status_label.configure(text="Anti-spoofing error. Proceeding without verification.")
                    print(f"Anti-spoofing error: {spoof_error}")
            
            # Check for face in the image
            face_encodings = face_recognition.face_encodings(frame)
            
            if len(face_encodings) == 0:
                self.status_label.configure(text="No face detected. Please position face clearly.")
                messagebox.showerror("Error", "No face detected. Please position your face clearly.")
                return
            
            if len(face_encodings) > 1:
                self.status_label.configure(text="Multiple faces detected. Please ensure only one face.")
                messagebox.showwarning("Warning", "Multiple faces detected. Please ensure only one face is visible.")
                return
            
            # Store the new face encoding and prepare to save image
            self.new_face_encoding = face_encodings[0]
            
            # Save the captured image temporarily
            student_id = self.student_data.get('student_id', '')
            images_dir = "./attendify_db/student_images"
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            
            self.new_image_path = f"{images_dir}/{student_id}_new.jpg"
            cv2.imwrite(self.new_image_path, frame)
            
            # Display the new captured image
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_pil = img_pil.resize((200, 150), Image.Resampling.LANCZOS)
            
            img_tk = ImageTk.PhotoImage(img_pil)
            self.photo_label.configure(image=img_tk, text="", bg='lightgreen')
            self.photo_label.image = img_tk
            
            # Update status
            self.status_label.configure(text="✅ New face captured successfully!")
            messagebox.showinfo("Success", "Face captured successfully! Click 'Save Changes' to update.")
            
        except Exception as e:
            error_msg = f"Failed to capture face: {str(e)}"
            self.status_label.configure(text="❌ Capture failed. Please try again.")
            messagebox.showerror("Error", error_msg)
            print(f"Face capture error: {e}")
    
    def on_save(self):
        """Handle save button click - validate and save changes to database"""
        try:
            # Validate all fields
            is_valid, errors = self.validate_fields()
            
            if not is_valid:
                error_text = "Please fix the following errors:\n• " + "\n• ".join(errors)
                messagebox.showerror("Validation Error", error_text)
                return
            
            # Collect updated data from form fields
            student_id = self.student_data.get('student_id', '')
            name = self.name_entry.get().strip()
            email = self.email_entry.get().strip()
            department = self.department_entry.get().strip()
            year = self.year_entry.get().strip()
            phone = self.phone_entry.get().strip()
            
            # Prepare face data (use new values if re-captured, else None to keep existing)
            face_encoding = None
            image_path = None
            
            if self.new_face_encoding is not None:
                # Face was re-captured
                face_encoding = self.new_face_encoding.tolist()
                image_path = self.new_image_path
                
                # Rename the temporary image to final name
                if image_path and os.path.exists(image_path):
                    final_image_path = f"./attendify_db/student_images/{student_id}.jpg"
                    
                    # Remove old image if exists
                    if os.path.exists(final_image_path):
                        os.remove(final_image_path)
                    
                    # Rename new image
                    os.rename(image_path, final_image_path)
                    image_path = final_image_path
            
            # Prepare student data dictionary
            updated_student_data = {
                'name': name,
                'email': email,
                'department': department,
                'year': year,
                'phone': phone
            }
            
            # Add face data if re-captured
            if face_encoding is not None:
                updated_student_data['face_encoding'] = face_encoding
            if image_path is not None:
                updated_student_data['image_path'] = image_path
            
            # Call database update method
            success = self.database.update_student(student_id, updated_student_data)
            
            if success:
                # Display success message
                messagebox.showinfo("Success", f"Student profile updated successfully!\n\nStudent ID: {student_id}\nName: {name}")
                
                # Refresh View Students window if open
                self.refresh_view_students_window()
                
                # Set result and close dialog
                self.result = {
                    'student_id': student_id,
                    'name': name,
                    'email': email,
                    'department': department,
                    'year': year,
                    'phone': phone,
                    'updated': True
                }
                self.dialog.destroy()
            else:
                # Display error message
                messagebox.showerror("Error", "Failed to update student profile. The student may not exist in the database.")
                
        except Exception as e:
            # Handle any errors gracefully
            error_msg = f"Failed to save changes: {str(e)}"
            messagebox.showerror("Database Error", error_msg)
            print(f"Save error: {e}")
    
    def refresh_view_students_window(self):
        """Refresh the View Students window if it's open"""
        try:
            # Get reference to main app
            main_app = self.dialog.master
            while main_app and not isinstance(main_app, AttendifyWithAntiSpoofing):
                main_app = main_app.master
            
            if not main_app:
                return
            
            # Check if View Students window exists and is open
            # Look for Toplevel windows with "Registered Students" title
            for widget in main_app.main_window.winfo_children():
                if isinstance(widget, tk.Toplevel) and widget.title() == "Registered Students":
                    # Window is open - close and reopen it to refresh
                    widget.destroy()
                    # Reload data and reopen
                    main_app.view_students()
                    break
                    
        except Exception as e:
            print(f"Error refreshing View Students window: {e}")    
    def on_delete(self):
        """Handle delete button click - delete student from database"""
        try:
            student_id = self.student_data.get('student_id', '')
            student_name = self.student_data.get('name', '')
            
            # Confirm deletion with user
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to delete this student?\n\n"
                f"Student ID: {student_id}\n"
                f"Name: {student_name}\n\n"
                f"This action cannot be undone. All attendance records for this student will also be deleted.",
                icon='warning'
            )
            
            if not confirm:
                return
            
            # Delete student from database
            success = self.database.delete_student(student_id)
            
            if success:
                # Delete student image file if exists
                image_path = self.student_data.get('image_path', '')
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Error deleting image file: {e}")
                
                # Also delete any temporary new image if exists
                if self.new_image_path and os.path.exists(self.new_image_path):
                    try:
                        os.remove(self.new_image_path)
                    except Exception as e:
                        print(f"Error deleting temporary image: {e}")
                
                # Show success message
                messagebox.showinfo(
                    "Success",
                    f"Student deleted successfully!\n\nStudent ID: {student_id}\nName: {student_name}"
                )
                
                # Refresh View Students window if open
                self.refresh_view_students_window()
                
                # Set result and close dialog
                self.result = {
                    'student_id': student_id,
                    'deleted': True
                }
                self.dialog.destroy()
            else:
                messagebox.showerror(
                    "Error",
                    "Failed to delete student. The student may not exist in the database."
                )
                
        except Exception as e:
            error_msg = f"Failed to delete student: {str(e)}"
            messagebox.showerror("Database Error", error_msg)
            print(f"Delete error: {e}")


    
    def on_cancel(self):
        """Handle cancel button click"""
        self.result = None
        self.dialog.destroy()


if __name__ == "__main__":
    app = AttendifyWithAntiSpoofing()
    app.start()


