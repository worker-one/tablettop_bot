import logging
import os
import threading
from time import sleep

import schedule as sc
from dotenv import find_dotenv, load_dotenv

from tablettop_bot.api.bot import start_bot
from tablettop_bot.db import crud
from tablettop_bot.db.database import create_tables, drop_tables, init_games_table

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load and get environment variables
load_dotenv(find_dotenv(usecwd=True))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")


def init_db():
    """Initialize the database."""
    # Create tables
    create_tables()

    # Add admin to user table
    if ADMIN_USERNAME:
        user = crud.upsert_user(id=ADMIN_USER_ID, username=ADMIN_USERNAME, role="admin")
        logger.info(f"User '{user.username}' ({user.id}) added to the database with admin role.")

    logger.info("Database initialized")


sc.every().day.at("23:05").do(crud.prolong)

# Function to run the scheduled tasks in a loop
def run_scheduled_tasks():
    print("def run_scheduled_tasks():")
    while True:
        sc.run_pending()
        sleep(1)  # Wait for a second before checking again

if __name__ == "__main__":
    drop_tables()
    init_db()
    init_games_table()
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()

    run_scheduled_tasks()
