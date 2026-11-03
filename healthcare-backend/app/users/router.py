"""Authenticated current-user profile endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.auth.schemas import UserRead
from app.core.database import get_db
from app.users.schemas import UserProfileUpdate
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me", response_model=UserRead)
def update_me(
    data: UserProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> UserRead:
    return UserService(db).update_me(data, actor)
