from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import Exchange, Skill, User
from ..schemas import BlockUpdate, RoleUpdate, SkillOut, UserOut, UserPublic
from ..services import public_user, skill_out, user_ratings

router = APIRouter(tags=["users"])


@router.get("/api/users/{user_id}", response_model=UserPublic)
def get_profile(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return public_user(user, user_ratings(db, [user_id]))


@router.get("/api/users/{user_id}/skills", response_model=list[SkillOut])
def get_user_skills(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    skills = db.scalars(select(Skill).where(Skill.owner_id == user_id, Skill.is_active.is_(True)))
    return [skill_out(s) for s in skills]


# ---------- admin ----------
def _target(db: Session, user_id: int, admin: User) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot apply this action to yourself")
    return user


@router.get("/api/admin/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.patch("/api/admin/users/{user_id}/role", response_model=UserOut)
def change_role(user_id: int, data: RoleUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _target(db, user_id, admin)
    user.role = data.role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/api/admin/users/{user_id}/block", response_model=UserOut)
def block_user(user_id: int, data: BlockUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _target(db, user_id, admin)
    user.is_blocked = data.is_blocked
    db.commit()
    db.refresh(user)
    return user


@router.delete("/api/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    db.delete(_target(db, user_id, admin))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/admin/stats")
def system_stats(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    by_status = dict(db.execute(select(Exchange.status, func.count(Exchange.id)).group_by(Exchange.status)).all())
    by_category = dict(db.execute(select(Skill.category, func.count(Skill.id)).group_by(Skill.category)).all())
    return {
        "users": db.scalar(select(func.count(User.id))),
        "skills": db.scalar(select(func.count(Skill.id))),
        "exchanges": db.scalar(select(func.count(Exchange.id))),
        "exchanges_by_status": by_status,
        "skills_by_category": by_category,
    }
