from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    icon_path = Column(String, nullable=True)
    games = relationship("Game", back_populates="platform")

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)

    cover_path = Column(String, nullable=True)
    rom_path = Column(String, nullable=False)

    platform_id = Column(Integer, ForeignKey("platforms.id"))

    platform = relationship("Platform", back_populates="games")
    saves = relationship("Save", back_populates="game")
    

class Save(Base):
    __tablename__ = "saves"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    game_id = Column(Integer, ForeignKey("games.id"))
    game = relationship("Game", back_populates="saves")
