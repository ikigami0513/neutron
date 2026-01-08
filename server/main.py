import os
import shutil
import uuid
import time
from datetime import datetime
from typing import List, Optional

import requests
from igdb_service import igdb

from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import FileResponse
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
    rom_filename = f"{uuid.uuid4()}_{rom.filename}"
    rom_path = os.path.join(UPLOAD_DIR, "roms", rom_filename)
    
    with open(rom_path, "wb+") as file_object:
        shutil.copyfileobj(rom.file, file_object)

    cover_db_path = None

    if cover:
        cover_filename = f"{uuid.uuid4()}_{cover.filename}"
        cover_real_path = os.path.join(UPLOAD_DIR, "covers", cover_filename)
        
        with open(cover_real_path, "wb+") as file_object:
            shutil.copyfileobj(cover.file, file_object)
        
        cover_db_path = f"covers/{cover_filename}"
    
    else:
        print("No cover provided. Attempting to scrape IGDB...")
        scraped_url = igdb.search_game(title)
        
        if scraped_url:
            try:
                img_data = requests.get(scraped_url).content
                
                cover_filename = f"{uuid.uuid4()}_scraped.jpg"
                cover_real_path = os.path.join(UPLOAD_DIR, "covers", cover_filename)
                
                with open(cover_real_path, "wb") as f:
                    f.write(img_data)
                
                cover_db_path = f"covers/{cover_filename}"
                print("Cover scraped and saved successfully.")
            except Exception as e:
                print(f"Error downloading scraped cover: {e}")

    db_game = models.Game(
        title=title,
        rom_path=f"roms/{rom_filename}",
        cover_path=cover_db_path,
        platform_id=platform_id
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

@app.post("/games/{game_id}/save")
def create_save(game_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    timestamp = int(time.time())
    filename = f"{game_id}_{timestamp}.sav"
    file_location = os.path.join("saves", filename)

    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    db_save = models.Save(
        file_path=file_location,
        game_id=game_id,
        created_at=datetime.utcnow()
    )
    db.add(db_save)
    db.commit()
    db.refresh(db_save)

    return {"info": "Save version created", "save_id": db_save.id}

@app.get("/games/{game_id}/save/latest")
def get_latest_save(game_id: int, db: Session = Depends(get_db)):
    latest_save = db.query(models.Save)\
        .filter(models.Save.game_id == game_id)\
        .order_by(models.Save.created_at.desc())\
        .first()

    if not latest_save or not os.path.exists(latest_save.file_path):
        raise HTTPException(status_code=404, detail="No save found for this game")

    return FileResponse(
        latest_save.file_path, 
        filename=f"{game_id}.sav",
        headers={"Cache-Control": "no-cache"} 
    )

@app.get("/games/{game_id}/save/latest/info")
def get_latest_save_info(game_id: int, db: Session = Depends(get_db)):
    latest_save = db.query(models.Save)\
        .filter(models.Save.game_id == game_id)\
        .order_by(models.Save.created_at.desc())\
        .first()

    if not latest_save:
        raise HTTPException(status_code=404, detail="No save found")

    return {
        "created_at": latest_save.created_at.isoformat(),
        "id": latest_save.id
    }
