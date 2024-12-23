from pydantic import BaseModel

class NewsCreate(BaseModel):
    title: str
    content: str

class AchievementCreate(BaseModel):
    title: str
    athlete_name: str
    event_date: str
    description: str
