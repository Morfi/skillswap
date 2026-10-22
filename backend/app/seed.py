"""Начальные данные: администратор и демо-пользователи с навыками."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Skill, User
from .security import hash_password

DEMO_PASSWORD = "demo123"

DEMO_USERS = [
    ("anna@skillswap.dev", "Анна", "Москва", "Преподаю английский 5 лет, мечтаю играть на гитаре.", [
        ("offer", "Английский язык", "languages", "expert", "online", "Разговорный английский, подготовка к IELTS."),
        ("want", "Гитара", "music", "beginner", "offline", "Хочу научиться аккомпанировать себе."),
    ]),
    ("ivan@skillswap.dev", "Иван", "Москва", "Музыкант и бэкенд-разработчик.", [
        ("offer", "Гитара для начинающих", "music", "expert", "both", "Аккорды, бой, перебор, первые песни за месяц."),
        ("offer", "Python с нуля", "it", "intermediate", "online", "Основы Python и автоматизация рутины."),
        ("want", "Английский язык", "languages", "intermediate", "online", "Нужен разговорный для работы."),
    ]),
    ("maria@skillswap.dev", "Мария", "Санкт-Петербург", "Шеф-повар домашней кухни.", [
        ("offer", "Итальянская кухня", "cooking", "expert", "offline", "Паста, ризотто, тирамису."),
        ("want", "Python", "it", "beginner", "online", "Хочу автоматизировать учёт заказов."),
    ]),
    ("oleg@skillswap.dev", "Олег", "Казань", "Тренер по йоге и любитель рисования.", [
        ("offer", "Йога", "sport", "expert", "both", "Хатха-йога для начинающих, работа со спиной."),
        ("want", "Акварель", "art", "beginner", "offline", ""),
    ]),
]


def seed(db: Session) -> None:
    if not db.scalar(select(User).where(User.email == settings.admin_email)):
        db.add(User(
            email=settings.admin_email,
            username="Администратор",
            password_hash=hash_password(settings.admin_password),
            role="admin",
        ))

    if settings.seed_demo_data:
        for email, name, city, bio, skills in DEMO_USERS:
            if db.scalar(select(User).where(User.email == email)):
                continue
            user = User(email=email, username=name, city=city, bio=bio, password_hash=hash_password(DEMO_PASSWORD))
            user.skills = [
                Skill(kind=k, title=t, category=c, level=lvl, format=f, description=d)
                for k, t, c, lvl, f, d in skills
            ]
            db.add(user)
    db.commit()
