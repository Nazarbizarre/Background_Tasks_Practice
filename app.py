from typing import Annotated
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, status, HTTPException, Depends
from time import sleep
from pathlib import Path
from sqlmodel import SQLModel, Field, create_engine, Session, select
import uuid
import shutil
from uvicorn import run as run_project



UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class FileModel(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    progress: int = Field(default=0)
    

engine = create_engine("sqlite:///./files.db")
SQLModel.metadata.create_all(engine)
    

app = FastAPI()

def get_session():
    with Session(engine) as session:
        yield session

def generate_progress_updates(file_id: str, db: Session):
    file = db.exec(select(FileModel).where(FileModel.id == file_id)).first()
    for i in range(10):
        file.progress = i * 10 
        sleep(2)
    file.progress = 100
    db.commit()

async def process_file(file_path: Path, file_id: str, db: Session, background_tasks = BackgroundTasks):

    
    
    if file_path.suffix != ".txt":
        raise HTTPException(status_code=422, detail="Failed: Unsupported file format, please upload a .txt file")

    with open(file_path, "r") as ex_file:
        content = ex_file.read()
        word_count = len(content.split(" "))


    output_path = UPLOAD_DIR / f"{file_path.stem}_word_count.txt"
    with open(output_path, "w") as f:
        f.write(f"Word Count: {word_count}")
    
    background_tasks.add_task(generate_progress_updates, file_id, db)

    if file_path.exists():
        file_path.unlink()

            
            
@app.post("/upload/")
async def upload_file(file: UploadFile, background_tasks: BackgroundTasks, status_code=status.HTTP_202_ACCEPTED, db = Depends(get_session)):
    file_id = str(uuid.uuid4())
    filemodel = FileModel(name=file.filename, id=file_id)
    db.add(filemodel)
    db.commit()
    db.refresh(filemodel)

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "w+b") as f:
        shutil.copyfileobj(file.file, f)


    background_tasks.add_task(process_file, file_path, filemodel.id, db, background_tasks)
    return {"message": f"File {file.filename} is being proccessed in the background", "task_id": filemodel.id}


@app.get("/tasks/{task_id}")
def get_task_status(file_id: str, db: Session = Depends(get_session)):
    file = db.exec(select(FileModel).where(FileModel.id == file_id)).first()
    if not file:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": file.id, "file_name": file.name, "status": file.progress}





if __name__ == "__main__":
    run_project(app=app)
