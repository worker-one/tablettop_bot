import logging
from datetime import datetime, timedelta

from omegaconf import OmegaConf
from telebot import TeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from tablettop_bot.core.games import generate_summary
from tablettop_bot.db import crud

# Load logging configuration with OmegaConf
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = OmegaConf.load("./src/tablettop_bot/conf/apps/host_game.yaml")
app_strings = config.strings


class GameState:
    def __init__(self):
        self.repeat_game = None
        self.server_password = None
        self.room = None
        self.online = None
        self.selected_game_id = None
        self.selected_date = None
        self.selected_time = None
        self.steam = None
        self.selected_server = None
        self.name = None
        self.min_players = None
        self.max_players = None
        self.description = None
        self.link = None

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
        return "Информация об игре не найдена."
    
def format_date_with_day_of_week(date):
    
    day_of_week = date.strftime("%A")
    formatted_date = date.strftime("%d.%m")
    return f"{formatted_date} {day_of_week}"

def generate_date_matrix():
    
    dates = []
    today = datetime.now().date()  # Corrected usage
    for i in range(21):
        date = today + timedelta(days=i)  # Corrected usage
        dates.append(date)
    return dates


def create_date_buttons():
    markup = InlineKeyboardMarkup(row_width=7)
    dates = generate_date_matrix()
    for i in range(0, len(dates), 7):
        row_dates = dates[i:i+7]
        row_buttons = []
        for date in row_dates:
            formatted_date = date.strftime("%d.%m")
            row_buttons.append(InlineKeyboardButton(formatted_date, callback_data=f"date_{date}"))
        markup.row(*row_buttons)
    return markup


