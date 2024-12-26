from sqlalchemy.orm import Session
from models import News, Achievement, AchievementPhoto
from datetime import datetime

def create_news(db: Session, title: str, content: str, image: bytes):
    db_news = News(
        title=title,
        content=content,
        image_data=image
    )
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return db_news

def create_achievement(db: Session, title: str, sport_type: str, athlete_name: str, event_date: str, event_place: str, description: str, images: list[bytes]):
    event_date_converted = datetime.strptime(event_date, "%Y-%m-%d").date()

    db_achievement = Achievement(
        title=title,
        sport_type=sport_type,
        athlete_name=athlete_name,
        event_date=event_date_converted,
        event_place=event_place,
        description=description,
    )
    db.add(db_achievement)
    db.commit()

    for image_data in images:
        db_image = AchievementPhoto(achievement_id=db_achievement.id, image_data=image_data)
        db.add(db_image)
    db.commit()

    db.refresh(db_achievement)
    return db_achievement
