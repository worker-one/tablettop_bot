from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base model"""

    pass


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    first_message_timestamp = Column(DateTime)
    last_message_timestamp = Column(DateTime)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    phone_number = Column(String)
    lang = Column(String, default="en")
    role = Column(String, default="user")

    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    type = Column(String)
    state = Column(String, nullable=True)
    content_type = Column(String)
    content = Column(String, nullable=True)

    user = relationship("User", back_populates="events")

    def dict(self) -> dict:
        """ Return a dictionary representation of the event """
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M"),
            "user_id": self.user_id,
            "type": self.type,
            "state": self.state,
            "content": self.content,
            "content_type": self.content_type
        }
