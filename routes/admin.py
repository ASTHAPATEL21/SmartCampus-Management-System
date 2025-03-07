from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Course, Assignment, Material, Grade, Notification, ClassSchedule

from datetime import datetime

from utils.hashing import hash_password

admin_router = APIRouter()
templates = Jinja2Templates(directory="templates")


def check_session(request: Request):
    """Check if the user is logged in via session cookie."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return session_token


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@admin_router.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, username: str = Depends(check_session)):
    """Admin Panel: Protected route for admin users."""
    return templates.TemplateResponse("admin_panel.html", {"request": request, "username": username})


@admin_router.get("/admin/manage-students", response_class=HTMLResponse)
async def manage_students(request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """View all students."""
    students = db.query(User).filter(User.role == "student").all()
    return templates.TemplateResponse("admin_manage_student.html", {"request": request, "students": students})


@admin_router.post("/admin/delete-student/{student_id}")
async def delete_student(student_id: int, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """Delete a student."""
    # Fetch the student from the database
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Delete the student
    db.delete(student)
    db.commit()
    return RedirectResponse(url="/admin/manage-students", status_code=303)


@admin_router.post("/admin/add-student")
async def add_student(
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
        username_session: str = Depends(check_session),
):
    """Add a new student."""
    # Check if the username already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the password
    hashed_password = hash_password(password)

    # Create a new student user
    new_student = User(username=username, hashed_password=hashed_password, role="student")
    db.add(new_student)
    db.commit()

    return RedirectResponse(url="/admin/manage-students", status_code=303)


@admin_router.get("/admin/manage-teachers", response_class=HTMLResponse)
async def manage_teachers(request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """View all teachers."""
    teachers = db.query(User).filter(User.role == "faculty").all()
    return templates.TemplateResponse("admin_manage_teacher.html", {"request": request, "teachers": teachers})


@admin_router.post("/admin/add-teacher")
async def add_teacher(
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
        username_session: str = Depends(check_session),
):
    """Add a new teacher."""
    # Check if the username already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the password
    hashed_password = hash_password(password)

    # Create a new teacher user
    new_teacher = User(username=username, hashed_password=hashed_password, role="faculty")
    db.add(new_teacher)
    db.commit()

    return RedirectResponse(url="/admin/manage-teachers", status_code=303)


@admin_router.post("/admin/delete-teacher/{teacher_id}")
async def delete_teacher(teacher_id: int, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """Delete a teacher."""
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "faculty").first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    db.delete(teacher)
    db.commit()
    return RedirectResponse(url="/admin/manage-teachers", status_code=303)


@admin_router.get("/admin/manage-courses", response_class=HTMLResponse)
async def manage_courses(request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """View all courses."""
    courses = db.query(Course).all()
    faculties = db.query(User).filter(User.role == "faculty").all()
    return templates.TemplateResponse("admin_manage_course.html",
                                      {"request": request, "courses": courses, "faculties": faculties})


@admin_router.post("/admin/add-course")
async def add_course(
        title: str = Form(...),
        faculty_id: int = Form(...),
        db: Session = Depends(get_db),
        username_session: str = Depends(check_session),
):
    """Add a new course."""
    # Fetch the assigned faculty
    faculty = db.query(User).filter(User.id == faculty_id, User.role == "faculty").first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    # Create the new course
    new_course = Course(title=title, faculty_id=faculty_id)
    db.add(new_course)
    db.commit()

    return RedirectResponse(url="/admin/manage-courses", status_code=303)


@admin_router.post("/admin/delete-course/{course_id}")
async def delete_course(course_id: int, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """Delete a course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return RedirectResponse(url="/admin/manage-courses", status_code=303)


@admin_router.get("/admin/manage-course/{course_id}", response_class=HTMLResponse)
async def manage_course_details(
        course_id: int,
        request: Request,
        db: Session = Depends(get_db),
        username: str = Depends(check_session),
):
    """View course details and manage enrollments."""

    # Validate course existence
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Fetch all students (available for enrollment)
    students = db.query(User).filter(User.role == "student").all()

    # Debugging: Fetch Grades
    grades = db.query(Grade).filter(Grade.course_id == course_id).all()
    print(f"Grades for course {course_id}: {grades}")

    # Fetch enrolled students for the course
    enrolled_students = (
        db.query(User)
        .join(Grade, Grade.student_id == User.id)
        .filter(Grade.course_id == course_id)
        .all()
    )
    print(f"Enrolled Students: {enrolled_students}")

    return templates.TemplateResponse(
        "admin_manage_course_details.html",
        {
            "request": request,
            "course": course,
            "students": students,
            "enrolled_students": enrolled_students,
        },
    )


