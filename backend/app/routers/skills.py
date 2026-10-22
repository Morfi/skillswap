from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Skill, User
from ..schemas import CATEGORIES, Match, SkillIn, SkillOut
from ..services import find_matches, skill_out

router = APIRouter(prefix="/api/skills", tags=["skills"])


def _get_editable(db: Session, skill_id: int, user: User) -> Skill:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill not found")
    if user.role != "admin" and skill.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can modify only your own skills")
    return skill


@router.get("/categories", response_model=list[str])
def categories():
    return CATEGORIES


@router.get("", response_model=list[SkillOut])
def list_skills(
    kind: str | None = None,
    category: str | None = None,
    level: str | None = None,
    format: str | None = None,
    city: str | None = None,
    search: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Skill).join(User)
    if mine:
        q = q.where(Skill.owner_id == user.id)
    else:
        q = q.where(Skill.is_active.is_(True), User.is_blocked.is_(False))
    if kind:
        q = q.where(Skill.kind == kind)
    if category:
        q = q.where(Skill.category == category)
    if level:
        q = q.where(Skill.level == level)
    if format:
        q = q.where(or_(Skill.format == format, Skill.format == "both"))
    if city:
        q = q.where(User.city.ilike(f"%{city}%"))
    if search:
        q = q.where(or_(Skill.title.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%")))
    return [skill_out(s) for s in db.scalars(q.order_by(Skill.created_at.desc(), Skill.id.desc()))]


@router.get("/matches", response_model=list[Match])
def matches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return find_matches(db, user)


@router.post("", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
def create_skill(data: SkillIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    skill = Skill(**data.model_dump(), owner_id=user.id)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill_out(skill)


@router.get("/{skill_id}", response_model=SkillOut)
def get_skill(skill_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill not found")
    return skill_out(skill)


@router.put("/{skill_id}", response_model=SkillOut)
def update_skill(skill_id: int, data: SkillIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    skill = _get_editable(db, skill_id, user)
    for key, value in data.model_dump().items():
        setattr(skill, key, value)
    db.commit()
    db.refresh(skill)
    return skill_out(skill)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(skill_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(_get_editable(db, skill_id, user))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
