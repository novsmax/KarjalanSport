from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

Base = declarative_base()

class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    image_data = Column(LargeBinary)  # Для хранения изображений
    created_at = Column(DateTime, default=datetime.utcnow)

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    sport_type = Column(String, nullable=False)
    athlete_name = Column(String, nullable=False)
    event_date = Column(Date, nullable=False)
    event_place = Column(String, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    photos = relationship("AchievementPhoto", back_populates="achievement")


class AchievementPhoto(Base):
    __tablename__ = "achievement_photos"

    id = Column(Integer, primary_key=True, index=True)
    image_data = Column(LargeBinary, nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    achievement = relationship("Achievement", back_populates="photos")

Base.metadata.create_all(bind=engine)