@admin_router.post("/admin/add-student-to-course/{course_id}")
async def add_student_to_course(
        course_id: int,
        student_id: int = Form(...),
        db: Session = Depends(get_db),
        username: str = Depends(check_session),
):
    """Enroll a student in the course and send a notification."""
    # Validate course existence
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Validate student existence
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check if the student is already enrolled
    existing_enrollment = (
        db.query(Grade)
        .filter(Grade.course_id == course_id, Grade.student_id == student_id)
        .first()
    )
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Student is already enrolled in this course")

    # Enroll the student in the course
    enrollment = Grade(student_id=student_id, course_id=course_id, grade="Not Graded")
    db.add(enrollment)
    db.commit()

    # Create a notification for the student
    notification = Notification(
        message=f"You have been enrolled in the course: {course.title}",
        user_id=student_id,
        created_at=datetime.now(),
    )
    db.add(notification)
    db.commit()

    return RedirectResponse(url=f"/admin/manage-course/{course_id}", status_code=303)


@admin_router.post("/admin/remove-student-from-course/{course_id}/{student_id}")
async def remove_student_from_course(
        course_id: int,
        student_id: int,
        db: Session = Depends(get_db),
        username: str = Depends(check_session),
):
    """Remove a student from the course."""
    enrollment = (
        db.query(Grade)
        .filter(Grade.course_id == course_id, Grade.student_id == student_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    db.delete(enrollment)
    db.commit()

    return RedirectResponse(url=f"/admin/manage-course/{course_id}", status_code=303)


@admin_router.get("/admin/reports/course", response_class=HTMLResponse)
async def course_reports(request: Request, search: str = "", db: Session = Depends(get_db)):
    """Display all courses with optional search functionality."""
    # Query courses with optional search filter
    courses_query = db.query(Course)
    if search:
        courses_query = courses_query.filter(Course.title.ilike(f"%{search}%"))

    courses = courses_query.all()

    return templates.TemplateResponse(
        "list_course_reports.html",
        {"request": request, "courses": courses, "search": search},
    )


@admin_router.get("/admin/reports/student", response_class=HTMLResponse)
async def list_student_reports(request: Request, search: str = "", db: Session = Depends(get_db)):
    """List all students with optional search functionality for generating reports."""
    # Query students with optional search filter
    students_query = db.query(User).filter(User.role == "student")
    if search:
        students_query = students_query.filter(User.username.ilike(f"%{search}%"))

    students = students_query.all()

    return templates.TemplateResponse(
        "list_student_reports.html",
        {"request": request, "students": students, "search": search},
    )


@admin_router.get("/admin/reports/course/{course_id}", response_class=HTMLResponse)
async def course_report(course_id: int, request: Request, db: Session = Depends(get_db)):
    """Generate a detailed report for a specific course."""
    # Fetch course details
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Collect course-specific data
    assignments_count = db.query(Assignment).filter(Assignment.course_id == course_id).count()
    materials_count = db.query(Material).filter(Material.course_id == course_id).count()
    schedules = db.query(ClassSchedule).filter(ClassSchedule.course_id == course_id).all()

    students = (
        db.query(User, Grade.grade)
        .join(Grade, Grade.student_id == User.id)
        .filter(Grade.course_id == course_id)
        .all()
    )

    return templates.TemplateResponse(
        "course_report.html",
        {
            "request": request,
            "course": course,
            "assignments_count": assignments_count,
            "materials_count": materials_count,
            "schedules": schedules,
            "students": students,
        },
    )


@admin_router.get("/admin/reports/student/{student_id}", response_class=HTMLResponse)
async def student_report(student_id: int, request: Request, db: Session = Depends(get_db)):
    """Generate a detailed report for a specific student."""
    # Fetch student details
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Collect student-specific data
    courses = (
        db.query(Course, Grade.grade)
        .join(Grade, Grade.course_id == Course.id)
        .filter(Grade.student_id == student_id)
        .all()
    )

    notifications = db.query(Notification).filter(Notification.user_id == student_id).all()

    return templates.TemplateResponse(
        "student_report.html",
        {
            "request": request,
            "student": student,
            "courses": courses,
            "notifications": notifications,
        },
    )
