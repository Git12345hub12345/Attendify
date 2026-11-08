# Attendify - Smart Face Attendance System

Face attendance system using face recognition with Python and SQL database!

## Features

✓ Face recognition with anti-spoofing detection
✓ SQL database (SQLite) for better performance
✓ Multiple camera support (built-in + external webcams)
✓ Student and course management
✓ Attendance tracking with late detection
✓ Report generation
✓ Clean and modern UI

## Quick Start

### For New Users
```bash
# Install dependencies
pip install -r requirements.txt  # Linux/Mac
pip install -r requirements_windows.txt  # Windows

# Run the application
python attendify.py
```

Database will be created automatically at `attendify_db/attendify.db`

### For Existing Users (Migration from old version)
```bash
# Backup your data first
cp -r attendify_db attendify_db_backup

# Run migration
python migrate_to_sql.py

# Run application
python attendify.py
```

## Requirements

- Python 3.8+
- OpenCV
- face_recognition
- tkinter
- SQLite3 (included with Python)

### Windows Setup

Follow these steps for Windows:
1. Follow instructions in this video: https://www.youtube.com/watch?v=oTv7HB6CRpQ
2. Install packages: `pip install -r requirements_windows.txt`

### Linux/Mac Setup

```bash
pip install -r requirements.txt
```

## Anti-Spoofing Feature

To enable liveness detection:

```bash
git clone https://github.com/computervisioneng/Silent-Face-Anti-Spoofing.git
pip install -r Silent-Face-Anti-Spoofing/requirements.txt
```

The application will automatically detect and enable anti-spoofing if available.

## Database

Attendify uses SQLite database for:
- Student information and face encodings
- Course details
- Attendance records with timestamps

**Benefits:**
- Fast queries with indexes
- Data integrity with foreign keys
- No duplicate attendance
- Single file backup
- Handles thousands of records

See `SQL_DATABASE_GUIDE.md` for detailed database documentation.

## Camera Support

- Automatic detection of available cameras
- Support for external USB webcams
- Camera selection dropdown
- DirectShow backend for Windows (faster, fewer errors)

## Project Structure

```
attendify/
├── attendify.py              # Main application
├── database.py               # Database module
├── migrate_to_sql.py         # Migration tool
├── requirements.txt          # Dependencies (Linux/Mac)
├── requirements_windows.txt  # Dependencies (Windows)
├── SQL_DATABASE_GUIDE.md     # Database documentation
├── attendify_db/
│   ├── attendify.db          # SQLite database
│   ├── student_images/       # Student photos
│   └── reports/              # Generated reports
└── Silent-Face-Anti-Spoofing/ # Anti-spoofing module (optional)
```

## Usage

1. **Start Camera**: Click "Start Camera" to activate webcam
2. **Select Course**: Choose a course from dropdown
3. **Register Students**: Click "Register Student" to add new students
4. **Mark Attendance**: Click "Mark Attendance" for face recognition
5. **View Reports**: Generate attendance reports by date range

## Videos

### Face Attendance System
<p align="center">
<a href="https://www.youtube.com/watch?v=z_dbnYHAQYg">
    <img width="600" src="https://utils-computervisiondeveloper.s3.amazonaws.com/thumbnails/with_play_button/face_attendance.jpg" alt="Watch the video">
    </br>Watch on YouTube: Face attendance system with Python and face recognition!
</a>
</p>

### Anti-Spoofing Feature
<p align="center">
<a href="https://www.youtube.com/watch?v=_KvtVk8Gk1A">
    <img width="600" src="https://utils-computervisiondeveloper.s3.amazonaws.com/thumbnails/with_play_button/face_attendance_spoofing.jpg" alt="Watch the video">
    </br>Watch on YouTube: Face attendance system with liveness detection!
</a>
</p>

### Web App Version
<p align="center">
<a href="https://www.youtube.com/watch?v=yWmW5uEtNws">
    <img width="600" src="https://utils-computervisiondeveloper.s3.amazonaws.com/thumbnails/with_play_button/face_attendance_web_app_react_python.jpg" alt="Watch the video">
    </br>Watch on YouTube: Face attendance + face recognition web app with React and Python!
</a>
</p>

The code for the web app is available [here](https://github.com/computervisiondeveloper/face-attendance-web-app-react-python).

## Troubleshooting

**Camera not detected?**
- Ensure camera is connected and not used by another app
- Check camera permissions
- Try different camera from dropdown

**Database locked?**
- Close all Attendify instances
- Only one connection at a time

**Face not recognized?**
- Ensure good lighting
- Position face clearly in camera
- Re-register if needed

## License

See LICENSE.md for details.

## Credits

Original project by Computer Vision Developer
Enhanced with SQL database, multi-camera support, and improved UI
