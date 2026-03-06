from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base


class Venue(Base):
    __tablename__ = "venues"

    VenuesID: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    VenueName: Mapped[str] = mapped_column(String(200), nullable=False)

    Location: Mapped[str] = mapped_column(String(300), nullable=False)

    VenuesReviews: Mapped[str | None] = mapped_column(Text, nullable=True)

    SeatingCapacity: Mapped[int | None] = mapped_column(Integer, nullable=True)