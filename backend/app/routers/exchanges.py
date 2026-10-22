from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Exchange, Skill, User
from ..schemas import ExchangeIn, ExchangeOut, ExchangeUpdate, RatingIn, StatusUpdate
from ..services import exchange_out

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])

# Кто и в какой статус может перевести заявку: (текущий статус, новый статус) -> роли участника
TRANSITIONS = {
    ("pending", "accepted"): {"receiver"},
    ("pending", "declined"): {"receiver"},
    ("pending", "cancelled"): {"requester"},
    ("accepted", "cancelled"): {"requester", "receiver"},
    ("accepted", "completed"): {"requester", "receiver"},
}


def _participant_role(e: Exchange, user: User) -> str | None:
    if e.requester_id == user.id:
        return "requester"
    if e.receiver_id == user.id:
        return "receiver"
    return None


def _get_visible(db: Session, exchange_id: int, user: User) -> Exchange:
    e = db.get(Exchange, exchange_id)
    if e is None or (_participant_role(e, user) is None and user.role != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exchange not found")
    return e


def _check_offered(db: Session, skill_id: int | None, user: User) -> None:
    if skill_id is None:
        return
    offered = db.get(Skill, skill_id)
    if offered is None or offered.owner_id != user.id or offered.kind != "offer":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "offered_skill_id must be your own 'offer' skill")


@router.get("", response_model=list[ExchangeOut])
def list_exchanges(
    direction: str = Query("all", pattern="^(all|incoming|outgoing)$"),
    status_filter: str | None = Query(None, alias="status"),
    all_users: bool = Query(False, description="Только для admin: заявки всех пользователей"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Exchange)
    if not (all_users and user.role == "admin"):
        if direction == "incoming":
            q = q.where(Exchange.receiver_id == user.id)
        elif direction == "outgoing":
            q = q.where(Exchange.requester_id == user.id)
        else:
            q = q.where(or_(Exchange.receiver_id == user.id, Exchange.requester_id == user.id))
    if status_filter:
        q = q.where(Exchange.status == status_filter)
    return [exchange_out(e) for e in db.scalars(q.order_by(Exchange.created_at.desc(), Exchange.id.desc()))]


@router.post("", response_model=ExchangeOut, status_code=status.HTTP_201_CREATED)
def create_exchange(data: ExchangeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    requested = db.get(Skill, data.requested_skill_id)
    if requested is None or not requested.is_active or requested.kind != "offer":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "requested_skill_id must be an active 'offer' skill")
    if requested.owner_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot request your own skill")
    _check_offered(db, data.offered_skill_id, user)
    duplicate = db.scalar(
        select(Exchange).where(
            Exchange.requester_id == user.id,
            Exchange.requested_skill_id == requested.id,
            Exchange.status.in_(["pending", "accepted"]),
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an active request for this skill")
    e = Exchange(
        requester_id=user.id,
        receiver_id=requested.owner_id,
        requested_skill_id=requested.id,
        offered_skill_id=data.offered_skill_id,
        message=data.message,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return exchange_out(e)


@router.get("/{exchange_id}", response_model=ExchangeOut)
def get_exchange(exchange_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return exchange_out(_get_visible(db, exchange_id, user))


@router.put("/{exchange_id}", response_model=ExchangeOut)
def update_exchange(
    exchange_id: int, data: ExchangeUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    e = _get_visible(db, exchange_id, user)
    if e.requester_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the requester can edit the request")
    if e.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only pending requests can be edited")
    _check_offered(db, data.offered_skill_id, user)
    e.offered_skill_id = data.offered_skill_id
    e.message = data.message
    db.commit()
    db.refresh(e)
    return exchange_out(e)


@router.patch("/{exchange_id}/status", response_model=ExchangeOut)
def change_status(
    exchange_id: int, data: StatusUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    e = _get_visible(db, exchange_id, user)
    allowed = TRANSITIONS.get((e.status, data.status))
    if not allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot change status from {e.status} to {data.status}")
    if _participant_role(e, user) not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not allowed to make this transition")
    e.status = data.status
    db.commit()
    db.refresh(e)
    return exchange_out(e)


@router.post("/{exchange_id}/rate", response_model=ExchangeOut)
def rate_exchange(
    exchange_id: int, data: RatingIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    e = _get_visible(db, exchange_id, user)
    role = _participant_role(e, user)
    if role is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only participants can rate")
    if e.status != "completed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only completed exchanges can be rated")
    field = f"{role}_rating"
    if getattr(e, field) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already rated this exchange")
    setattr(e, field, data.rating)
    db.commit()
    db.refresh(e)
    return exchange_out(e)


@router.delete("/{exchange_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exchange(exchange_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = _get_visible(db, exchange_id, user)
    if user.role != "admin":
        if e.requester_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the requester can delete the request")
        if e.status not in ("pending", "declined", "cancelled"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Accepted or completed exchanges cannot be deleted")
    db.delete(e)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
