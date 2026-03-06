from sqlalchemy import Integer, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base

class Notification(Base):
    __tablename__ = "notifications"

    NotificationID: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    UserID: Mapped[int] = mapped_column(ForeignKey("users.UserID"), nullable=False)

    Message: Mapped[str] = mapped_column(Text, nullable=False)

    IsRead: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    CreatedAt: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )