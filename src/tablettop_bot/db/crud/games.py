import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Game, ScheduledGame

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_game(
    name: str, min_players: int, max_players: int,
    description: str = "", link: str = "", online: bool = False
    ):
    db: Session = get_session()
    game = Game(
        name=name, min_players=min_players, max_players=max_players,
        description=description, link=link, online=online
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game

def schedule_game(game_id: int, scheduled_datetime, initiator_id: int, nickname: str, use_steam: bool, server_password: str, serverdata: str, discord_telegram_link: str = None, room: int = None, repeat_weekly: bool = False):
    db: Session = get_session()
    scheduled_game = ScheduledGame(
        game_id=game_id,
        date=scheduled_datetime.date(),
        time=scheduled_datetime.time(),
        datetime=scheduled_datetime,
        initiator_id=initiator_id,
        initiator_name=nickname,
        use_steam=use_steam,
        server_password=server_password,
        server_data=serverdata,
        discord_telegram_link=discord_telegram_link,
        player_ids=str(initiator_id),
        player_nicknames=nickname,
        room=room,
        repweekly=repeat_weekly
    )
    db.add(scheduled_game)
    db.commit()
    db.refresh(scheduled_game)
    return scheduled_game

def add_player_to_game(user_id: int, scheduled_game_id: int, lib_game_id: int, user_nickname: str):
    db: Session = get_session()
    scheduled_game = db.query(ScheduledGame).filter(ScheduledGame.id == scheduled_game_id).first()
    if not scheduled_game:
        return False, 'Игра не найдена.'

    player_ids = scheduled_game.player_ids.split(',') if scheduled_game.player_ids else []
    player_nicknames = scheduled_game.player_nicknames.split(',') if scheduled_game.player_nicknames else []

    player_ids.append(str(user_id))
    player_nicknames.append(user_nickname)

    scheduled_game.player_ids = ','.join(player_ids)
    scheduled_game.player_nicknames = ','.join(player_nicknames)
    db.commit()
    db.refresh(scheduled_game)
    return scheduled_game

def get_all_games():
    db: Session = get_session()
    return db.query(Game).order_by(Game.name).all()

def get_game_details(game_id: int):
    db: Session = get_session()
    return db.query(Game).filter(Game.id == game_id).first()

def get_scheduled_games():
    db: Session = get_session()
    return db.query(ScheduledGame).filter(
        ScheduledGame.skipped == 0, ScheduledGame.date >= datetime.now().date()
        ).order_by(ScheduledGame.date, ScheduledGame.time).all()

def get_online_games():
    db: Session = get_session()
    return db.query(Game).filter(Game.online == 1).order_by(Game.name).all()

def get_offline_games():
    db: Session = get_session()
    return db.query(Game).filter(Game.online == 0).order_by(Game.name).all()

def get_available_room(selected_datetime: datetime):
    db: Session = get_session()
    scheduled_games = db.query(ScheduledGame).all()
    taken_rooms = [
        game.room for game in scheduled_games
        if game.datetime + timedelta(hours=9) > selected_datetime
    ]

    for room in range(1, 21):
        db: Session = get_session()
        if room not in taken_rooms:
            return room
    return None

def get_scheduled_game_by_id(game_id: int):
    db: Session = get_session()
    return db.query(ScheduledGame).filter(ScheduledGame.id == game_id, ScheduledGame.skipped == 0).first()

def update_scheduled_game_players(game_id: int, player_ids: str, player_nicknames: str):
    db: Session = get_session()
    scheduled_game = db.query(ScheduledGame).filter(ScheduledGame.id == game_id).first()
    if scheduled_game:
        scheduled_game.player_ids = player_ids
        scheduled_game.player_nicknames = player_nicknames
        db.commit()
    return scheduled_game

# filepath: /home/verner/tablettop_bot/src/tablettop_bot/db/crud/games.py
def get_game_name_by_id(game_id: int):
    db: Session = get_session()
    game = db.query(Game).filter(Game.id == game_id).first()
    return game.name if game else "Unknown Game"

def prolong():
    db: Session = get_session()
    today = datetime.now()
    scheduled_games = db.query(ScheduledGame).filter(ScheduledGame.repweekly == True).all()

    for game in scheduled_games:
        game_datetime = datetime.combine(game.date, game.time)
        next_game_datetime = game_datetime + timedelta(days=7)

        if today <= next_game_datetime < today + timedelta(days=21):
            db: Session = get_session()
            new_room = get_available_room(next_game_datetime)
            if new_room:
                new_scheduled_game = ScheduledGame(
                    game_id=game.game_id,
                    date=next_game_datetime.date(),
                    time=next_game_datetime.time(),
                    datetime=next_game_datetime,
                    initiator_id=game.initiator_id,
                    initiator_name=game.initiator_name,
                    use_steam=game.use_steam,
                    server_data=game.server_data,
                    server_password=game.server_password,
                    discord_telegram_link=game.discord_telegram_link,
                    player_ids=game.player_ids,
                    player_nicknames=game.player_nicknames,
                    room=new_room,
                    repweekly=game.repweekly,
                    PGID=game.id,
                    GameTree=game.GameTree,
                    skipped=False
                )
                db.add(new_scheduled_game)
                db.commit()
                update_gametree(game.id, new_scheduled_game.id)

def update_gametree(parent_game_id: int, new_game_id: int = None):
    db: Session = get_session()
    parent_game = db.query(ScheduledGame).filter(ScheduledGame.id == parent_game_id).first()
    if not parent_game:
        return

    game_tree = parent_game.GameTree.split(',') if parent_game.GameTree else []
    if new_game_id:
        game_tree.append(str(new_game_id))
    game_tree.append(str(parent_game_id))
    updated_gametree = ','.join(sorted(set(game_tree)))

    db.query(ScheduledGame).filter(ScheduledGame.id.in_(game_tree)).update({"GameTree": updated_gametree}, synchronize_session=False)
    db.commit()

def get_enrolled_games_by_user(user_id: int):
    db: Session = get_session()
    return db.query(ScheduledGame).filter(ScheduledGame.skipped == 0, ScheduledGame.player_ids.like(f'%{user_id}%')).all()

def get_hosted_games_by_user(user_id: int):
    db: Session = get_session()
    return db.query(ScheduledGame).filter(ScheduledGame.skipped == 0, ScheduledGame.initiator_id == user_id).all()

def get_game_tree_by_id(game_id: int):
    db: Session = get_session()
    scheduled_game = db.query(ScheduledGame).filter(ScheduledGame.id == game_id).first()
    return scheduled_game.GameTree if scheduled_game else None

def update_game_skipped_status(game_id: int, skipped: bool):
    db: Session = get_session()
    scheduled_game = db.query(ScheduledGame).filter(ScheduledGame.id == game_id).first()
    if scheduled_game:
        scheduled_game.skipped = skipped
        db.commit()
    return scheduled_game

def delete_games_by_ids(game_ids: list):
    db: Session = get_session()
    db.query(ScheduledGame).filter(ScheduledGame.id.in_(game_ids)).delete(synchronize_session=False)
    db.commit()

def get_game_initiator_and_tree(game_id: int):
    db: Session = get_session()
    scheduled_game = db.query(ScheduledGame).filter(ScheduledGame.id == game_id).first()
    if scheduled_game:
        return scheduled_game.initiator_id, scheduled_game.GameTree
    return None, None

def delete_past_games(cutoff_time):
    db: Session = get_session()
    db.query(ScheduledGame).filter(
        ScheduledGame.datetime < cutoff_time
    ).delete()
    db.commit()

def get_enrolled_players(id: int):
    db: Session = get_session()
    scheduled_game = db.query(ScheduledGame).filter(ScheduledGame.skipped == 0, ScheduledGame.id == id).first()
    if scheduled_game:
        return scheduled_game.player_ids.split(','), scheduled_game.player_nicknames.split(',')
    return None, None

def synchronize_series_players(game_id: int):
    db: Session = get_session()
    game = db.query(ScheduledGame).filter(ScheduledGame.id == game_id).first()
    if not game or not game.GameTree:
        return

    game_tree_ids = game.GameTree.split(',')
    all_players = []

    for g_id in game_tree_ids:
        g = db.query(ScheduledGame).filter(ScheduledGame.id == g_id).first()
        if g:
            player_ids = g.player_ids.split(',') if g.player_ids else []
            player_nicknames = g.player_nicknames.split(',') if g.player_nicknames else []
            all_players.extend(zip(player_ids, player_nicknames))

    all_player_ids_str = ','.join([pid for pid, _ in all_players])
    all_player_nicknames_str = ','.join([pname for _, pname in all_players])

    db.query(ScheduledGame).filter(ScheduledGame.id.in_(game_tree_ids)).update({"player_ids": all_player_ids_str, "player_nicknames": all_player_nicknames_str}, synchronize_session=False)
    db.commit()
