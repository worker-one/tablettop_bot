import logging

from omegaconf import OmegaConf
from telebot import TeleBot


# Load logging configuration with OmegaConf
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = OmegaConf.load("./src/tablettop_bot/conf/apps/about.yaml")
app_strings = config.strings

def register_handlers(bot: TeleBot):
    """ Register handlers for about app """

    logger.info("Registering about app handlers")
    @bot.message_handler(commands=['about'])
    def send_about_info(message):
        print("def send_about_info(message):")
        bot.send_message(message.chat.id, app_strings.about, parse_mode='Markdown')