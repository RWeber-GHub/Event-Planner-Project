from sqlalchemy import String, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base

class User(Base):
    __tablename__ = "users"

    UserID: Mapped[int] = mapped_column(Integer, primary_key=True)
    Role: Mapped[str] = mapped_column(
        Enum("Venue", "User", "Admin", name="user_roles"),
        default="User"
    )
    Email: Mapped[str] = mapped_column(String(255), unique=True)
    Password: Mapped[str] = mapped_column(String(255))
    Phone: Mapped[str] = mapped_column(String(20))
    Status: Mapped[str] = mapped_column(String(50), default="Active")