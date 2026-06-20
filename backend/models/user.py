import enum
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum
from database import Base


class UserStatus(enum.Enum):
    active = "active"
    inactive = "inactive"


class UserGrade(enum.Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(SAEnum(UserStatus), default=UserStatus.active, nullable=False)
    grade = Column(SAEnum(UserGrade), default=UserGrade.BRONZE, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
