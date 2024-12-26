from fastapi import FastAPI, Request, Depends, HTTPException, File, Form, UploadFile, Query
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.sessions import SessionMiddleware
from database import engine, get_db
from models import Base, News, Achievement, AchievementPhoto
from crud import create_news, create_achievement
from typing import List
from sqlalchemy import extract, func
from datetime import datetime, timedelta


app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory="templates")
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        request.session["user"] = username
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    raise HTTPException(status_code=400, detail="Invalid username or password")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


def truncate_words(content, word_limit):
    words = content.split()
    return ' '.join(words[:word_limit]) + ('...' if len(words) > word_limit else '')

templates.env.filters['truncate_words'] = truncate_words


@app.get("/", response_class=HTMLResponse)
def homepage(request: Request, db: Session = Depends(get_db)):
    latest_news = db.query(News).order_by(News.created_at.desc()).limit(4).all()
    return templates.TemplateResponse("index.html", {"request": request, "news": latest_news})


@app.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=302)

    news = db.query(News).all()
    achievements = db.query(Achievement).all()
    achievement_images = {
        achievement.id: db.query(AchievementPhoto).filter(AchievementPhoto.achievement_id == achievement.id).all()
        for achievement in achievements
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "news": news,
            "achievements": achievements,
            "achievement_images": achievement_images,
        },
    )


