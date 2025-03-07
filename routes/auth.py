from fastapi import APIRouter, Depends, HTTPException, Form, Request
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from database import SessionLocal
from models import User
from utils.hashing import verify_password

auth_router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    """Dependency to provide database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_session(request: Request):
    """Check if the user is logged in via session cookie."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return session_token


# GET route to serve the login page
@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@auth_router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate user and redirect to the appropriate panel."""
    user = db.query(User).filter(User.username == username).first()

    # Verify user credentials
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check user role
    if user.role != role:
        raise HTTPException(status_code=403, detail=f"Invalid role for user {username}")

    # Redirect to appropriate panel based on role
    if role == "admin":
        response = RedirectResponse(url="/admin/panel", status_code=302)
    elif role == "faculty":
        response = RedirectResponse(url="/faculty/panel", status_code=302)
    elif role == "student":
        response = RedirectResponse(url="/student/panel", status_code=302)
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role")

    # Set a session cookie
    response.set_cookie(key="session_token", value=username, httponly=True)
    return response


@auth_router.get("/logout")
async def logout():
    """Log out the user and clear the session cookie."""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("session_token")
    return response


@auth_router.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, username: str = Depends(check_session)):
    """Admin Panel: Protected route for admin users."""
    return templates.TemplateResponse("admin_panel.html", {"request": request, "username": username})


@auth_router.get("/faculty/panel", response_class=HTMLResponse)
async def faculty_panel(request: Request, username: str = Depends(check_session)):
    """Faculty Panel: Protected route for faculty users."""
    return templates.TemplateResponse("faculty_panel.html", {"request": request, "username": username})


@auth_router.get("/student/panel", response_class=HTMLResponse)
async def student_panel(request: Request, username: str = Depends(check_session)):
    """Student Panel: Protected route for student users."""
    return templates.TemplateResponse("student_panel.html", {"request": request, "username": username})
