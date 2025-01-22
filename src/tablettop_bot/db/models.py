from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time
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


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    online = Column(Boolean)
    min_players = Column(Integer)
    max_players = Column(Integer)
    description = Column(String, nullable=True)
    link = Column(String, nullable=True)

class ScheduledGame(Base):
    __tablename__ = 'scheduled_games'

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey('games.id'))
    date = Column(Date)
    time = Column(Time)
    datetime = Column(DateTime)
    initiator_id = Column(Integer)
    initiator_name = Column(String)
    use_steam = Column(Boolean)
    server_data = Column(String, nullable=True)
    server_password = Column(String, nullable=True)
    discord_telegram_link = Column(String, nullable=True)
    player_ids = Column(Text, nullable=True)
    player_nicknames = Column(Text, nullable=True)
    room = Column(Integer)
    repweekly = Column(Boolean, default=False)
    PGID = Column(Integer, nullable=True)
    GameTree = Column(Text, nullable=True)
    skipped = Column(Boolean, default=False)


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
