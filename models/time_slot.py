from sqlalchemy import Integer, Time
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base
import datetime


class TimeSlot(Base):
    __tablename__ = "time_slots"

    TimeID: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    StartTime: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    EndTime: Mapped[datetime.time] = mapped_column(Time, nullable=False)