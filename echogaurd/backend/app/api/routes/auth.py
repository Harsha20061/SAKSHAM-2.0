from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.repositories.user_repository import UserRepository
from app.models.schemas import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    CurrentUserResponse,
    UserSearchResponse,
)
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.api.dependencies import get_current_user
from app.db.models.user import User

router = APIRouter()

@router.post("/signup", response_model=CurrentUserResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)

    if await user_repo.exists_by_username(request.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    hashed_pwd = hash_password(request.password)
    user = await user_repo.create(
        username=request.username,
        display_name=request.display_name,
        password_hash=hashed_pwd
    )
    await db.commit()
    await db.refresh(user)

    return CurrentUserResponse(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        created_at=user.created_at
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_username(request.username)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not user.password_hash:
        raise credentials_exception

    if not verify_password(request.password, user.password_hash):
        raise credentials_exception

    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=CurrentUserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return CurrentUserResponse(
        id=str(current_user.id),
        username=current_user.username,
        display_name=current_user.display_name,
        created_at=current_user.created_at
    )

@router.get(
    "/users/search",
    response_model=list[UserSearchResponse],
)
async def search_users(
    q: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = q.strip()

    if not query:
        return []

    user_repo = UserRepository(db)

    users = await user_repo.search_users(
        query=query,
        exclude_user_id=current_user.id,
        limit=10,
    )

    return [
        UserSearchResponse(
            id=str(user.id),
            username=user.username,
            display_name=user.display_name,
        )
        for user in users
    ]
