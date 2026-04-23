from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.notification import Notification
from app.models.user import User


async def get_notifications_for_user(
    session: AsyncSession,
    user: User,
) -> List[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_notification_as_read_for_user(
    session: AsyncSession,
    user: User,
    notification_id: int,
) -> None:
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise NotFoundError(
            message="Notification not found",
            code="NOTIFICATION_NOT_FOUND",
            details={
                "notification_id": notification_id,
                "user_id": user.id,
            },
        )

    notification.is_read = True
    await session.commit()
