from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Time
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


# User Model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # Store hashed passwords
    role = Column(String, nullable=False)  # 'student', 'faculty', 'admin'

    # Relationships
    courses = relationship("Course", back_populates="faculty")
    grades = relationship("Grade", back_populates="student")
    notifications = relationship("Notification", back_populates="user")


# Course Model
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    faculty_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    faculty = relationship("User", back_populates="courses")
    assignments = relationship("Assignment", back_populates="course")
    materials = relationship("Material", back_populates="course")
    schedules = relationship("ClassSchedule", back_populates="course")



# Material Model
class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)  # Path to the uploaded file
    caption = Column(Text, nullable=True)  # Caption for the material
    uploaded_at = Column(DateTime, default=datetime.now, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))

    # Relationships
    course = relationship("Course", back_populates="materials")


# Assignment Model
class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=False)
    file_path = Column(String, nullable=True)  # New column for optional file upload
    course_id = Column(Integer, ForeignKey("courses.id"))

    # Relationships
    course = relationship("Course", back_populates="assignments")


# Grade Model
class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))  # This line is correct
    grade = Column(String, nullable=False)

    # Relationships
    student = relationship("User", back_populates="grades")
    course = relationship("Course")


# Notification Model
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")


# ClassSchedule Model
class ClassSchedule(Base):
    __tablename__ = "class_schedules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    day_of_week = Column(String, nullable=False)  # e.g., Monday, Tuesday
    start_time = Column(Time, nullable=False)  # Start time of the class
    end_time = Column(Time, nullable=False)  # End time of the class
    location = Column(String, nullable=True)  # Optional class location

    # Relationships
    course = relationship("Course", back_populates="schedules")
