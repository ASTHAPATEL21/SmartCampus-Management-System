from fastapi import APIRouter, Request, Depends, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from models import User, Course, Material, Notification, ClassSchedule
from datetime import datetime

from database import SessionLocal
from models import User, Course, Assignment, Grade

faculty_router = APIRouter()
templates = Jinja2Templates(directory="templates")
UPLOAD_DIRECTORY = "uploaded_materials/"  # Define the upload directory
UPLOAD_DIRECTORY = "uploaded_assignments/"  # Define upload directory


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


@faculty_router.get("/faculty/panel", response_class=HTMLResponse)
async def faculty_panel(request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """Faculty Panel: View courses allocated to the logged-in faculty."""
    # Fetch the logged-in faculty member
    faculty = db.query(User).filter(User.username == username, User.role == "faculty").first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty member not found")

    # Fetch courses allocated to this faculty member
    courses = db.query(Course).filter(Course.faculty_id == faculty.id).all()

    return templates.TemplateResponse(
        "faculty_panel.html",
        {"request": request, "faculty": faculty, "courses": courses},
    )


@faculty_router.get("/faculty/manage-course-materials/{course_id}", response_class=HTMLResponse)
async def manage_course_materials(course_id: int, request: Request, db: Session = Depends(get_db),
                                  username: str = Depends(check_session)):
    """View and upload course materials."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.faculty.username != username:
        raise HTTPException(status_code=403, detail="You are not authorized to manage this course")

    materials = db.query(Material).filter(Material.course_id == course_id).all()
    return templates.TemplateResponse(
        "manage_course_materials.html",
        {"request": request, "course": course, "materials": materials},
    )


@faculty_router.post("/faculty/upload-material/{course_id}")
async def upload_material(
        course_id: int,
        caption: str = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        username: str = Depends(check_session),
):
    """Upload a material for a course and notify students."""
    # Validate course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Validate faculty
    faculty = db.query(User).filter(User.username == username, User.role == "faculty").first()
    if not faculty or course.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="You are not authorized to upload materials for this course")

    # Save file to directory
    Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)
    file_path = f"{UPLOAD_DIRECTORY}{file.filename}"
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    # Save material record in the database
    material = Material(file_path=file_path, caption=caption, course_id=course_id)
    db.add(material)
    db.commit()

    # Determine file type
    file_extension = file.filename.split('.')[-1].lower()
    file_type = {
        "pdf": "PDF Document",
        "docx": "Word Document",
        "png": "Image",
        "jpg": "Image",
        "jpeg": "Image"
    }.get(file_extension, "File")

    # Notify all enrolled students
    enrolled_students = db.query(User).join(Grade, Grade.student_id == User.id).filter(
        Grade.course_id == course_id).all()
    notification_message = f"A {file_type} has been shared by {faculty.username} for the course {course.title}."

    for student in enrolled_students:
        notification = Notification(
            message=notification_message,
            user_id=student.id,
            created_at=datetime.now(),
        )
        db.add(notification)

    db.commit()

    return RedirectResponse(url=f"/faculty/manage-course-materials/{course_id}", status_code=303)


@faculty_router.get("/faculty/manage-assignments/{course_id}", response_class=HTMLResponse)
async def manage_assignments(
        course_id: int,
        request: Request,
        db: Session = Depends(get_db),
        username: str = Depends(check_session),
):
    """View and manage assignments for a course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    faculty = db.query(User).filter(User.username == username, User.role == "faculty").first()
    if not faculty or course.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="You are not authorized to manage assignments for this course")

    assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()

    return templates.TemplateResponse(
        "manage_assignments.html",
        {"request": request, "course": course, "assignments": assignments},
    )


@faculty_router.post("/faculty/add-assignment/{course_id}")
async def add_assignment(
        course_id: int,
        title: str = Form(...),
        description: str = Form(...),
        due_date: str = Form(...),
        file: UploadFile = File(None),  # Optional file upload
        db: Session = Depends(get_db),
        username: str = Depends(check_session),
):
    """Add an assignment for a course with optional file upload."""
    # Validate course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Validate faculty
    faculty = db.query(User).filter(User.username == username, User.role == "faculty").first()
    if not faculty or course.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="You are not authorized to add assignments for this course")

    # Save the uploaded file (if provided)
    file_path = None
    if file:
        Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)
        file_path = f"{UPLOAD_DIRECTORY}{file.filename}"
        with open(file_path, "wb") as f:
            f.write(file.file.read())

    # Save assignment to the database
    assignment = Assignment(
        title=title,
        description=description,
        due_date=datetime.strptime(due_date, "%Y-%m-%d"),
        file_path=file_path,
        course_id=course_id,
    )
    db.add(assignment)
    db.commit()

    # Notify enrolled students
    enrolled_students = db.query(User).join(Grade, Grade.student_id == User.id).filter(
        Grade.course_id == course_id).all()
    notification_message = f"A new assignment '{title}' has been added by {faculty.username} for the course {course.title}."

    for student in enrolled_students:
        notification = Notification(
            message=notification_message,
            user_id=student.id,
            created_at=datetime.now(),
        )
        db.add(notification)

    db.commit()

    return RedirectResponse(url=f"/faculty/manage-assignments/{course_id}", status_code=303)



