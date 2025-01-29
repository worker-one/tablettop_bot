import logging
from datetime import datetime, timedelta

from omegaconf import OmegaConf
from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from tablettop_bot.db import crud

# Load logging configuration with OmegaConf
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = OmegaConf.load("./src/tablettop_bot/conf/apps/join_game.yaml")
app_strings = config.strings

def cleanup_past_games():
    cutoff_time = datetime.now() - timedelta(minutes=30)
    crud.delete_past_games(cutoff_time)

def get_initiator_username(bot, chat_id, user_id):
    try:
        user = bot.get_chat_member(chat_id, user_id)
        username = user.user.username if user and user.user.username else user.user.first_name + " " + user.user.last_name
    except Exception as e:
        print(f"Error getting username: {e}")
        username = 'Unknown User'
    return username

def format_enrolled_games(enrolled_games, chat_id, user_id):
    # Sort games by date and time
    sorted_games = sorted(enrolled_games, key=lambda game: game.datetime)
    formatted_message = '<b>Список ваших игр:</b>\n'
    current_date = None

    for game in sorted_games:
        game_date = game.date
        game_day_russian = app_strings.day_name_mapping[game_date.strftime('%A')]
        game_date_formatted = f"{game_day_russian} - {game_date.strftime('%d.%m.%Y')}"
        game_time = game.time
        game_details = crud.get_game_details(game.game_id)
        game_name = game_details.name
        max_players = game_details.max_players

        if game_date_formatted != current_date:
            formatted_message += f'\n<b>{game_date_formatted}</b>\n'
            current_date = game_date_formatted

        player_ids = game.player_ids.split(',')
        player_nicknames = game.player_nicknames.split(',')
        enrolled_users = [player_nicknames[i] if player_nicknames[i] else 'Гость' for i in range(len(player_ids))]

        num_players = len(enrolled_users)
        initiator = game.initiator_name

        formatted_message += f'<b>{game_time}</b> - <a href="{game_details.link}">{game_name}</a> ({num_players}/{max_players} игроков)\n'
        formatted_message += f'@{initiator} (инициатор игры)\n'

        # Remove initiator from enrolled users if present
        enrolled_users = [user for user in enrolled_users if user != initiator]

        # Format enrolled users
        enrolled_users_message = '\n'.join([f'@{user}' if user != 'Гость' else 'Гость' for user in enrolled_users])
        if enrolled_users_message:
            formatted_message += f'{enrolled_users_message}\n'

        print(f"room = {game.room}")

        # Add server or room information
        if game.use_steam:
            formatted_message += f'Server: {game.server_data}, Password: {game.server_password}\n'
        if game.room:
            room_link = config.app.room_to_link.get(game.room)
            if room_link:
                formatted_message += f'Discord комната: <a href="{room_link}">#{game.room}</a>\n'
            else:
                formatted_message += f'Discord комната: {game.discord_telegram_link}\n\n'
        formatted_message += "\n"

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Отписаться от игры", callback_data='select_unsubscribe_game'))
    keyboard.add(InlineKeyboardButton("Удалить игру", callback_data='select_delete_game'))


    return formatted_message, keyboard


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

game_state = GameState()

# Dictionary to map English day names to Russian day names
def get_nearest_days_with_games(scheduled_games, max_days=8):
    nearest_days = []
    current_date = None
    days_with_games = 0
    displayed_dates = set()

    for game in scheduled_games:
        if game.date not in displayed_dates:
            displayed_dates.add(game.date)
            nearest_days.append(game.date)
            days_with_games += 1

        if days_with_games >= max_days:
            break

    return nearest_days


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

def format_date_with_day_of_week(date):
    day_of_week = date.strftime("%A")
    formatted_date = date.strftime("%d.%m")
    return f"{formatted_date} {day_of_week}"


