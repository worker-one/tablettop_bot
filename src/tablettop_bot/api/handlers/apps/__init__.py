import yaml
from telebot import TeleBot

# Load the config file
with open("./src/tablettop_bot/conf/config.yaml") as file:
    config = yaml.safe_load(file)

# Dynamically import the modules listed in the config file
apps = config["apps"]
imported_apps = {app: __import__(f"tablettop_bot.api.handlers.apps.{app}", fromlist=[""]) for app in apps}


def register_handlers(bot: TeleBot):
    for app in imported_apps.values():
        app.register_handlers(bot)
