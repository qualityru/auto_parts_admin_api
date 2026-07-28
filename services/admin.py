from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from models import Order, OrderItem, OrderStatus, User, UserAuth, UserProfile
from services.broker import publish_event
from schemas import UserProfileUpdateRequest


ACTIVE_STATUSES = {
    OrderStatus.created,
    OrderStatus.confirmed,
    OrderStatus.processing,
    OrderStatus.shipped,
}


def money(value) -> float:
    return float(Decimal(str(value or 0)))


def status_value(value) -> str:
    return value.value if isinstance(value, OrderStatus) else str(value)


def full_name(profile: UserProfile | None) -> str:
    if not profile:
        return ""
    return " ".join(
        item
        for item in [profile.last_name, profile.first_name, profile.middle_name]
        if item
    )


def supplier_name(item: OrderItem) -> str:
    warehouse = item.warehouse_snapshot or {}
    product = item.product_snapshot or {}
    info = warehouse.get("supplier_info") or product.get("supplier_info") or {}
    original = info.get("original_data") or warehouse.get("original_data") or {}
    for value in [
        info.get("name"),
        info.get("title"),
        original.get("supplier_name"),
        original.get("supplier"),
        original.get("provider"),
        warehouse.get("supplier_name"),
        warehouse.get("supplier"),
        product.get("supplier_name"),
        product.get("supplier"),
        item.warehouse_name,
    ]:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Поставщик не указан"


def supplier_article(item: OrderItem) -> str:
    warehouse = item.warehouse_snapshot or {}
    product = item.product_snapshot or {}
    info = warehouse.get("supplier_info") or product.get("supplier_info") or {}
    original = info.get("original_data") or warehouse.get("original_data") or {}
    for value in [
        original.get("supplier_article"),
        original.get("article"),
        original.get("ARTICLE"),
        original.get("art"),
        original.get("code"),
        original.get("PIN"),
        info.get("article"),
        info.get("code"),
        warehouse.get("supplier_article"),
        warehouse.get("article"),
        product.get("supplier_article"),
        product.get("article"),
        item.article,
    ]:
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def serialize_order_item(item: OrderItem) -> dict:
    product = item.product_snapshot or {}
    images = product.get("images") if isinstance(product.get("images"), list) else []
    return {
        "id": item.id,
        "product_id": item.product_id,
        "warehouse_id": item.warehouse_id,
        "brand": item.brand,
        "article": item.article,
        "supplier_article": supplier_article(item),
        "name": item.name,
        "image": item.image or product.get("image") or (images[0] if images else ""),
        "supplier": supplier_name(item),
        "warehouse_name": item.warehouse_name,
        "price": money(item.price),
        "quantity": item.quantity,
        "total": money(item.price) * item.quantity,
        "return_type": item.return_type,
        "fail_percent": money(item.fail_percent),
    }


def serialize_order(order: Order) -> dict:
    return {
        "id": order.id,
        "user_id": order.user_id,
        "status": status_value(order.status),
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "delivery_address": order.delivery_address,
        "comment": order.comment,
        "total_amount": money(order.total_amount),
        "profit_amount": round(money(order.total_amount) * settings.MARKUP_PART / 100, 2),
        "currency": order.currency,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": [serialize_order_item(item) for item in order.items],
    }


def serialize_user(user: User, orders_count: int = 0, orders_sum: float = 0) -> dict:
    profile = user.profile
    return {
        "id": user.id,
        "enable": user.enable,
        "full_name": full_name(profile),
        "first_name": profile.first_name if profile else "",
        "last_name": profile.last_name if profile else "",
        "middle_name": profile.middle_name if profile else "",
        "phone": profile.phone if profile else "",
        "email": profile.email if profile else "",
        "delivery_address": profile.delivery_address if profile else "",
        "auths": user.auths_map,
        "orders_count": orders_count,
        "orders_sum": round(orders_sum, 2),
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


async def dashboard_stats(session: AsyncSession) -> dict:
    total_orders = await session.scalar(select(func.count()).select_from(Order)) or 0
    total_amount = await session.scalar(select(func.coalesce(func.sum(Order.total_amount), 0))) or 0
    total_users = await session.scalar(select(func.count()).select_from(User)) or 0
    active_orders = await session.scalar(
        select(func.count()).select_from(Order).where(Order.status.in_(ACTIVE_STATUSES))
    ) or 0
    cancelled_orders = await session.scalar(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.cancelled)
    ) or 0
    recent_result = await session.execute(
        select(Order).options(selectinload(Order.items)).order_by(desc(Order.created_at)).limit(8)
    )
    total = money(total_amount)
    return {
        "orders_count": total_orders,
        "orders_amount": total,
        "revenue_amount": total,
        "markup_part": settings.MARKUP_PART,
        "profit_amount": round(total * settings.MARKUP_PART / 100, 2),
        "users_count": total_users,
        "active_orders_count": active_orders,
        "cancelled_orders_count": cancelled_orders,
        "recent_orders": [serialize_order(order) for order in recent_result.scalars().unique().all()],
    }


