"""Gamification: badge auto-award, reward redemption, leaderboard
(Business Rules 4 & 5)."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Badge, Redemption, Reward, User, UserBadge
from .notifications import notify


def _metric_value(user: User, metric: str) -> int:
    return {
        "xp": user.xp,
        "completed_challenges": user.completed_challenges,
        "points_balance": user.points_balance,
    }.get(metric, 0)


def check_and_award_badges(db: Session, user: User) -> list[Badge]:
    """Award any badge whose unlock rule the user now satisfies (Rule 4).
    Idempotent — never awards the same badge twice. Returns newly awarded."""
    earned_ids = {ub.badge_id for ub in
                  db.query(UserBadge).filter(UserBadge.user_id == user.id).all()}
    newly: list[Badge] = []
    badge_q = db.query(Badge)
    if user.company_id:  # only this company's badges apply
        badge_q = badge_q.filter(Badge.company_id == user.company_id)
    for badge in badge_q.all():
        if badge.id in earned_ids:
            continue
        if _metric_value(user, badge.rule_metric) >= badge.rule_threshold:
            db.add(UserBadge(user_id=user.id, badge_id=badge.id))
            notify(db, user_id=user.id, title=f"Badge unlocked: {badge.name}",
                   message=badge.description or "", type="badge", commit=False)
            newly.append(badge)
    if newly:
        db.commit()
    return newly


def redeem_reward(db: Session, user: User, reward_id: int) -> Redemption:
    """Deduct points + decrement stock (Rule 5). Blocks on stock/balance."""
    reward = db.query(Reward).get(reward_id)
    if not reward or reward.status != "Active" or reward.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Reward not available")
    if reward.stock <= 0:
        raise HTTPException(status_code=400, detail="Reward out of stock")
    if user.points_balance < reward.points_required:
        raise HTTPException(status_code=400, detail="Insufficient points balance")

    user.points_balance -= reward.points_required
    reward.stock -= 1
    redemption = Redemption(user_id=user.id, reward_id=reward.id,
                            points_spent=reward.points_required)
    db.add(redemption)
    notify(db, user_id=user.id, title=f"Reward redeemed: {reward.name}",
           message=f"-{reward.points_required} points", type="info", commit=False)
    db.commit()
    db.refresh(redemption)
    return redemption


def leaderboard(db: Session, company_id: int | None = None) -> list[dict]:
    q = db.query(User)
    if company_id is not None:
        q = q.filter(User.company_id == company_id)
    users = q.order_by(User.xp.desc()).all()
    rows = []
    for u in users:
        badge_count = db.query(UserBadge).filter(UserBadge.user_id == u.id).count()
        rows.append({
            "user_id": u.id,
            "full_name": u.full_name,
            "department": u.department.name if u.department else None,
            "xp": u.xp,
            "points_balance": u.points_balance,
            "completed_challenges": u.completed_challenges,
            "badge_count": badge_count,
        })
    return rows
