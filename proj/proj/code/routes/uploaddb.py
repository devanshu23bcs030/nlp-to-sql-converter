from fastapi import APIRouter, File, UploadFile
import uuid
import shutil
import os
from globals import session_map

router = APIRouter()

UPLOAD_FOLDER = "temp_db_files"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/upload_db/")
async def upload_db(file: UploadFile = File(...)):
    if not file.filename.endswith(".db"):
        return {"error": "Only .db files are allowed"}

    temp_filename = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{file.filename}")
    with open(temp_filename, "wb") as f:
        shutil.copyfileobj(file.file, f)

    session_token = str(uuid.uuid4())
    session_map[session_token] = temp_filename

    return {"session_token": session_token}