def register_handlers(bot: TeleBot):
    """ Register handlers for join game app """

    logger.info("Registering `join_game` handlers")

    @bot.message_handler(commands=['join_game', 'start'])
    def handle_start(message):
        cleanup_past_games()
        crud.prolong()

        scheduled_games = crud.get_scheduled_games()
        print(f"scheduled_games = {len(scheduled_games)}")
        if scheduled_games:
            formatted_message = format_scheduled_games(bot, scheduled_games, message.chat.id)
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("Записаться", callback_data='enroll'))
            keyboard.row(InlineKeyboardButton("Обновить расписание", callback_data='update_schedule'))
            keyboard.row(InlineKeyboardButton("Мои игры", callback_data='my_games'))
            bot.send_message(message.chat.id, formatted_message, reply_markup=keyboard, parse_mode='HTML', disable_web_page_preview=True)
        else:
            bot.send_message(message.chat.id, app_strings.no_scheduled_games)

    GAMES_PER_PAGE = 10

    def handle_enroll_page(chat_id, available_games, page=1, message_id=None):
        total_pages = (len(available_games) + GAMES_PER_PAGE - 1) // GAMES_PER_PAGE
        start_idx = (page - 1) * GAMES_PER_PAGE
        end_idx = start_idx + GAMES_PER_PAGE
        page_games = available_games[start_idx:end_idx]

        nearest_days = get_nearest_days_with_games(available_games)  # Get nearest 8 days with games
        sorted_games = [
            game for game in page_games 
            if game.date in nearest_days
        ]

        keyboard = InlineKeyboardMarkup(row_width=1)
        for game in sorted_games:
            game_details = crud.get_game_details(game.game_id)
            if game_details:
                game_name = game_details.name
            else:
                game_name = "Unknown Game"
            game_date = game.date
            game_time = game.time.strftime('%H:%M')
            button_text = f'{game_name} - {game_date} {game_time}'
            keyboard.add(InlineKeyboardButton(button_text, callback_data=f'enroll_game_{game.id}'))

        # Add navigation buttons
        if page > 1:
            keyboard.add(InlineKeyboardButton("Назад", callback_data=f'enroll_page_{page - 1}'))
        if page < total_pages:
            keyboard.add(InlineKeyboardButton("Вперед", callback_data=f'enroll_page_{page + 1}'))
        keyboard.add(InlineKeyboardButton("Назад", callback_data='back_to_main'))

        if message_id:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=app_strings.choose_game_to_join,
                reply_markup=keyboard
            )
        else:
            bot.send_message(
                chat_id=chat_id,
                text=app_strings.choose_game_to_join,
                reply_markup=keyboard
            )

    @bot.message_handler(commands=['create_game'])
    def create_game_command(message):
        msg = bot.send_message(message.chat.id, app_strings.enter_game_name)
        bot.register_next_step_handler(msg, process_game_name)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('date_'))
    def handle_date_selection(call):
        game_state.selected_date = call.data.split('_')[1]
        formatted_date = format_date_with_day_of_week(datetime.strptime(game_state.selected_date, '%Y-%m-%d'))
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Выберите время игры на {formatted_date}:")
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        time_keyboard = create_time_buttons()

        bot.send_message(call.message.chat.id, "Выберите время игры:", reply_markup=time_keyboard)

    def format_scheduled_games(bot, scheduled_games, chat_id):
        nearest_days = get_nearest_days_with_games(scheduled_games)
        formatted_message = ''
        current_date = None

        for game in scheduled_games:
            if game.date in nearest_days:
                if game.date != current_date:
                    day_name = game.date.strftime("%A")
                    russian_day_name = app_strings.day_name_mapping[day_name]
                    formatted_message += f'\n<b>{russian_day_name} - {game.date.strftime("%d.%m.%Y")}</b>\n'
                    current_date = game.date

                game_details = crud.get_game_details(game.game_id)
                game_name = game_details.name
                max_players = game_details.max_players

                # Fetch enrolled users
                enrolled_users_ids = crud.get_enrolled_players(game.id)[0]

                num_players = len(enrolled_users_ids)

                formatted_message += f'<b>{game.time.strftime("%H:%M")}</b>  <a href="{game_details.link}">{game_name}</a> ({num_players}/{max_players} игроков)\n'

        return formatted_message

    def process_game_name(message):
        game_state.name = message.text
        msg = bot.send_message(message.chat.id, "Введите минимальное количество игроков:")
        bot.register_next_step_handler(msg, process_min_players)

    def process_min_players(message):
        try:
            min_players = int(message.text)
            if min_players > 0:
                game_state.min_players = min_players
                msg = bot.send_message(message.chat.id, "Введите максимальное количество игроков:")
                bot.register_next_step_handler(msg, process_max_players)
            else:
                raise ValueError
        except ValueError:
            msg = bot.send_message(message.chat.id, "Пожалуйста, введите положительное числовое значение для минимального количества игроков.")
            bot.register_next_step_handler(msg, process_min_players)

    def process_max_players(message):
        try:
            max_players = int(message.text)
            if max_players > 0:
                if max_players >= game_state.min_players:
                    game_state.max_players = max_players
                    msg = bot.send_message(message.chat.id, "Введите описание игры:")
                    bot.register_next_step_handler(msg, process_description)
                else:
                    msg = bot.send_message(message.chat.id, f"Максимальное количество игроков должно быть больше минимального ({game_state.min_players}). Пожалуйста, введите допустимое значение.")
                    bot.register_next_step_handler(msg, process_max_players)
            else:
                raise ValueError
        except ValueError:
            msg = bot.send_message(message.chat.id, "Пожалуйста, введите положительное числовое значение для максимального количества игроков.")
            bot.register_next_step_handler(msg, process_max_players)


    def process_description(message):
        game_state.description = message.text
        msg = bot.send_message(message.chat.id, "Введите ссылку на страницу с информацией об игре:")
        bot.register_next_step_handler(msg, process_link)


    def process_link(message):
        allowed_sources = [
            "tesera.ru",
            "boardgamegeek.com",
            "https://t.me/+HCf2_QuXVy5hMWRi",
            "https://t.me/c/2051862565/"
        ]

        game_link = message.text.strip()
        is_valid_source = False

        # Check if the link matches any of the allowed patterns
        for source in allowed_sources:
            if source in game_link:
                is_valid_source = True
                break

        if is_valid_source:
            game_state.link = game_link
            msg = bot.send_message(message.chat.id, "Игра через Tabletop Simulator? Да/Нет")
            bot.register_next_step_handler(msg, process_online)
        else:
            # Update the error message with the embedded link
            error_message = (
                "Пожалуйста, введите ссылку с одного из следующих сайтов: "
                "tesera.ru,boardgamegeek.com, или из "
                "<a href='https://t.me/+HCf2_QuXVy5hMWRi'>Нашей группы</a>."
            )
            msg = bot.send_message(message.chat.id, error_message, parse_mode='HTML',disable_web_page_preview=True)
            bot.register_next_step_handler(msg, process_link)


    def process_online(message):
        if message.text.lower() in ['да', 'yes']:
            game_state.online = 1
        elif message.text.lower() in ['нет', 'no']:
            game_state.online = 0
        else:
            msg = bot.send_message(message.chat.id, "Пожалуйста, ответьте 'Да' или 'Нет':")
            bot.register_next_step_handler(msg, process_online)
            return

        # Display game summary
        summary =  (f"<b><a href='{game_state.link}'>{game_state.name}</a></b>\n"
                            f"<code>Число игроков: {game_state.min_players}-{game_state.max_players}</code>\n \n"
                            f"<code>{game_state.description} </code>\n")
        bot.send_message(message.chat.id, "\n\n" + summary,parse_mode='HTML',disable_web_page_preview=True)

        # save_game_to_database
        crud.add_game(
            game_state.name, game_state.min_players, game_state.max_players, game_state.description, game_state.link, game_state.online
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('select_delete_game'))
    def handle_select_delete_game(call):
        user_id = call.from_user.id

        # Fetch hosted games from the database
        hosted_games = crud.get_hosted_games_by_user(user_id)

        if hosted_games:
            keyboard = InlineKeyboardMarkup()
            sorted_games = sorted(hosted_games, key=lambda game: (game.date, game.time))
            for game in sorted_games:
                # Get game details
                game_details = crud.get_game_details(game.game_id)
                if game_details is None:
                    continue  # Skip if game details are not found
                try:
                    # Parse game date and time
                    game_date = game.datetime
                    game_info = f'{game_details.name} - {game_date.strftime("%d.%m.%Y %H:%M")}'
                    # Add a button for each game
                    keyboard.add(InlineKeyboardButton(game_info, callback_data=f'delete_game_{game.id}'))
                except ValueError as e:
                    print(f"Error parsing date for game {game.id}: {e}")
                    continue  # Skip this game if date parsing fails

            # Acknowledge the callback query
            bot.answer_callback_query(call.id)

            # Send a message to display the inline keyboard
            bot.send_message(call.message.chat.id,
                            "Пожалуйста, выберите анонс, который хотите удалить",
                            reply_markup=keyboard)
        else:
            bot.answer_callback_query(call.id)

            # Inform the user that they are not an organizer of any games
            bot.send_message(call.message.chat.id,
                            "Вы не являетесь организатором ни одной игры.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('select_unsubscribe_game'))
    def handle_select_unsubscribe_game(call):
        bot.answer_callback_query(call.id)  # Acknowledge the callback query
        user_id = call.from_user.id
        enrolled_games = crud.get_enrolled_games_by_user(user_id)

        if enrolled_games:
            keyboard = InlineKeyboardMarkup()
            sorted_games = sorted(enrolled_games, key=lambda game: (game.date, game.time))
            for game in sorted_games:
                game_details = crud.get_game_details(game.game_id)
                game_datetime = game.datetime
                game_info = f'{game_details.name} - {game_datetime.strftime("%d.%m.%Y %H:%M")}'
                keyboard.add(InlineKeyboardButton(game_info, callback_data=f'unsubscribe_game_{game.id}'))
            bot.edit_message_text("Пожалуйста, выберите анонс, который хотите покинуть", call.message.chat.id,
                                call.message.message_id, reply_markup=keyboard)
        else:
            bot.answer_callback_query(call.id, "Вы не записаны ни на одну игру.", show_alert=True)


    @bot.callback_query_handler(func=lambda call: call.data.startswith('unsubscribe_game_'))
    def handle_unsubscribe_game(call):
        game_id = int(call.data.split('_')[-1])
        user_id = call.from_user.id

        result = crud.get_scheduled_game_by_id(game_id)

        if result:
            initiator_id = result.initiator_id
            if str(user_id) == str(initiator_id):
                bot.answer_callback_query(call.id, "Вы создали данную игру. Поэтому её можно только удалить.", show_alert=True)
                return

            enrolled_user_ids = result.player_ids.split(',') if result.player_ids else []
            player_nicknames = result.player_nicknames.split(',') if result.player_nicknames else []

            if str(user_id) in enrolled_user_ids:
                index = enrolled_user_ids.index(str(user_id))
                enrolled_user_ids.pop(index)
                player_nicknames.pop(index)

                updated_user_ids = ','.join(enrolled_user_ids)
                updated_nicknames = ','.join(player_nicknames)

                crud.update_scheduled_game_players(game_id, updated_user_ids, updated_nicknames)

                game_name = crud.get_game_name_by_id(result.game_id)
                game_date = result.date.strftime('%d.%m.%Y')
                game_time = result.time.strftime('%H:%M')

                unsubscribe_message = (f"Вы успешно отписались от игры <b>{game_name}</b> на "
                                    f" <b>{game_date}</b> в <b>{game_time}</b>.")
                bot.answer_callback_query(call.id, "Вы успешно отписались от игры.")
                bot.send_message(call.message.chat.id, unsubscribe_message, parse_mode='HTML')
            else:
                bot.answer_callback_query(call.id, "Вы не записаны на эту игру.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Игра не найдена.", show_alert=True)

    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_game_'))
    def handle_delete_game(call):
        game_id = int(call.data.split('_')[-1])
        user_id = call.from_user.id

        initiator_id, game_tree = crud.get_game_initiator_and_tree(game_id)

        if initiator_id and str(user_id) == str(initiator_id):
            # Ask the user if they want to delete a single game or the entire series
            markup = InlineKeyboardMarkup()
            single_game_btn = InlineKeyboardButton("Удалить только эту игру",
                                                        callback_data=f'delete_single_{game_id}')
            entire_series_btn = InlineKeyboardButton("Удалить всю серию игр",
                                                        callback_data=f'delete_series_{game_id}')
            markup.add(single_game_btn, entire_series_btn)

            bot.send_message(call.message.chat.id, "Вы хотите удалить только эту игру или всю серию?", reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "Вы не являетесь организатором этой игры.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_series_'))
    def handle_delete_series(call):
        game_id = int(call.data.split('_')[-1])
        user_id = call.from_user.id

        # Fetch the GameTree
        game_tree = crud.get_game_tree_by_id(game_id)

        if game_tree:  # Check if GameTree exists
            game_tree_ids = game_tree.split(',')

            # Include the parent game ID if it's not already in the GameTree
            if str(game_id) not in game_tree_ids:
                game_tree_ids.append(str(game_id))

            # Delete all games in the series
            crud.delete_games_by_ids(game_tree_ids)
            bot.answer_callback_query(call.id, "Серия игр успешно удалена.")
            bot.send_message(call.message.chat.id, "Вы успешно удалили всю серию игр.")
        else:
            bot.answer_callback_query(call.id, "Игра не является регулярной.", show_alert=True)


    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_single_'))
    def handle_delete_confirmation(call):
        game_id = int(call.data.split('_')[-1])
        user_id = call.from_user.id

        initiator_id, game_tree = crud.get_game_initiator_and_tree(game_id)

        if initiator_id and str(user_id) == str(initiator_id):
            if call.data.startswith('delete_single_'):
                # Delete only the selected game
                crud.update_game_skipped_status(game_id, True)
                bot.answer_callback_query(call.id, "Игра успешно удалена.")
                bot.send_message(call.message.chat.id, "Вы успешно удалили игру.")
        else:
            bot.answer_callback_query(call.id, app_strings.not_initiator, show_alert=True)


    @bot.callback_query_handler(
        func=lambda call: call.data.startswith('enroll') or call.data.startswith('back_to_main') or call.data.startswith('update_schedule') or call.data.startswith('my_games'))
    def handle_callback(call):
        bot.answer_callback_query(call.id)

        data = call.data
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        try:
            # Initial call when data is 'enroll'
            if data == 'enroll':
                available_games = crud.get_scheduled_games()

                if available_games:
                    handle_enroll_page(chat_id, available_games, page=1, message_id=message_id)
                else:
                    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='На данный момент нет доступных игр для записи.')

            # Handling page navigation
            elif data.startswith('enroll_page_'):
                page = int(data.split('_')[-1])
                available_games = crud.get_scheduled_games()
                handle_enroll_page(chat_id, available_games, page=page, message_id=message_id)

            # Handling game enrollment
            elif data.startswith('enroll_game_'):
                game_id = int(data.split('_')[2])
                user_id = call.from_user.id
                scheduled_game = crud.get_scheduled_game_by_id(game_id)

                player_ids = scheduled_game.player_ids.split(',') if scheduled_game.player_ids else []
                if str(user_id) in player_ids:
                    message = "Вы уже записались на эту игру"
                    bot.send_message(user_id, text=message, parse_mode="HTML", disable_web_page_preview=True)
                else:
                    lib_id = scheduled_game.game_id if scheduled_game else None
                    nickname = get_initiator_username(bot, call.message.chat.id, user_id)  # Fetch the user nickname
                    
                    game = crud.get_game_details(scheduled_game.game_id)
                    scheduled_game = crud.add_player_to_game(user_id, game_id, lib_id, nickname)  # Pass the nickname
                    if scheduled_game.server_data:
                        message = app_strings.game_info_steam_template.format(
                            game_name=game.name,
                            formatted_date_ru=scheduled_game.date.strftime('%d.%m.%Y'),
                            day_of_week=scheduled_game.date.strftime('%A'),
                            formatted_time=scheduled_game.time.strftime('%H:%M'),
                            room_link=config.app.room_to_link.get(str(scheduled_game.room)),
                            room=scheduled_game.room,
                            server_data=scheduled_game.server_data,
                            server_password=scheduled_game.server_password,
                            initiator_nickname=scheduled_game.initiator_name
                        )
                    else:
                        message = app_strings.game_info_template.format(
                            game_name=game.name,
                            formatted_date_ru=scheduled_game.date.strftime('%d.%m.%Y'),
                            room_link=config.app.room_to_link.get(str(scheduled_game.room)),
                            day_of_week=scheduled_game.date.strftime('%A'),
                            formatted_time=scheduled_game.time.strftime('%H:%M'),
                            room=scheduled_game.room,
                            initiator_nickname=scheduled_game.initiator_name
                        )

                    bot.send_message(user_id, text=message, parse_mode="HTML", disable_web_page_preview=True)

            # Handling callback data for main menu
            elif data == 'back_to_main':
                keyboard = InlineKeyboardMarkup()
                keyboard.row(InlineKeyboardButton("Записаться", callback_data='enroll'))
                keyboard.row(InlineKeyboardButton("Обновить расписание", callback_data='update_schedule'))
                keyboard.row(InlineKeyboardButton("Мои игры", callback_data='my_games'))
                new_text = 'Выберите действие:'
                bot.send_message(chat_id=chat_id, text=new_text, reply_markup=keyboard)

            # Handling callback data for 'my_games' and 'my_gamescommand'
            elif data == 'my_games' or data == 'my_gamescommand':
                user_id = call.from_user.id
                enrolled_games = crud.get_enrolled_games_by_user(user_id)
                if enrolled_games:
                    formatted_message, keyboard = format_enrolled_games(enrolled_games, chat_id, user_id)
                    bot.send_message(chat_id=chat_id, text=formatted_message, reply_markup=keyboard, parse_mode='HTML',
                                    disable_web_page_preview=True)
                else:
                    bot.send_message(chat_id, 'Вы не записаны на ни одну игру.')

            # Handling callback data for 'update_schedule'
            elif data == 'update_schedule':
                new_games = crud.get_scheduled_games()
                if new_games:
                    formatted_message = format_scheduled_games(bot, new_games, call.message.chat.id)
                    keyboard = InlineKeyboardMarkup()
                    keyboard.row(InlineKeyboardButton("Записаться", callback_data='enroll'))
                    keyboard.row(InlineKeyboardButton("Обновить расписание", callback_data='update_schedule'))
                    keyboard.row(InlineKeyboardButton("Мои игры", callback_data='my_games'))
                    bot.send_message(call.message.chat.id, text=formatted_message, reply_markup=keyboard, parse_mode='HTML',
                                    disable_web_page_preview=True)
                else:
                    bot.send_message(call.message.chat.id, 'На данный момент нет доступных игр для записи.')

        except Exception as e:
            print(f"Error in handle_callback: {e}")
            bot.send_message(chat_id, app_strings.error)
