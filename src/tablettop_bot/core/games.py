"""Application that provides functionality for the Telegram bot."""

import logging.config

from tablettop_bot.db import crud

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_summary(game_id, scheduled_datetime, serverdata, server_password, use_steam, ini_id, discord_telegram_link,
                     room, flag, repeat):
    game_details = crud.get_game_details(game_id)

    if game_details is None:
        return "Ошибка: Игра не найдена."

    if repeat:
        time_repeat = f"Дата проведения: Еженедельно с {scheduled_datetime.strftime('%d.%m.%Y')} \n"
    else:
        time_repeat = f"Дата проведения: {scheduled_datetime.strftime('%d.%m.%Y')}\n"

    summary = (
        f"<b>Игра успешно создана!</b>\n\n"
        f"{time_repeat}"
        f"Время: {scheduled_datetime.strftime('%H:%M')} (UTC+3 MSK)\n\n"
        f"<a href = '{discord_telegram_link}'>Ссылка на комнату #{room} в Discord</a>\n\n"
    )

    if use_steam:
        summary += (
            f"Сервер в Tabletop Simulator: {serverdata if serverdata else 'N/A'}\n"
            f"Пароль от сервера: {server_password if server_password else 'N/A'}\n\n"
        )

    if not flag:
        summary += f"Ведущий: {ini_id}\n\n"
    else:
        summary += f"Ведущий: @{ini_id}\n\n"

    return summary