@app.get("/actual_news", response_class=HTMLResponse)
def actual_news(request: Request, page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    print("Полученный параметр page:", page)
    page_size = 8
    total_news = db.query(News).count()
    total_pages = (total_news + page_size - 1) // page_size

    if page > total_pages and total_pages > 0:
        page = total_pages

    news = db.query(News).offset((page - 1) * page_size).limit(page_size).all()

    return templates.TemplateResponse(
        "actual_news.html",
        {
            "request": request,
            "news": news,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@app.get("/news/{news_id}", response_class=HTMLResponse)
def single_news(news_id: int, request: Request, db: Session = Depends(get_db)):

    news_item = db.query(News).filter(News.id == news_id).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    recent_news = (
        db.query(News)
        .filter(News.id != news_id)
        .order_by(News.created_at.desc())
        .limit(3)
        .all()
    )

    return templates.TemplateResponse(
        "single_news.html",
        {
            "request": request,
            "news_item": news_item,
            "recent_news": recent_news,
        },
    )


@app.get("/achievements_archive/", response_class=HTMLResponse)
def achievements_archive(
    request: Request,
    db: Session = Depends(get_db),
    sport: str = Query("", alias="sport"),
    year: str = Query("", alias="year"),
    athlete: str = Query("", alias="athlete"),
    page: int = Query(1, ge=1)
):
    page_size = 8
    query = db.query(Achievement)

    # Фильтрация
    if sport:
        query = query.filter(Achievement.sport_type.ilike(f"%{sport}%"))
    if year:
        query = query.filter(extract('year', Achievement.event_date) == int(year))
    if athlete:
        query = query.filter(Achievement.athlete_name.ilike(f"%{athlete}%"))

    total_achievements = query.count()
    total_pages = (total_achievements + page_size - 1) // page_size

    achievements = query.offset((page - 1) * page_size).limit(page_size).all()

    years = db.query(extract('year', Achievement.event_date)).distinct().all()
    years = [year[0] for year in years if year[0] is not None]

    sport_types = db.query(Achievement.sport_type).distinct().all()
    sport_types = [sport[0] for sport in sport_types]

    names = db.query(Achievement.athlete_name).distinct().all()
    names = [name[0] for name in names]

    return templates.TemplateResponse(
        "achievements_archive.html",
        {
            "request": request,
            "achievements": achievements,
            "current_page": page,
            "total_pages": total_pages,
            "years": sorted(set(years)),
            "sport_types": sorted(set(sport_types)),
            "names": sorted(set(names)),
            "selected_sport": sport,
            "selected_year": year,
            "selected_athlete": athlete
        },
    )


@app.get("/achievements/{achievement_id}", response_class=HTMLResponse)
def achievement_detail(achievement_id: int, request: Request, db: Session = Depends(get_db)):
    achievement = db.query(Achievement).filter(Achievement.id == achievement_id).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    other_achievements = db.query(Achievement).filter(Achievement.id != achievement_id).limit(5).all()

    return templates.TemplateResponse("single_achievement.html", {
        "request": request,
        "achievement": achievement,
        "other_achievements": other_achievements
    })


@app.get("/achievements/{achievement_id}/gallery", response_class=HTMLResponse)
def achievement_gallery(achievement_id: int, request: Request, db: Session = Depends(get_db)):
    achievement = db.query(Achievement).filter(Achievement.id == achievement_id).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Достижение не найдено")

    photos = db.query(AchievementPhoto).filter(AchievementPhoto.achievement_id == achievement_id).all()

    return templates.TemplateResponse(
        "achievement_gallery.html",
        {"request": request, "photos": photos, "achievement": achievement}
    )


@app.get("/gallery", response_class=HTMLResponse)
def gallery_page(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1)
):
    page_size = 8
    total_achievements = db.query(Achievement).count()
    total_pages = (total_achievements + page_size - 1) // page_size

    achievements = (
        db.query(Achievement)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return templates.TemplateResponse(
        "gallery.html",
        {
            "request": request,
            "achievements": achievements,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request, db: Session = Depends(get_db)):
    random_photos = db.query(AchievementPhoto).order_by(func.random()).limit(4).all()
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "random_photos": random_photos}
    )




@app.post("/news/")
def add_news(
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    image_data = image.file.read()
    news = create_news(db=db, title=title, content=content, image=image_data)
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@app.get("/news/{news_id}/image")
def get_news_image(news_id: int, db: Session = Depends(get_db)):
    news_item = db.query(News).filter(News.id == news_id).first()
    if not news_item or not news_item.image_data:
        raise HTTPException(status_code=404, detail="Изображение не найдено")

    return Response(content=news_item.image_data, media_type="image/png")


@app.get("/news/{news_id}/delete")
def delete_news(news_id: int, db: Session = Depends(get_db)):
    news_item = db.query(News).filter(News.id == news_id).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    db.delete(news_item)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@app.post("/news/{news_id}/edit")
def edit_news(
    news_id: int,
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    news_item = db.query(News).filter(News.id == news_id).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    news_item.title = title
    news_item.content = content

    if image and image.filename:
        news_item.image_data = image.file.read()

    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@app.post("/achievements/")
async def add_achievement(
    title: str = Form(...),
    sport_type: str = Form(...),
    athlete_name: str = Form(...),
    event_date: str = Form(...),
    event_place: str = Form(...),
    description: str = Form(...),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    image_data_list = [await image.read() for image in images]
    create_achievement(
        db,
        title=title,
        sport_type=sport_type,
        athlete_name=athlete_name,
        event_date=event_date,
        event_place=event_place,
        description=description,
        images=image_data_list,
    )
    return RedirectResponse("/admin/dashboard", status_code=303)



@app.get("/news/{news_id}/image")
def get_news_image(news_id: int, db: Session = Depends(get_db)):
    news = db.query(News).filter(News.id == news_id).first()
    if not news or not news.image_data:
        raise HTTPException(status_code=404, detail="Изображение не найдено")
    return Response(content=news.image_data, media_type="image/png")


@app.get("/achievements/{achievement_id}/image/{image_id}")
def get_achievement_image(achievement_id: int, image_id: int, db: Session = Depends(get_db)):
    image = db.query(AchievementPhoto).filter(
        AchievementPhoto.achievement_id == achievement_id,
        AchievementPhoto.id == image_id
    ).first()

    if not image or not image.image_data:
        raise HTTPException(status_code=404, detail="Изображение не найдено")

    return Response(content=image.image_data, media_type="image/png")


@app.get("/achievements/{achievement_id}/delete")
def delete_achievement(achievement_id: int, db: Session = Depends(get_db)):
    achievement = db.query(Achievement).filter(Achievement.id == achievement_id).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    achievement_images = db.query(AchievementPhoto).filter(AchievementPhoto.achievement_id == achievement_id).all()
    for image in achievement_images:
        db.delete(image)

    db.delete(achievement)
    db.commit()

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@app.post("/achievements/{achievement_id}/edit")
def edit_achievement(
    achievement_id: int,
    title: str = Form(...),
    sport_type: str = Form(...),
    athlete_name: str = Form(...),
    event_date: str = Form(...),
    event_place: str = Form(...),
    description: str = Form(...),
    new_images: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    achievement = db.query(Achievement).filter(Achievement.id == achievement_id).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Достижение не найдено")

    try:
        event_date_converted = datetime.strptime(event_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD.")

    achievement.title = title
    achievement.sport_type = sport_type
    achievement.athlete_name = athlete_name
    achievement.event_date = event_date_converted
    achievement.event_place = event_place
    achievement.description = description

    #print(new_images)
    if new_images:
        db.query(AchievementPhoto).filter(AchievementPhoto.achievement_id == achievement.id).delete()

        for image in new_images:
            if image.filename:
                image_data = image.file.read()
                new_image = AchievementPhoto(
                    achievement_id=achievement.id,
                    image_data=image_data
                )
                db.add(new_image)

    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)


VALID_USERNAME = "admin"
VALID_PASSWORD = "admin"



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)































