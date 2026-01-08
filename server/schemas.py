from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class PlatformBase(BaseModel):
    name: str
    icon_path: Optional[str] = None

class PlatformCreate(PlatformBase):
    pass

class Platform(PlatformBase):
    id: int
    
    class Config:
        from_attributes = True

class SaveBase(BaseModel):
    file_path: str

class SaveCreate(SaveBase):
    game_id: int

class Save(SaveBase):
    id: int
    created_at: datetime
    game_id: int

    class Config:
        from_attributes = True

class GameBase(BaseModel):
    title: str
    rom_path: str
    cover_path: Optional[str] = None

class GameCreate(GameBase):
    platform_id: int

class Game(GameBase):
    id: int
    platform_id: int
    platform: Optional[Platform] = None
    saves: List[Save] = []

    class Config:
        from_attributes = True
        