from typing import Annotated
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, status, HTTPException, Depends
from time import sleep
from pathlib import Path
from sqlmodel import SQLModel, Field, create_engine, Session, select
from uuid import uuid4
import shutil
from uvicorn import run as run_project



UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class FileModel(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    progress: int = Field(default=0)
    

engine = create_engine("sqlite:///./files.db")
SQLModel.metadata.create_all(engine)
    

app = FastAPI()

def get_session():
    with Session(engine) as session:
        yield session

def generate_progress_updates(filename: str = ""):
    for i in range(10):
        yield f"Processing {filename}: {i * 10}% complete\n"
        sleep(5)
    yield f"Processing {filename}: 100% complete\n"

async def process_file(file_path: Path, background_tasks = BackgroundTasks):

        
    if file_path.suffix != ".txt":
        raise HTTPException(status_code=422, detail="Failed: Unsupported file format, please upload a .txt file")

    with open(file_path, "r") as file:
        content = file.read()
        word_count = len(content.split())


    output_path = UPLOAD_DIR / f"{file_path.stem}_word_count.txt"
    with open(output_path, "w") as f:
        f.write(f"Word Count: {word_count}")
    
    background_tasks.add_task(process_file, file_path)

    if file_path.exists():
        file_path.unlink()
            
            
@app.post("/upload/")
async def upload_file(file: UploadFile, background_tasks: BackgroundTasks, status_code=status.HTTP_202_ACCEPTED, db = Session = Depends(get_session)):

    task = FileModel(name=file.filename)
    db.add(task)
    db.commit()
    db.refresh(task)

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "w+b") as f:
        shutil.copyfileobj(file.file, f)


    background_tasks.add_task(process_file, file_path)
    raise status_code


@app.get("/tasks/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_session)):
    task = db.exec(select(FileModel).where(FileModel.id == task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task.id, "file_name": task.file_name}





if __name__ == "__main__":
    run_project(app=app)
