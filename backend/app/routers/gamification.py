"""Gamification: leaderboard, my badges, reward catalogue + redemption."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Reward, User, UserBadge
from ..schemas import LeaderboardEntry, RedeemRequest, RewardOut, UserBadgeOut
from ..services import gamification

router = APIRouter(prefix="/api", tags=["gamification"])


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return gamification.leaderboard(db)


@router.get("/my-badges", response_model=list[UserBadgeOut])
def my_badges(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(UserBadge).filter(UserBadge.user_id == user.id).all()


@router.get("/users/{user_id}/badges", response_model=list[UserBadgeOut])
def user_badges(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(UserBadge).filter(UserBadge.user_id == user_id).all()


@router.post("/rewards/redeem")
def redeem(payload: RedeemRequest, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    redemption = gamification.redeem_reward(db, user, payload.reward_id)
    return {
        "ok": True,
        "points_balance": user.points_balance,
        "redemption_id": redemption.id,
    }
