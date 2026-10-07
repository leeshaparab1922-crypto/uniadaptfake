from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import csv
import io

# Database Session Dependency (तुमच्या प्रोजेक्टमधील path प्रमाणे)
from app.db.session import get_db

router = APIRouter(prefix="/admin/students", tags=["Students Admin"])

# --- Pydantic Schemas ---
class StudentBase(BaseModel):
    roll_number: str
    full_name: str
    email: EmailStr
    department_code: Optional[str] = "CSL102"
    program_code: Optional[str] = "CS2034"
    batch_start_year: Optional[int] = 2026
    current_semester_no: int = 1
    section_name: str = "c"

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_semester_no: Optional[int] = None
    section_name: Optional[str] = None

# --- In-Memory / DB Mock Helper (किंवा तुमचे SQLModel वापरा) ---
# जर तुमच्याकडे थेट Student मॉडेल असेल तर: from app.models.student import Student

@router.post("", status_code=status.HTTP_201_CREATED)
def add_single_student(student: StudentCreate, db: Session = Depends(get_db)):
    """
    Manually add a single student if missed during CSV import.
    """
    # 1. Check for Duplicate Roll Number
    # existing = db.query(Student).filter(Student.roll_number == student.roll_number).first()
    # if existing:
    #     raise HTTPException(status_code=400, detail=f"Roll number {student.roll_number} already exists!")
    
    # 2. Commit to Database
    # new_st = Student(**student.dict())
    # db.add(new_st)
    # db.commit()
    # db.refresh(new_st)
    
    return {
        "status": "success",
        "message": f"Student {student.roll_number} successfully enrolled",
        "student": student
    }

@router.delete("/{roll_number}", status_code=status.HTTP_200_OK)
def delete_student(roll_number: str, db: Session = Depends(get_db)):
    """
    Remove an unwanted student record from the database.
    """
    # student = db.query(Student).filter(Student.roll_number == roll_number).first()
    # if not student:
    #     raise HTTPException(status_code=404, detail="Student record not found")
    
    # db.delete(student)
    # db.commit()
    
    return {
        "status": "success",
        "message": f"Student {roll_number} deleted successfully"
    }

@router.put("/{roll_number}", status_code=status.HTTP_200_OK)
def update_student(roll_number: str, payload: StudentUpdate, db: Session = Depends(get_db)):
    """
    Update student details (Name, Email, Section, Semester).
    """
    return {
        "status": "success",
        "message": f"Student {roll_number} updated successfully",
        "updated_data": payload
    }

@router.post("/import-csv")
async def import_students_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Bulk import students via CSV stream.
    """
    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    
    students_list = []
    for row in reader:
        students_list.append(row)
        
    return {
        "status": "success",
        "imported_count": len(students_list),
        "students": students_list
    }