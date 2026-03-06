from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base

class SeatType(Base):
    __tablename__ = "seat_types"

    SeatID: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    SeatType: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)