def register_handlers(bot: TeleBot):
    """ Register handlers host game app """

    logger.info("Registering `host_hame` handlers")
    @bot.message_handler(commands=['host_game'])
    def host_game(message):
        
        send_game_library_with_selection(message.chat.id)

    def send_game_library_with_selection(chat_id):
        
        send_game_library(chat_id)

    def send_game_library(chat_id, page=0, message_id=None):
        games = crud.get_all_games()

        if not games:
            bot.send_message(chat_id, 'Библиотека игр пуста.')
            return

        items_per_page = 11
        total_pages = (len(games) + items_per_page - 1) // items_per_page
        page_games = games[page * items_per_page:(page + 1) * items_per_page]

        message = 'Библиотека игр:\n'

        keyboard = InlineKeyboardMarkup()
        for game in page_games:
            keyboard.row(InlineKeyboardButton(
                f'{game.name}', callback_data=f'select_game_{game.id}'))

        navigation_buttons = []
        if page > 0:
            navigation_buttons.append(InlineKeyboardButton('⬅️ Предыдущая страница', callback_data=f'prev_page_{page - 1}'))
        if page < total_pages - 1:
            navigation_buttons.append(InlineKeyboardButton('➡️ Следующая страница', callback_data=f'next_page_{page + 1}'))
        if navigation_buttons:
            keyboard.row(*navigation_buttons)

        if message_id:
            bot.edit_message_text(message, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
        else:
            bot.send_message(chat_id, message, reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('prev_page_') or call.data.startswith('next_page_'))
    def handle_page_navigation(call):
        
        page = int(call.data.split('_')[-1])
        send_game_library(call.message.chat.id, page=page, message_id=call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('select_game_'))
    def handle_game_selection(call):
        
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id, timeout=2)
        global selected_game_id
        game_number = int(call.data.split('_')[2])

        # Check if the game exists in the library
        game = crud.get_game_details(game_number)

        if game:
            selected_game_id = game_number
            bot.send_message(call.message.chat.id, "Выберите дату игры:", reply_markup=create_date_buttons())
        else:
            bot.send_message(call.message.chat.id, app_strings.game_not_found)

    game_state = GameState()

    @bot.callback_query_handler(func=lambda call: call.data.startswith('date_'))
    def handle_date_selection(call):
        
        game_state.selected_date = call.data.split('_')[1]
        formatted_date = format_date_with_day_of_week(datetime.strptime(game_state.selected_date, '%Y-%m-%d'))
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Выберите время игры на {formatted_date}:")
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        time_keyboard = create_time_buttons()
        bot.send_message(call.message.chat.id, "Выберите время игры:", reply_markup=time_keyboard)

    def create_time_buttons():
        
        markup = InlineKeyboardMarkup(row_width=7)
        time_slots = [(hour, minute) for hour in range(10, 24) for minute in range(0, 60, 30)]
        for i in range(0, len(time_slots), 7):
            row_times = time_slots[i:i+7]
            row_buttons = []
            for hour, minute in row_times:
                time_str = f"{hour:02d}:{minute:02d}"
                row_buttons.append(InlineKeyboardButton(time_str, callback_data=f"time_{time_str}"))
            markup.row(*row_buttons)
        return markup

    @bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
    def handle_time_selection(call):
        game_state.selected_time = call.data.split('_')[1]
        selected_date_str = game_state.selected_date + " " + game_state.selected_time
        selected_datetime = datetime.strptime(selected_date_str, '%Y-%m-%d %H:%M')

        now = datetime.now()
        if selected_datetime < now - timedelta(minutes=30):
            bot.send_message(call.message.chat.id, "Неправильное время. Пожалуйста, выберите время.")
            bot.send_message(call.message.chat.id, "Выберите время игры:", reply_markup=create_time_buttons())
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Нужен ли Steam?", reply_markup=create_steam_keyboard())

    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('steam_'))
    def handle_steam_selection(call):
        
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id,timeout=1)
        if isinstance(call, CallbackQuery):
            selected_date_str = game_state.selected_date + " " + game_state.selected_time
            selected_datetime = datetime.strptime(selected_date_str, '%Y-%m-%d %H:%M')

            now = datetime.now()
            
            if selected_datetime < now - timedelta(minutes=30):
                bot.send_message(call.message.chat.id, "Неправильное время. Пожалуйста, выберите время в будущем.")
                bot.send_message(call.message.chat.id, "Выберите время игры:", reply_markup=create_time_buttons())
                return

            room = crud.get_available_room(selected_datetime)
            if room:
                game_state.room = room
                config.app.room_to_link.get(str(room))

                if call.data == 'steam_yes':
                    bot.send_message(call.message.chat.id, "Введите сервер в tabletop simulator:")
                    bot.register_next_step_handler(call.message, ask_for_server)
                elif call.data == 'steam_no':
                    ask_for_link(call.message)
            else:
                bot.send_message(call.message.chat.id, "Извините, все комнаты в Discord заняты.")
        else:
            bot.send_message(call.message.chat.id, "Ошибка: Неверные данные для выбора Steam.")


    def ask_for_server(message):
        global game_state
        game_state.selected_server = message.text  # Store the entered server information

        bot.send_message(message.chat.id, "Введите пароль для сервера:")
        bot.register_next_step_handler(message, handle_password_input)


    def handle_password_input(message):
        global game_state
        password = message.text
        game_state.server_password = password

        ask_if_repeat_game(message)  # Now ask if the game should repeat


    def ask_if_repeat_game(message):
        
        markup = InlineKeyboardMarkup()
        yes_button = InlineKeyboardButton(text="Да", callback_data='repeat_yes')
        no_button = InlineKeyboardButton(text="Нет", callback_data='repeat_no')
        markup.add(yes_button, no_button)

        bot.send_message(message.chat.id, "Хотите ли вы повторить игру каждую неделю?", reply_markup=markup)

        
    @bot.callback_query_handler(func=lambda call: call.data in ['repeat_yes', 'repeat_no'])
    def handle_repeat_response(call):
        
        """
        Handle the user's response to whether the game should repeat weekly.
        """
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id, timeout=1)
        message = call.message
        game_state.repeat_game = (call.data == 'repeat_yes')

        selected_date_str = game_state.selected_date + " " + game_state.selected_time
        selected_datetime = datetime.strptime(selected_date_str, '%Y-%m-%d %H:%M')

        now = datetime.now()
        
        
        if selected_datetime < now:
            bot.send_message(message.chat.id, app_strings.invalid_time)
            bot.send_message(message.chat.id, "Выберите время игры:", reply_markup=create_time_buttons())
            return

        try:
            username = message.chat.username
        except Exception as e:
            
            username = 'Гость'

        flagusername = True
        if username is None:
            if message.chat.last_name is not None:
                username = message.chat.first_name + " " + message.chat.last_name
            else:
                username = message.chat.first_name
            flagusername = False

        room = game_state.room
        link = config.app.room_to_link.get(str(room))

        
        crud.schedule_game(selected_game_id, selected_datetime, initiator_id=message.chat.id, nickname=username,
                    use_steam=bool(game_state.server_password), server_password=game_state.server_password,
                    serverdata=game_state.selected_server, discord_telegram_link=None, room=room,repeat_weekly=game_state.repeat_game)
        
        summary = generate_summary(selected_game_id, selected_datetime, serverdata=game_state.selected_server,
                                server_password=game_state.server_password, use_steam=bool(game_state.server_password),
                                ini_id=username, discord_telegram_link=link, room=room, flag=flagusername,repeat = game_state.repeat_game)

        bot.send_message(message.chat.id, f"{summary}\n {get_game_info_message(selected_game_id)}", parse_mode='HTML',
                        disable_web_page_preview=True)

    def ask_for_link(message):
        
        ask_if_repeat_game(message)

    def ask_for_password(message):
        
        global game_state
        selected_date_str = game_state.selected_date + " " + game_state.selected_time  # Concatenate date and time strings
        selected_datetime = datetime.strptime(selected_date_str, '%Y-%m-%d %H:%M')
        now = datetime.now()
        
        if selected_datetime < now - timedelta(minutes=30):
            bot.send_message(message.chat.id, "Неправильное время. Пожалуйста, выберите время в будущем.")
            bot.send_message(message.chat.id, "Выберите время игры:", reply_markup=create_time_buttons())
            return

        password = message.text

        try:
            user = bot.get_chat_member(message.chat.id, message.from_user.id)
            username = user.user.username if user and user.user.username else 'Unknown User'
        except Exception as e:
            logger.info(f"Error getting username: {e}")
            username = 'Unknown User'
        flagusername= True
        if username is None:
            username = message.chat.first_name + " " +message.chat.last_name
            flagusername =False
        room = game_state.room
        link = config.app.room_to_link.get(str(room))
        crud.schedule_game(selected_game_id, selected_datetime, initiator_id=message.from_user.id, nickname=username, use_steam=True, server_password=password, serverdata=game_state.selected_server, room=game_state.room,repeat_weekly=game_state.repeat_game)
        summary = generate_summary(selected_game_id, selected_datetime, serverdata=game_state.selected_server, ini_id=username,server_password=password, use_steam=True,discord_telegram_link=link,room=room,flag = flagusername,repeat = game_state.repeat_game)
        bot.send_message(message.chat.id, f"{summary}\n {get_game_info_message(selected_game_id)} ", parse_mode='HTML',
                        disable_web_page_preview=True)
        ask_if_repeat_game(message)


    def create_steam_keyboard():
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("Да", callback_data="steam_yes"),
                InlineKeyboardButton("Нет", callback_data="steam_no"))
        return markup