@faculty_router.post("/faculty/delete-assignment/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(check_session),
):
    """Delete an assignment."""
    # Fetch the assignment from the database
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if the logged-in user is authorized to delete this assignment
    if assignment.course.faculty.username != username:
        raise HTTPException(status_code=403, detail="You are not authorized to delete this assignment")

    # Delete the assignment record
    db.delete(assignment)
    db.commit()

    return RedirectResponse(url=f"/faculty/manage-assignments/{assignment.course_id}", status_code=303)



@faculty_router.get("/faculty/manage-grades/{course_id}", response_class=HTMLResponse)
async def manage_grades(course_id: int, request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """Display the grade management interface for a course."""
    # Validate course existence and faculty authorization
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.faculty.username != username:
        raise HTTPException(status_code=403, detail="Unauthorized to manage grades for this course")

    # Fetch enrolled students and their grades
    grades = (
        db.query(Grade)
        .join(User, Grade.student_id == User.id)
        .filter(Grade.course_id == course_id)
        .all()
    )

    return templates.TemplateResponse(
        "manage_grades.html",
        {"request": request, "course": course, "grades": grades},
    )




@faculty_router.post("/faculty/save-grades/{course_id}")
async def save_grades(
    course_id: int,
    request: Request,  # Fetch the entire request
    db: Session = Depends(get_db),
    username: str = Depends(check_session),
):
    """Save grades for multiple students and notify them."""
    # Validate course existence
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.faculty.username != username:
        raise HTTPException(status_code=403, detail="Unauthorized to save grades for this course")

    # Extract grades from form data
    form_data = await request.form()
    grades = {key.split("[")[1][:-1]: value for key, value in form_data.items() if key.startswith("grades[")}

    # Update grades for each student
    notifications = []
    for student_id, grade in grades.items():
        grade_record = (
            db.query(Grade)
            .filter(Grade.course_id == course_id, Grade.student_id == int(student_id))
            .first()
        )
        if grade_record:
            grade_record.grade = grade
        else:
            # Create a new grade record if not found
            new_grade = Grade(student_id=int(student_id), course_id=course_id, grade=grade)
            db.add(new_grade)

        # Add a notification for the student
        notification_message = f"Your grade has been updated to '{grade}' in the course '{course.title}'."
        notification = Notification(
            message=notification_message,
            user_id=int(student_id),
            created_at=datetime.now(),
        )
        notifications.append(notification)

    # Save all notifications at once
    db.add_all(notifications)
    db.commit()

    return RedirectResponse(url=f"/faculty/manage-grades/{course_id}", status_code=303)


@faculty_router.get("/faculty/manage-schedule/{course_id}", response_class=HTMLResponse)
async def manage_schedule(course_id: int, request: Request, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """View and manage schedule for a course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.faculty.username != username:
        raise HTTPException(status_code=403, detail="You are not authorized to manage this course")

    schedules = db.query(ClassSchedule).filter(ClassSchedule.course_id == course_id).all()
    return templates.TemplateResponse(
        "manage_schedule.html",
        {"request": request, "course": course, "schedules": schedules},
    )

@faculty_router.post("/faculty/add-schedule/{course_id}")
async def add_schedule(
    course_id: int,
    day_of_week: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    location: str = Form(None),
    db: Session = Depends(get_db),
    username: str = Depends(check_session),
):
    """Add a new schedule for a course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.faculty.username != username:
        raise HTTPException(status_code=403, detail="You are not authorized to add schedule for this course")

    # Add new schedule
    new_schedule = ClassSchedule(
        course_id=course_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        location=location,
    )
    db.add(new_schedule)
    db.commit()

    # Notify all enrolled students
    enrolled_students = db.query(User).join(Grade, Grade.student_id == User.id).filter(Grade.course_id == course_id).all()
    notification_message = f"New class scheduled for {course.title} on {day_of_week} from {start_time} to {end_time} at {location or 'TBD'}."
    for student in enrolled_students:
        notification = Notification(
            message=notification_message,
            user_id=student.id,
            created_at=datetime.now()
        )
        db.add(notification)

    db.commit()
    return RedirectResponse(url=f"/faculty/manage-schedule/{course_id}", status_code=303)


@faculty_router.post("/faculty/delete-schedule/{schedule_id}")
async def delete_schedule(schedule_id: int, db: Session = Depends(get_db), username: str = Depends(check_session)):
    """Delete a schedule."""
    schedule = db.query(ClassSchedule).filter(ClassSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    course = db.query(Course).filter(Course.id == schedule.course_id).first()
    if course.faculty.username != username:
        raise HTTPException(status_code=403, detail="You are not authorized to delete this schedule")

    # Notify all enrolled students
    enrolled_students = db.query(User).join(Grade, Grade.student_id == User.id).filter(Grade.course_id == course.id).all()
    notification_message = f"The class scheduled for {course.title} on {schedule.day_of_week} from {schedule.start_time} to {schedule.end_time} has been canceled."
    for student in enrolled_students:
        notification = Notification(
            message=notification_message,
            user_id=student.id,
            created_at=datetime.now()
        )
        db.add(notification)

    # Delete the schedule
    db.delete(schedule)
    db.commit()
    return RedirectResponse(url=f"/faculty/manage-schedule/{course.id}", status_code=303)
