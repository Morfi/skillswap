"""Бизнес-логика: подбор партнёров для обмена и рейтинги."""

import re
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Exchange, Skill, User
from .schemas import ExchangeOut, Match, SkillOut, UserPublic

_WORD = re.compile(r"\w{3,}", re.UNICODE)


def skill_out(s: Skill) -> SkillOut:
    out = SkillOut.model_validate(s)
    out.owner_name = s.owner.username if s.owner else None
    out.owner_city = s.owner.city if s.owner else None
    return out


def exchange_out(e: Exchange) -> ExchangeOut:
    out = ExchangeOut.model_validate(e)
    out.requester_name = e.requester.username if e.requester else None
    out.receiver_name = e.receiver.username if e.receiver else None
    out.offered_skill_title = e.offered_skill.title if e.offered_skill else None
    out.requested_skill_title = e.requested_skill.title if e.requested_skill else None
    return out


def similarity(a: Skill, b: Skill) -> int:
    """0 — не похожи, 1 — одна категория, 3 — совпадают по названию."""
    ta, tb = a.title.lower(), b.title.lower()
    if ta in tb or tb in ta or set(_WORD.findall(ta)) & set(_WORD.findall(tb)):
        return 3
    if a.category == b.category:
        return 1
    return 0


def user_ratings(db: Session, user_ids: list[int] | None = None) -> dict[int, tuple[float, int]]:
    """Средняя оценка, которую пользователь получил от партнёров по завершённым обменам."""
    scores: dict[int, list[int]] = defaultdict(list)
    for e in db.scalars(select(Exchange).where(Exchange.status == "completed")):
        if e.requester_rating:  # оценку поставил requester -> она относится к receiver
            scores[e.receiver_id].append(e.requester_rating)
        if e.receiver_rating:
            scores[e.requester_id].append(e.receiver_rating)
    return {
        uid: (round(sum(v) / len(v), 2), len(v))
        for uid, v in scores.items()
        if user_ids is None or uid in user_ids
    }


def public_user(u: User, ratings: dict[int, tuple[float, int]]) -> UserPublic:
    out = UserPublic.model_validate(u)
    if u.id in ratings:
        out.rating, out.reviews = ratings[u.id]
    return out


def find_matches(db: Session, me: User) -> list[Match]:
    """Ищет партнёров: кто предлагает то, что я ищу, и/или ищет то, что я предлагаю.

    Взаимные совпадения (обе стороны что-то получают) всегда выше односторонних.
    """
    my = [s for s in me.skills if s.is_active]
    my_wants = [s for s in my if s.kind == "want"]
    my_offers = [s for s in my if s.kind == "offer"]
    if not my:
        return []

    others = db.scalars(
        select(Skill).join(User).where(Skill.owner_id != me.id, Skill.is_active.is_(True), User.is_blocked.is_(False))
    ).all()

    by_user: dict[int, dict] = {}
    for s in others:
        if s.kind == "offer":
            score = max((similarity(s, w) for w in my_wants), default=0)
            bucket = "they_offer"
        else:
            score = max((similarity(s, o) for o in my_offers), default=0)
            bucket = "they_want"
        if score == 0:
            continue
        entry = by_user.setdefault(s.owner_id, {"user": s.owner, "they_offer": [], "they_want": [], "score": 0})
        entry[bucket].append(s)
        entry["score"] += score

    ratings = user_ratings(db)
    matches = []
    for entry in by_user.values():
        mutual = bool(entry["they_offer"]) and bool(entry["they_want"])
        matches.append(
            Match(
                user=public_user(entry["user"], ratings),
                they_offer=[skill_out(s) for s in entry["they_offer"]],
                they_want=[skill_out(s) for s in entry["they_want"]],
                mutual=mutual,
                score=entry["score"] + (10 if mutual else 0),
            )
        )
    matches.sort(key=lambda m: (m.score, m.user.rating or 0), reverse=True)
    return matches
