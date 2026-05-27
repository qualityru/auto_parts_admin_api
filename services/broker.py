import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import aio_pika
from loguru import logger

from config import settings


def _json_default(value: Any):
    if isinstance(value, (datetime, Decimal)):
        return str(value)
    return value


async def publish_event(routing_key: str, payload: dict[str, Any]) -> None:
    try:
        connection = await aio_pika.connect_robust(settings.BROKER_URL)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                settings.BROKER_EXCHANGE,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload, default=_json_default).encode("utf-8"),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=routing_key,
            )
            logger.info("Published admin event {}", routing_key)
    except Exception as exc:
        logger.warning("Admin broker publish failed for {}: {}", routing_key, exc)


async def consume_shop_events() -> None:
    try:
        connection = await aio_pika.connect_robust(settings.BROKER_URL)
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            settings.BROKER_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        queue = await channel.declare_queue("admin_backend.events", durable=True)
        await queue.bind(exchange, routing_key=settings.BROKER_ORDER_CREATED_ROUTING_KEY)
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    logger.info(
                        "Received shop event {}: {}",
                        message.routing_key,
                        message.body.decode("utf-8", errors="replace"),
                    )
    except Exception as exc:
        logger.warning("Admin broker consumer stopped: {}", exc)
