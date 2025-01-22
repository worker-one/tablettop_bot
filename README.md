## Tablettop Telegram Bot

A Telegram bot for Tablettop application. The project uses the `pyTelegramBotAPI` library for interaction with Telegram's API and SQLAlchemy for database interactions.

## Structure

The project is structured in `src/tablettop_bot/` as following:

`main.py` - The main file that connects (creates and initializes if neede) to database, defines and runs the bot.

`core/` - The module that contains core services for the bot's applications.

`conf/config.yaml` - The base configuration for the bot: name, version, timezone, applications enabled, database settings, etc.

`conf/apps/` - Config files for user's applications

`conf/admin/` - Config files for admin's applications

`api/handlers/apps` - The user's application handles for interactions with the Telegram API.

`api/handlers/admin` - The admin's application handles for interactions with the Telegram API.

`db/database.py` - The file that handles interactions with the database.

`db/models.py` - Models for database tables.

`db/crud/` - CRUD operations for database.

`tests/` - The directory that contains the tests for the application.

`Dockerfile` - The file that defines the Docker container for this project.

## In-built admin applications

### Send public message to all users of the bot

### Grant admin rights to other user

### Export database tables of the bot

### About

## In-built user applications

### Host Game

Host a game.

### Join Game

Join to a game, manage the existing subscribtions to games.

### Library

Read games in the library

### About

Information about the bot.

## Setup

1. Clone this repository.
2. Create a `.env` file in the root directory and add your database connection string and bot token.
3. Install the dependencies with `pip install .`.
4. Run the bot with `python src/tablettop_bot/main.py`.

## Docker

To run this application in a Docker container, follow these steps:

1. Build the Docker image with `docker build -t tablettop-bot .`.
2. Run the Docker container with `docker run -p 80:80 tablettop-bot`.
