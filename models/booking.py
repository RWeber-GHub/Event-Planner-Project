from sqlalchemy import Integer, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base

class Booking(Base):
    __tablename__ = "bookings"

    BookingID: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    EventID: Mapped[int] = mapped_column(ForeignKey("events.EventID"), nullable=False)
    TimeID: Mapped[int | None] = mapped_column(ForeignKey("time_slots.TimeID"), nullable=True)
    BookerID: Mapped[int] = mapped_column(ForeignKey("users.UserID"), nullable=False)

    Status: Mapped[str] = mapped_column(
        Enum("Pending", "Confirmed", "Cancelled", name="booking_status"),
        default="Pending",
        nullable=False,
    )