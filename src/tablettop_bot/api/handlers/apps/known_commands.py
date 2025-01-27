import logging

from omegaconf import OmegaConf
from telebot import TeleBot


# Load logging configuration with OmegaConf
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = OmegaConf.load("./src/tablettop_bot/conf/apps/known_commands.yaml")
app_config = config.app
app_strings = config.strings


def register_handlers(bot: TeleBot):
    """ Register handlers host game app """

    logger.info("Registering `known_commands` handlers")
    @bot.message_handler(func=lambda message: True)
    def handle_known_commands(message):

        command_stem = message.text[1:]

        if command_stem in app_config.commands:
            # If the message is a known command, do nothing and let the appropriate handler catch it
            return
        else:
            bot.send_message(message.chat.id, app_strings.message)