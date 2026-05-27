from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.security import create_admin_token, require_admin
from database import get_session
from schemas import LoginRequest, LoginResponse, StatusUpdateRequest
from services import admin as admin_service

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    if (
        payload.login != settings.ADMIN_LOGIN
        or payload.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    return {
        "access_token": create_admin_token(),
        "admin": {"login": settings.ADMIN_LOGIN, "role": "admin"},
    }


@router.get("/auth/me")
async def me(admin=Depends(require_admin)):
    return {"login": admin.get("sub"), "role": "admin"}


@router.get("/dashboard/stats")
async def dashboard_stats(
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_admin),
):
    return await admin_service.dashboard_stats(session)


@router.get("/orders")
async def list_orders(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_admin),
):
    return await admin_service.list_orders(session, status_filter, search)


@router.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_admin),
):
    return await admin_service.get_order(session, order_id)


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    payload: StatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_admin),
):
    return await admin_service.update_order_status(
        session, order_id, payload.status
    )


@router.get("/users")
async def list_users(
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_admin),
):
    return await admin_service.list_users(session, search)


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_admin),
):
    return await admin_service.get_user(session, user_id)


@router.get("/users/{user_id}/orders")
async def get_user_orders(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_admin),
):
    return await admin_service.user_orders(session, user_id)


@router.get("/payments/providers")
async def payment_providers(admin=Depends(require_admin)):
    return admin_service.payment_providers()


@router.get("/payments/settings")
async def payment_settings(admin=Depends(require_admin)):
    return admin_service.payment_settings()
