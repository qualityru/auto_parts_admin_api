from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    JSON,
    MetaData,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
    relationship,
)


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class OrderStatus(str, Enum):
    created = "created"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    enable: Mapped[bool] = mapped_column(Boolean, default=True)

    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", uselist=False, back_populates="user", lazy="selectin"
    )
    auths: Mapped[list["UserAuth"]] = relationship(
        "UserAuth", back_populates="user", lazy="selectin"
    )

    @property
    def auths_map(self) -> dict[str, str]:
        if not self.auths:
            return {}
        return {
            auth.provider.slug: auth.subject
            for auth in self.auths
            if auth.provider
        }


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    middle_name: Mapped[Optional[str]] = mapped_column(String(255))
    username: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    age: Mapped[Optional[str]] = mapped_column(String(255))
    country: Mapped[Optional[str]] = mapped_column(String(255))
    lang: Mapped[Optional[str]] = mapped_column(String(255))
    delivery_address: Mapped[Optional[str]] = mapped_column(String(500))

    user: Mapped["User"] = relationship(
        "User", uselist=False, back_populates="profile"
    )


class AuthProvider(Base):
    __tablename__ = "auth_providers"

    slug: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    enable: Mapped[bool] = mapped_column(Boolean, default=True)

    auths: Mapped[list["UserAuth"]] = relationship(
        "UserAuth", back_populates="provider"
    )


class UserAuth(TimestampMixin, Base):
    __tablename__ = "user_auths"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("auth_providers.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token: Mapped[Optional[str]] = mapped_column(String)

    user: Mapped["User"] = relationship("User", back_populates="auths")
    provider: Mapped["AuthProvider"] = relationship(
        "AuthProvider", back_populates="auths", lazy="selectin"
    )


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status"),
        default=OrderStatus.created,
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(255))
    customer_phone: Mapped[str] = mapped_column(String(64))
    delivery_address: Mapped[str] = mapped_column(String(500))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(16), default="RUB")

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", lazy="selectin"
    )


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[str] = mapped_column(String(255))
    warehouse_id: Mapped[str] = mapped_column(String(255))
    brand: Mapped[str] = mapped_column(String(255))
    article: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(500))
    image: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(16), default="RUB")
    quantity: Mapped[int]
    warehouse_name: Mapped[Optional[str]] = mapped_column(String(255))
    return_type: Mapped[Optional[str]] = mapped_column(String(255))
    fail_percent: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    product_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    warehouse_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
