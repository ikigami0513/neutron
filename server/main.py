import os
import shutil
import uuid
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import models
import schemas
from database import SessionLocal, engine

app = FastAPI()

UPLOAD_DIR = "media"

os.makedirs(os.path.join(UPLOAD_DIR, "roms"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "covers"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "saves"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "icons"), exist_ok=True)

app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_upload_file(upload_file: UploadFile, subfolder: str) -> str:
    _, ext = os.path.splitext(upload_file.filename)
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    folder_path = os.path.join(UPLOAD_DIR, subfolder)
    file_path = os.path.join(folder_path, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    return f"{subfolder}/{unique_filename}"

@app.post("/platforms/", response_model=schemas.Platform)
def create_platform(
    name: str = Form(...),
    icon: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    icon_path = None
    if icon:
        icon_path = save_upload_file(icon, "icons")

    db_platform = models.Platform(name=name, icon_path=icon_path)
    db.add(db_platform)
    db.commit()
    db.refresh(db_platform)
    return db_platform

@app.get("/platforms/", response_model=List[schemas.Platform])
def read_platforms(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(models.Platform).offset(skip).limit(limit).all()

@app.get("/platforms/{platform_id}", response_model=schemas.Platform)
def read_platform(platform_id: int, db: Session = Depends(get_db)):
    platform = db.query(models.Platform).filter(models.Platform.id == platform_id).first()
    if platform is None:
        raise HTTPException(status_code=404, detail="Platform not found")
    return platform


@app.post("/games/", response_model=schemas.Game)
def create_game(
    title: str = Form(...),
    platform_id: int = Form(...),
    rom: UploadFile = File(...),
    cover: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    platform = db.query(models.Platform).filter(models.Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    rom_path = save_upload_file(rom, "roms")
    
    cover_path = None
    if cover:
        cover_path = save_upload_file(cover, "covers")

    db_game = models.Game(
        title=title,
        platform_id=platform_id,
        rom_path=rom_path,
        cover_path=cover_path
    )
    
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game

@app.get("/games/", response_model=List[schemas.Game])
def read_games(
    skip: int = 0, 
    limit: int = 100, 
    platform_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Game)

    if platform_id is not None:
        query = query.filter(models.Game.platform_id == platform_id)

    if search:
        query = query.filter(models.Game.title.ilike(f"%{search}%"))

    return query.offset(skip).limit(limit).all()

@app.post("/saves/", response_model=schemas.Save)
def create_save(
    game_id: int = Form(...),
    save_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    file_path = save_upload_file(save_file, "saves")

    db_save = models.Save(
        game_id=game_id,
        file_path=file_path
    )

    db.add(db_save)
    db.commit()
    db.refresh(db_save)
    return db_save
