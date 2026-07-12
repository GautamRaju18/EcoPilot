"""Master-data CRUD. A small factory generates list/get/create/update/delete
for each master entity so the code stays DRY (Backend/M1 zone)."""
from typing import Type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["master-data"])


def _register(model: Type, create_schema: Type[BaseModel], out_schema: Type[BaseModel],
              path: str, name: str):
    manager = require_roles("Manager")  # writes: Manager/Admin only

    @router.get(f"/{path}", response_model=list[out_schema], name=f"list_{name}")
    def list_items(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
        return db.query(model).all()

    @router.get(f"/{path}/{{item_id}}", response_model=out_schema, name=f"get_{name}")
    def get_item(item_id: int, db: Session = Depends(get_db),
                 _: models.User = Depends(get_current_user)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{name} not found")
        return obj

    @router.post(f"/{path}", response_model=out_schema, name=f"create_{name}")
    def create_item(payload: create_schema, db: Session = Depends(get_db),
                    _: models.User = Depends(manager)):
        obj = model(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @router.put(f"/{path}/{{item_id}}", response_model=out_schema, name=f"update_{name}")
    def update_item(item_id: int, payload: create_schema, db: Session = Depends(get_db),
                    _: models.User = Depends(manager)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{name} not found")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return obj

    @router.delete(f"/{path}/{{item_id}}", name=f"delete_{name}")
    def delete_item(item_id: int, db: Session = Depends(get_db),
                    _: models.User = Depends(manager)):
        obj = db.query(model).get(item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{name} not found")
        db.delete(obj)
        db.commit()
        return {"ok": True}


_register(models.Department, schemas.DepartmentCreate, schemas.DepartmentOut,
          "departments", "department")
_register(models.Category, schemas.CategoryCreate, schemas.CategoryOut,
          "categories", "category")
_register(models.EmissionFactor, schemas.EmissionFactorCreate, schemas.EmissionFactorOut,
          "emission-factors", "emission_factor")
_register(models.ProductESGProfile, schemas.ProductCreate, schemas.ProductOut,
          "products", "product")
_register(models.EnvironmentalGoal, schemas.GoalCreate, schemas.GoalOut,
          "goals", "goal")
_register(models.ESGPolicy, schemas.PolicyCreate, schemas.PolicyOut,
          "policies", "policy")
_register(models.Badge, schemas.BadgeCreate, schemas.BadgeOut,
          "badges", "badge")
_register(models.Reward, schemas.RewardCreate, schemas.RewardOut,
          "rewards", "reward")


# Users list (for pickers / admin) — read-only here
@router.get("/users", response_model=list[schemas.UserOut], name="list_users")
def list_users(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return db.query(models.User).all()