async def list_orders(session: AsyncSession, status_filter: str | None, search: str | None) -> list[dict]:
    query = select(Order).options(selectinload(Order.items)).order_by(desc(Order.created_at))
    filters = []
    if status_filter:
        filters.append(Order.status == OrderStatus(status_filter))
    if search:
        pattern = f"%{search.strip()}%"
        search_filters = [
            Order.customer_name.ilike(pattern),
            Order.customer_phone.ilike(pattern),
        ]
        if search.strip().isdigit():
            search_filters.append(Order.id == int(search.strip()))
        query = query.outerjoin(OrderItem)
        search_filters.extend([OrderItem.article.ilike(pattern), OrderItem.name.ilike(pattern)])
        filters.append(or_(*search_filters))
    if filters:
        query = query.where(and_(*filters))
    result = await session.execute(query.limit(200))
    return [serialize_order(order) for order in result.scalars().unique().all()]


async def get_order(session: AsyncSession, order_id: int) -> dict:
    order = await session.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return serialize_order(order)


async def update_order_status(session: AsyncSession, order_id: int, next_status: str) -> dict:
    order = await session.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order.status = OrderStatus(next_status)
    await session.commit()
    await session.refresh(order)
    await publish_event(
        settings.BROKER_ORDER_STATUS_ROUTING_KEY,
        {
            "event": "orders.status.changed",
            "source": "admin_backend",
            "order_id": order.id,
            "user_id": order.user_id,
            "status": next_status,
        },
    )
    return await get_order(session, order_id)


async def list_users(session: AsyncSession, search: str | None) -> list[dict]:
    query = select(User).options(selectinload(User.profile), selectinload(User.auths).selectinload(UserAuth.provider))
    if search:
        pattern = f"%{search.strip()}%"
        query = (
            query.outerjoin(UserProfile)
            .outerjoin(UserAuth)
            .where(
                or_(
                    UserProfile.first_name.ilike(pattern),
                    UserProfile.last_name.ilike(pattern),
                    UserProfile.middle_name.ilike(pattern),
                    UserProfile.phone.ilike(pattern),
                    UserProfile.email.ilike(pattern),
                    UserAuth.subject.ilike(pattern),
                )
            )
        )
    result = await session.execute(query.order_by(desc(User.created_at)).limit(200))
    users = result.scalars().unique().all()
    stats_result = await session.execute(
        select(
            Order.user_id,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        ).group_by(Order.user_id)
    )
    stats = {row[0]: (row[1], money(row[2])) for row in stats_result.all()}
    return [serialize_user(user, *(stats.get(user.id, (0, 0)))) for user in users]


async def get_user(session: AsyncSession, user_id: int) -> dict:
    user = await session.scalar(
        select(User)
        .options(selectinload(User.profile), selectinload(User.auths).selectinload(UserAuth.provider))
        .where(User.id == user_id)
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    orders = await user_orders(session, user_id)
    return serialize_user(user, len(orders), sum(order["total_amount"] for order in orders)) | {"orders": orders}


async def update_user_profile(
    session: AsyncSession, user_id: int, payload: UserProfileUpdateRequest
) -> dict:
    user = await session.scalar(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == user_id)
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    profile = user.profile
    if not profile:
        profile = UserProfile(user_id=user.id)
        user.profile = profile
        session.add(profile)

    profile.first_name = payload.first_name
    profile.last_name = payload.last_name
    profile.middle_name = payload.middle_name
    profile.phone = payload.phone
    profile.delivery_address = payload.delivery_address
    await session.commit()
    return await get_user(session, user_id)


async def user_orders(session: AsyncSession, user_id: int) -> list[dict]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(desc(Order.created_at))
    )
    return [serialize_order(order) for order in result.scalars().unique().all()]


def payment_providers() -> list[dict]:
    return [
        {"id": "yookassa", "name": "ЮKassa", "status": "draft", "enabled": False},
        {"id": "tinkoff", "name": "Tinkoff Pay", "status": "draft", "enabled": False},
        {"id": "sberpay", "name": "SberPay", "status": "draft", "enabled": False},
    ]


def payment_settings() -> dict:
    return {
        "statuses": ["pending", "authorized", "paid", "failed", "refunded"],
        "transaction_model": {
            "order_id": "future integer relation",
            "provider": "provider id",
            "external_id": "payment gateway id",
            "amount": "decimal",
            "status": "payment status",
        },
        "providers": payment_providers(),
    }
