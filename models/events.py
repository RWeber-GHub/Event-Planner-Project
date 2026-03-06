from sqlalchemy import (
    String, Integer, DateTime, Text, Numeric, Boolean, Enum
)
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base


class Event(Base):
    __tablename__ = "events"

    EventID: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    VenueID: Mapped[int] = mapped_column(Integer, nullable=False)
    CategoryID: Mapped[int | None] = mapped_column(Integer, nullable=True)
    TimeID: Mapped[int | None] = mapped_column(Integer, nullable=True)

    Name: Mapped[str] = mapped_column(String(200), nullable=False)
    StartDate: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    EndDate: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    Desc: Mapped[str | None] = mapped_column(Text, nullable=True)

    ImagePoster: Mapped[str | None] = mapped_column(String(500), nullable=True)

    TicketPrice: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    PublicityLevel: Mapped[str] = mapped_column(
        Enum("Public", "Private", "Unlisted", name="publicity_levels"),
        nullable=False,
        default="Public",
    )

    Approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)