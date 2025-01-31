import csv
import logging
import logging.config
import os

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .models import Base, Game

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Load logging configuration with OmegaConf
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv(usecwd=True))

# Retrieve environment variables
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Check if any of the required environment variables are not set
if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    logger.warning("One or more postgresql database environment variables are not set. Using SQLite instead.")
    DATABASE_URL = "sqlite:///local_database.db"
else:
    # Construct the database URL for PostgreSQL
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"

def get_engine():
    """Get a new engine for the database."""
    return create_engine(
        DATABASE_URL,
        connect_args={"connect_timeout": 5, "application_name": "tablettop_bot"} if "postgresql" in DATABASE_URL else {},
        poolclass=NullPool if "postgresql" in DATABASE_URL else None,
    )


def create_tables():
    """Create tables in the database."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Tables created")


def drop_tables():
    """Drop tables in the database."""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    logger.info("Tables dropped")


def get_session():
    """Get a new session from the database engine."""
    engine = get_engine()
    return sessionmaker(bind=engine)()


def export_all_tables(export_dir: str):
    """Export all tables to CSV files."""
    db = get_session()
    inspector = inspect(db.get_bind())

    for table_name in inspector.get_table_names():
        file_path = os.path.join(export_dir, f"{table_name}.csv")
        with open(file_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            writer.writerow(columns)

            records = db.execute(text(f"SELECT * FROM {table_name}")).fetchall()
            for record in records:
                writer.writerow(record)

    db.close()


engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Start a new session
Session = sessionmaker(bind=engine)
session = Session()

def init_games_table():
    # Insert data into the games table
    games_data = [
        {
            "id": 1,
            "name": "🐙 Ужас Аркхэма. Карточная игра",
            "min_players": 1,
            "max_players": 4,
            "description": "Каждый игрок берет на себя роль одного из сыщиков...",
            "online": True,
            "link": "https://boardgamegeek.com/boardgame/359609/arkham-horror-the-card-game-revised-edition",
        },
        {
            "id": 2,
            "name": "🌖 НРИ. Грани Вселенной 1",
            "min_players": 1,
            "max_players": 5,
            "description": "«Грани вселенной» — это настолько-ролевая ПБТА-игра в жанре космооперы...",
            "online": False,
            "link": "https://t.me/c/2051862565/3476/6526",
        },
        {
            "id": 3,
            "name": "🐙 Ужас Аркхэма 3.0",
            "min_players": 1,
            "max_players": 6,
            "description": "Штат Массачусетс, 1926 год. Слишком долго город Аркхэм стоял...",
            "online": True,
            "link": "https://boardgamegeek.com/boardgame/257499/arkham-horror-third-edition",
        },
        {
            "id": 4,
            "name": "🐙 Ужас Аркхэма 2.0",
            "min_players": 1,
            "max_players": 8,
            "description": "На дворе 1926 год, самый пик 'бурных двадцатых', в прокуренных притонах...",
            "online": True,
            "link": "https://boardgamegeek.com/boardgame/15987/arkham-horror",
        },
        {
            "id": 5,
            "name": "🧠 НРИ. Сети разума",
            "min_players": 1,
            "max_players": 4,
            "description": "Итак, свечи горят, музыка играет, а мы уже готовы слушать историю...",
            "online": False,
            "link": "https://boardgamegeek.com/rpg/56388/pathfinder-roleplaying-game-2nd-edition",
        },
        {
            "id": 6,
            "name": "🐉 D&D v3.5. Карта судьбы",
            "min_players": 1,
            "max_players": 6,
            "description": "Dungeons & Dragons (D&D) — это настольная ролевая игра...",
            "online": True,
            "link": "https://boardgamegeek.com/rpg/243/dungeons-and-dragons-35-edition",
        },
        {
            "id": 7,
            "name": "🐙 Особняки Безумия",
            "min_players": 1,
            "max_players": 6,
            "description": "«Особняки безумия» переносят вас и ваших друзей в таинственный...",
            "online": True,
            "link": "https://boardgamegeek.com/boardgame/205059/mansions-of-madness-second-edition",
        },
        {
            "id": 8,
            "name": "🩸Спартак. Кровь и песок",
            "min_players": 3,
            "max_players": 15,
            "description": "Действие этой игры происходит в Древнем Риме. Игроки являются главами...",
            "online": True,
            "link": "https://tesera.ru/game/Spartacus-A-Game-of-Blood-and-Treachery/",
        },
        {
            "id": 9,
            "name": "🩸Спартак. Кровь и песок 1",
            "min_players": 3,
            "max_players": 15,
            "description": "Действие этой игры происходит в Древнем Риме. Игроки являются главами...",
            "online": True,
            "link": "https://tesera.ru/game/Spartacus-A-Game-of-Blood-and-Treachery/",
        },
        {
            "id": 10,
            "name": "🩸Спартак. Кровь и песок 2",
            "min_players": 3,
            "max_players": 15,
            "description": "Действие этой игры происходит в Древнем Риме. Игроки являются главами...",
            "online": True,
            "link": "https://tesera.ru/game/Spartacus-A-Game-of-Blood-and-Treachery/",
        },
        {
            "id": 11,
            "name": "🩸Спартак. Кровь и песок 3",
            "min_players": 3,
            "max_players": 15,
            "description": "Действие этой игры происходит в Древнем Риме. Игроки являются главами...",
            "online": True,
            "link": "https://tesera.ru/game/Spartacus-A-Game-of-Blood-and-Treachery/",
        },
        {
            "id": 12,
            "name": "🩸Спартак. Кровь и песок 4",
            "min_players": 3,
            "max_players": 15,
            "description": "Действие этой игры происходит в Древнем Риме. Игроки являются главами...",
            "online": True,
            "link": "https://tesera.ru/game/Spartacus-A-Game-of-Blood-and-Treachery/",
        },
        {
            "id": 13,
            "name": "🩸Спартак. Кровь и песок 5",
            "min_players": 3,
            "max_players": 15,
            "description": "Действие этой игры происходит в Древнем Риме. Игроки являются главами...",
            "online": True,
            "link": "https://tesera.ru/game/Spartacus-A-Game-of-Blood-and-Treachery/",
        },
        {
            "id": 14,
            "name": "🩸Спартак. Кровь и песок 6",
            "min_players": 3,
            "max_players": 15,
            "description": "Действие этой игры происходит в Древнем Риме. Игроки являются главами...",
            "online": True,
            "link": "https://tesera.ru/game/Spartacus-A-Game-of-Blood-and-Treachery/",
        },
        {
            "id": 15,
            "name": "🌖 НРИ. Грани Вселенной 2",
            "min_players": 1,
            "max_players": 5,
            "description": "«Грани вселенной» — это настолько-ролевая ПБТА-игра в жанре космооперы...",
            "online": False,
            "link": "https://t.me/c/2051862565/3476/6526",
        },
    ]

    # Add and commit data
    for game_data in games_data:
        game = Game(**game_data)
        session.add(game)

    session.commit()
