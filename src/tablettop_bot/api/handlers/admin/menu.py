import logging
import logging.config

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

config = OmegaConf.load("./src/tablettop_bot/conf/admin/menu.yaml")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_menu_markup(lang) -> InlineKeyboardMarkup:
    """Create the admin menu markup."""
    menu_markup = InlineKeyboardMarkup(row_width=1)
    for option in config[lang].admin_menu.options:
        menu_markup.add(InlineKeyboardButton(option.label, callback_data=option.value))
    return menu_markup


def register_handlers(bot):
    """Register the handlers for the admin menu."""

    @bot.message_handler(commands=["admin"])
    def admin_menu_command(message: Message, data: dict):
        """Handler to show the admin menu."""
        user = data["user"]
        if user.role != "admin":
            # Inform the user that they do not have admin rights
            bot.send_message(message.from_user.id, config[user.lang].no_rights)
            return

        # Send the admin menu
        bot.send_message(
            message.from_user.id, config[user.lang].admin_menu.title, reply_markup=create_admin_menu_markup(user.lang)
        )
