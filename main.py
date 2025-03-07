from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes.auth import auth_router
from routes.admin import admin_router
from routes.faculty import faculty_router
from routes.student import student_router

# Initialize app and template directory
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mount Static Directories
app.mount("/uploaded_materials", StaticFiles(directory="uploaded_materials"), name="uploaded_materials")
app.mount("/uploaded_assignments", StaticFiles(directory="uploaded_assignments"), name="uploaded_assignments")

# Include Routers
app.include_router(auth_router, prefix="/auth")
app.include_router(admin_router)
app.include_router(faculty_router)
app.include_router(student_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the homepage."""
    return templates.TemplateResponse("home.html", {"request": request})


# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP errors."""
    return templates.TemplateResponse("error.html", {"request": request, "error": str(exc.detail)}, status_code=exc.status_code)


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP errors."""
    return templates.TemplateResponse("error.html", {"request": request, "error": str(exc.detail)}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions."""
    return templates.TemplateResponse("error.html", {"request": request, "error": "An unexpected error occurred."}, status_code=500)
