import logging

from omegaconf import OmegaConf
from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from tablettop_bot.db import crud

# Load logging configuration with OmegaConf
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = OmegaConf.load("./src/tablettop_bot/conf/apps/library.yaml")
app_strings = config.strings


def get_game_info_message(game_id):
    game_info = crud.get_game_details(game_id)

    if game_info:
        game_name = game_info.name
        min_players = game_info.min_players
        max_players = game_info.max_players
        description = game_info.description
        link = game_info.link

        game_message = (f"<b><a href='{link}'>{game_name}</a></b>\n"
                        f"<code>Число игроков: {min_players}-{max_players}</code>\n \n"
                        f"<code>{description} </code>\n")
        return game_message
    else:
        return app_strings.game_not_found


def register_handlers(bot: TeleBot):
    """ Register handlers for game library app """

    logger.info("Registering library app handlers")
    @bot.message_handler(commands=['library'])
    def handle_library_command(message):
        initial_message = bot.send_message(message.chat.id, app_strings.library_list)
        game_library(message.chat.id, initial_message.message_id)


    def game_library(chat_id, message_id, page=0):
        games = crud.get_offline_games()

        if not games:
            bot.send_message(chat_id, app_strings.library_empty)
            return

        items_per_page = 11
        total_pages = (len(games) + items_per_page - 1) // items_per_page
        page_games = games[page * items_per_page: (page + 1) * items_per_page]

        keyboard = InlineKeyboardMarkup()
        for game in page_games:
            keyboard.add(InlineKeyboardButton(game.name, callback_data=f'game_info_{game.id}'))

        navigation_buttons = []
        if total_pages > 1:
            if page > 0:
                navigation_buttons.append(
                    InlineKeyboardButton(app_strings.prev_page, callback_data=f'prev_page_library_{page - 1}'))
            if page < total_pages - 1:
                navigation_buttons.append(
                    InlineKeyboardButton(app_strings.next_page, callback_data=f'next_page_library_{page + 1}'))
        if navigation_buttons:
            keyboard.row(*navigation_buttons)

        bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('prev_page_library') or call.data.startswith('next_page_library'))
    def handle_library_page_navigation(call):
        page = int(call.data.split('_')[-1])
        game_library(call.message.chat.id, call.message.message_id, page=page)


    @bot.message_handler(commands=['tabletop_library'])
    def handle_online_library_command(message):
        initial_message = bot.send_message(message.chat.id, app_strings.online_library_list)
        online_library(message.chat.id, initial_message.message_id)


    def online_library(chat_id, message_id, page=0):
        online_games = crud.get_online_games()

        if not online_games:
            bot.send_message(chat_id, app_strings.online_library_empty)
            return

        items_per_page = 11
        total_pages = (len(online_games) + items_per_page - 1) // items_per_page
        page_games = online_games[page * items_per_page: (page + 1) * items_per_page]

        keyboard = InlineKeyboardMarkup()
        for game in page_games:
            keyboard.add(InlineKeyboardButton(game.name, callback_data=f'game_info_{game.id}'))

        navigation_buttons = []
        if total_pages > 1:
            if page > 0:
                navigation_buttons.append(
                    InlineKeyboardButton(app_strings.prev_page, callback_data=f'prev_page_online_{page - 1}'))
            if page < total_pages - 1:
                navigation_buttons.append(
                    InlineKeyboardButton(app_strings.next_page, callback_data=f'next_page_online_{page + 1}'))
        if navigation_buttons:
            keyboard.row(*navigation_buttons)

        bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('prev_page_online') or call.data.startswith('next_page_online'))
    def handle_online_page_navigation(call):
        page = int(call.data.split('_')[-1])
        online_library(call.message.chat.id, call.message.message_id, page=page)


    @bot.callback_query_handler(func=lambda call: call.data.startswith('game_info_'))
    def handle_select_game(call):
        game_id = int(call.data.split('_')[-1])
        game_message = get_game_info_message(game_id)
        bot.send_message(call.message.chat.id, game_message, parse_mode='HTML')
