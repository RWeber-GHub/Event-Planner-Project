from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base


class Category(Base):
    __tablename__ = "categories"

    CategoryID: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    Name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)