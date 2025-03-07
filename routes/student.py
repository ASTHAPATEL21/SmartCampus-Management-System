from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Course, Grade, Notification, Material, Assignment, ClassSchedule
from pathlib import Path

student_router = APIRouter()
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


@student_router.get("/student/panel", response_class=HTMLResponse)
async def student_panel(request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """Student Panel: View notifications and enrolled courses."""
    # Fetch the logged-in student
    student = db.query(User).filter(User.username == username, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Fetch notifications for the student
    notifications = db.query(Notification).filter(Notification.user_id == student.id).order_by(
        Notification.created_at.desc()).all()

    # Fetch courses in which the student is enrolled
    enrolled_courses = (
        db.query(Course)
        .join(Grade, Grade.course_id == Course.id)
        .filter(Grade.student_id == student.id)
        .all()
    )

    return templates.TemplateResponse(
        "student_panel.html",
        {"request": request, "student": student, "notifications": notifications, "enrolled_courses": enrolled_courses},
    )


@student_router.get("/student/notifications", response_class=HTMLResponse)
async def view_notifications(request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """View all notifications for the logged-in student."""
    # Fetch the logged-in student
    student = db.query(User).filter(User.username == username, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Fetch all notifications for the student
    notifications = db.query(Notification).filter(Notification.user_id == student.id).order_by(
        Notification.created_at.desc()).all()

    return templates.TemplateResponse(
        "student_notifications.html",
        {"request": request, "student": student, "notifications": notifications},
    )


@student_router.get("/student/courses", response_class=HTMLResponse)
async def student_courses(request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """List all courses the student is enrolled in."""
    # Fetch the logged-in student
    student = db.query(User).filter(User.username == username, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Fetch courses the student is enrolled in
    courses = (
        db.query(Course)
        .join(Grade, Grade.course_id == Course.id)
        .filter(Grade.student_id == student.id)
        .all()
    )

    # Prepare data for each course
    course_data = []
    for course in courses:
        num_materials = db.query(Material).filter(Material.course_id == course.id).count()
        num_assignments = db.query(Assignment).filter(Assignment.course_id == course.id).count()
        course_data.append({
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "num_materials": num_materials,
            "num_assignments": num_assignments,
        })

    return templates.TemplateResponse(
        "student_courses.html",
        {
            "request": request,
            "student": student,
            "courses": course_data,
        },
    )


@student_router.get("/student/course-materials/{course_id}", response_class=HTMLResponse)
async def view_materials(course_id: int, request: Request, db: Session = Depends(get_db),
                         username: str = Depends(check_session)):
    """View materials for a specific course."""
    # Fetch the logged-in student
    student = db.query(User).filter(User.username == username, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check if the student is enrolled in the course
    enrollment = db.query(Grade).filter(Grade.course_id == course_id, Grade.student_id == student.id).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="You are not enrolled in this course")

    # Fetch course materials
    materials = db.query(Material).filter(Material.course_id == course_id).all()
    course = db.query(Course).filter(Course.id == course_id).first()

    return templates.TemplateResponse(
        "student_course_materials.html",
        {
            "request": request,
            "student": student,
            "course": course,
            "materials": materials,
        },
    )


@student_router.get("/student/course-assignments/{course_id}", response_class=HTMLResponse)
async def view_assignments(course_id: int, request: Request, db: Session = Depends(get_db),
                           username: str = Depends(check_session)):
    """View assignments for a specific course."""
    # Fetch the logged-in student
    student = db.query(User).filter(User.username == username, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check if the student is enrolled in the course
    enrollment = db.query(Grade).filter(Grade.course_id == course_id, Grade.student_id == student.id).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="You are not enrolled in this course")

    # Fetch course assignments
    assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()
    course = db.query(Course).filter(Course.id == course_id).first()

    return templates.TemplateResponse(
        "student_course_assignments.html",
        {
            "request": request,
            "student": student,
            "course": course,
            "assignments": assignments,
        },
    )


@student_router.get("/student/assignments", response_class=HTMLResponse)
async def all_assignments(
        request: Request,
        db: Session = Depends(get_db),
        username: str = Depends(check_session)
):
    """Fetch all assignments for the student's enrolled courses, sorted by nearest due date."""
    # Get the current student
    student = db.query(User).filter(User.username == username, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # Get all courses the student is enrolled in
    enrolled_courses = db.query(Course.id).join(Grade).filter(Grade.student_id == student.id).subquery()

    # Fetch assignments for these courses
    assignments = (
        db.query(Assignment, Course.title.label("course_title"))
        .join(Course, Assignment.course_id == Course.id)
        .filter(Course.id.in_(enrolled_courses))
        .order_by(Assignment.due_date.asc())
        .all()
    )

    # Convert assignments for rendering
    assignment_list = [
        {
            "title": a.Assignment.title,
            "description": a.Assignment.description,
            "due_date": a.Assignment.due_date,
            "file_path": a.Assignment.file_path,
            "course_title": a.course_title,
        }
        for a in assignments
    ]

    return templates.TemplateResponse(
        "student_assignments.html",
        {"request": request, "student_assignments": assignment_list},
    )




@student_router.get("/student/grades", response_class=HTMLResponse)
async def view_grades(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(check_session)
):
    """Fetch all grades for courses the student is enrolled in."""
    # Fetch the student
    student = db.query(User).filter(User.username == username, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # Fetch grades for the student's courses
    grades = (
        db.query(Grade, Course.title.label("course_title"))
        .join(Course, Grade.course_id == Course.id)
        .filter(Grade.student_id == student.id)
        .all()
    )

    # Prepare data for rendering
    grade_list = [
        {
            "course_title": g.course_title,
            "grade": g.Grade.grade
        }
        for g in grades
    ]

    return templates.TemplateResponse(
        "student_grades.html",
        {"request": request, "grades": grade_list},
    )



@student_router.get("/student/scheduled-classes", response_class=HTMLResponse)
async def view_scheduled_classes(request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """View all scheduled classes for enrolled courses."""
    # Fetch the logged-in student
    student = db.query(User).filter(User.username == username, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Fetch scheduled classes for courses the student is enrolled in
    schedules = (
        db.query(ClassSchedule, Course.title.label("course_title"))
        .join(Course, ClassSchedule.course_id == Course.id)
        .join(Grade, Grade.course_id == Course.id)
        .filter(Grade.student_id == student.id)
        .order_by(ClassSchedule.day_of_week.asc(), ClassSchedule.start_time.asc())
        .all()
    )

    # Format the schedule for rendering
    schedule_list = [
        {
            "course_title": schedule.course_title,
            "day_of_week": schedule.ClassSchedule.day_of_week,
            "start_time": schedule.ClassSchedule.start_time,
            "end_time": schedule.ClassSchedule.end_time,
            "location": schedule.ClassSchedule.location or "TBD",
        }
        for schedule in schedules
    ]

    return templates.TemplateResponse(
        "student_scheduled_classes.html",
        {"request": request, "schedules": schedule_list},
    )
