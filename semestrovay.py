import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

TELEGRAM_BOT_TOKEN = '6930378447:AAGJ97xZbLAuOw0oPQPt2RcdXfryQ_cTXuU'
OPENDOTA_API_URL = 'https://api.opendota.com/api'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

HEROES = {}
ITEMS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("Ввести Player ID")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text('Привет! Пожалуйста, введите ваш Player ID:', reply_markup=reply_markup)

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("/lastmatches"), KeyboardButton("/topheroes_pickrate"), KeyboardButton("/topheroes_winrate")],
        [KeyboardButton("/herostats"), KeyboardButton("/heroitems"), KeyboardButton("/back")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        'Вы можете использовать следующие команды:\n'
        '/lastmatches - последние 5 игр\n'
        '/topheroes_pickrate - топ 5 героев по pickrate\n'
        '/topheroes_winrate - топ 5 героев по winrate\n'
        '/herostats - статистика героя\n'
        '/heroitems - популярные предметы героя',
        reply_markup=reply_markup
    )

async def request_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("/back")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text('Пожалуйста, введите ваш Player ID:', reply_markup=reply_markup)

def get_heroes():
    global HEROES
    response = requests.get(f'{OPENDOTA_API_URL}/heroes')
    if response.status_code == 200:
        heroes = response.json()
        HEROES = {hero['localized_name'].lower(): hero for hero in heroes}
    else:
        logger.error('Не удалось получить героев из API OpenDota')

def get_items():
    global ITEMS
    response = requests.get(f'{OPENDOTA_API_URL}/constants/items')
    if response.status_code == 200:
        items = response.json()
        ITEMS = {str(item['id']): item['dname'] for item in items.values() if 'id' in item and 'dname' in item}
    else:
        logger.error('Не удалось получить элементы из API OpenDota')

def get_last_matches(player_id: str, num_matches: int = 5):
    response = requests.get(f'{OPENDOTA_API_URL}/players/{player_id}/recentMatches')
    if response.status_code == 200:
        matches = response.json()
        if matches:
            return matches[:num_matches]
        else:
            return 'Для этого игрока не найдено ни одного совпадения.'
    else:
        return 'Ошибка при получении данных из API OpenDota.'

def get_match_details(match_id: int):
    response = requests.get(f'{OPENDOTA_API_URL}/matches/{match_id}')
    if response.status_code == 200:
        return response.json()
    else:
        return None

async def lastmatches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    player_id = context.user_data.get('player_id')
    if not player_id:
        await update.message.reply_text('Пожалуйста, введите ваш Player ID, используя кнопку "Ввести Player ID".')
        return
    
    matches = get_last_matches(player_id)
    if isinstance(matches, str):
        await update.message.reply_text(matches)
        return
    
    messages = []
    for match in matches:
        match_id = match['match_id']
        match_details = get_match_details(match_id)
        if match_details:
            radiant_win = match_details['radiant_win']
            radiant_networth = sum(player['net_worth'] for player in match_details['players'] if player['isRadiant'])
            dire_networth = sum(player['net_worth'] for player in match_details['players'] if not player['isRadiant'])
            result = 'Radiant Win' if radiant_win else 'Dire Win'
            
            message = (
                f"Матч ID: {match_id}\n"
                f"Результат: {result}\n"
                f"Radiant Net Worth: {radiant_networth}\n"
                f"Dire Net Worth: {dire_networth}\n"
                f"Kills: {match['kills']}, Deaths: {match['deaths']}, Assists: {match['assists']}\n"
            )
            messages.append(message)
        else:
            messages.append(f"Не удалось получить детали матча с ID {match_id}")
    
    await update.message.reply_text("\n\n".join(messages))

def get_top_heroes(player_id: str):
    response = requests.get(f'{OPENDOTA_API_URL}/players/{player_id}/heroes')
    if response.status_code == 200:
        return response.json()
    else:
        return 'Ошибка при получении данных из API OpenDota.'

async def topheroes_pickrate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    player_id = context.user_data.get('player_id')
    if not player_id:
        await update.message.reply_text('Пожалуйста, введите ваш Player ID, используя кнопку "Ввести Player ID".')
        return

    heroes = get_top_heroes(player_id)
    if isinstance(heroes, str):
        await update.message.reply_text(heroes)
        return

    top_pickrate_heroes = sorted(heroes, key=lambda x: x['games'], reverse=True)[:5]
    messages = []
    for hero in top_pickrate_heroes:
        hero_id = hero['hero_id']
        hero_name = next((name for name, details in HEROES.items() if details['id'] == hero_id), 'Unknown Hero')
        games = hero['games']
        winrate = (hero['win'] / games) * 100 if games > 0 else 0
        messages.append(f"Герой: {hero_name}, Кол-во игр: {games}, Winrate: {winrate:.2f}%")
    
    await update.message.reply_text("\n".join(messages))

async def topheroes_winrate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    player_id = context.user_data.get('player_id')
    if not player_id:
        await update.message.reply_text('Пожалуйста, введите ваш Player ID, используя кнопку "Ввести Player ID".')
        return

    heroes = get_top_heroes(player_id)
    if isinstance(heroes, str):
        await update.message.reply_text(heroes)
        return

    top_winrate_heroes = sorted(heroes, key=lambda x: (x['win'] / x['games']) if x['games'] > 0 else 0, reverse=True)[:5]
    messages = []
    for hero in top_winrate_heroes:
        hero_id = hero['hero_id']
        hero_name = next((name for name, details in HEROES.items() if details['id'] == hero_id), 'Unknown Hero')
        games = hero['games']
        winrate = (hero['win'] / games) * 100 if games > 0 else 0
        messages.append(f"Герой: {hero_name}, Winrate: {winrate:.2f}%, Кол-во игр: {games}")
    
    await update.message.reply_text("\n".join(messages))


def get_hero_stats(hero_name: str):
    response = requests.get(f'{OPENDOTA_API_URL}/heroStats')
    if response.status_code == 200:
        heroes_stats = response.json()
        for hero in heroes_stats:
            if hero['localized_name'].lower() == hero_name.lower():
                return hero
        return 'Герой не найден.'
    else:
        return 'Ошибка при получении данных из API OpenDota.'

def get_hero_items(hero_id: int):
    response = requests.get(f'{OPENDOTA_API_URL}/heroes/{hero_id}/itemPopularity')
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f'Error fetching hero items for hero ID {hero_id}: {response.status_code}')
        return 'Ошибка при получении данных из API OpenDota.'

async def herostats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Пожалуйста, введите имя героя:')
    context.user_data['awaiting_hero_name'] = 'herostats'

async def heroitems(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Пожалуйста, введите имя героя:')
    context.user_data['awaiting_hero_name'] = 'heroitems'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'awaiting_hero_name' in context.user_data:
        hero_name = update.message.text.strip().lower()
        logger.info(f"Получено имя героя: {hero_name}")

        if hero_name not in HEROES:
            await update.message.reply_text('Герой не найден. Пожалуйста, введите действительное имя героя.')
            return

        if context.user_data['awaiting_hero_name'] == 'herostats':
            hero_stats = get_hero_stats(hero_name)
            if isinstance(hero_stats, str):
                await update.message.reply_text(hero_stats)
                return
            logger.info(f"Данные статистики героя: {hero_stats}")
            total_pro_pick = sum(hero.get('pro_pick', 0) for hero in HEROES.values())
            message = (
                f"Герой: {hero_stats['localized_name']}\n"
                f"Winrate: {hero_stats['pro_win'] / hero_stats.get('pro_pick', 1) * 100:.2f}%\n"
                f"Pickrate: {hero_stats.get('pro_pick', 0) / total_pro_pick * 100 if total_pro_pick > 0 else 0:.2f}%\n"
            )

            if '3' in hero_stats:
                message += (
                    f"Avg Kills: {hero_stats['3']['avg_kills']:.2f}\n"
                    f"Avg Deaths: {hero_stats['3']['avg_deaths']:.2f}\n"
                    f"Avg Assists: {hero_stats['3']['avg_assists']:.2f}\n"
                )
            else:
                message += "Средняя статистика (убийства, смерти, помощи) недоступна.\n"
            overall_health = hero_stats['base_health'] + (hero_stats['base_str'] * 22)
            overall_armor = hero_stats['base_armor'] + (hero_stats['base_agi'] * 0.17)
            overall_mana = hero_stats['base_mana'] + (hero_stats['base_int'] * 12)

            message += (
                f"ID: {hero_stats['id']}\n"
                f"Primary Attribute: {hero_stats['primary_attr']}\n"
                f"Attack Type: {hero_stats['attack_type']}\n"
                f"Roles: {', '.join(hero_stats['roles'])}\n"
                f"Base Health: {hero_stats['base_health']}\n"
                f"Base Health Regen: {hero_stats['base_health_regen']}\n"
                f"Base Mana: {hero_stats['base_mana']}\n"
                f"Base Mana Regen: {hero_stats['base_mana_regen']}\n"
                f"Base Armor: {hero_stats['base_armor']}\n"
                f"Base Magic Resist: {hero_stats['base_mr']}\n"
                f"Base Attack Min: {hero_stats['base_attack_min']}\n"
                f"Base Attack Max: {hero_stats['base_attack_max']}\n"
                f"Base Strength: {hero_stats['base_str']}\n"
                f"Strength Gain: {hero_stats['str_gain']}\n"
                f"Base Agility: {hero_stats['base_agi']}\n"
                f"Agility Gain: {hero_stats['agi_gain']}\n"
                f"Base Intelligence: {hero_stats['base_int']}\n"
                f"Intelligence Gain: {hero_stats['int_gain']}\n"
                f"Attack Range: {hero_stats['attack_range']}\n"
                f"Projectile Speed: {hero_stats['projectile_speed']}\n"
                f"Attack Rate: {hero_stats['attack_rate']}\n"
                f"Move Speed: {hero_stats['move_speed']}\n"
                f"Legs: {hero_stats['legs']}\n"
                f"Day Vision: {hero_stats['day_vision']}\n"
                f"Night Vision: {hero_stats['night_vision']}\n"
                f"Overall Health: {overall_health}\n"
                f"Overall Armor: {overall_armor:.2f}\n"
                f"Overall Mana: {overall_mana}\n"
            )

            await update.message.reply_text(message)

        elif context.user_data['awaiting_hero_name'] == 'heroitems':
            hero_id = HEROES[hero_name]['id']
            hero_items = get_hero_items(hero_id)
            if isinstance(hero_items, str):
                await update.message.reply_text(hero_items)
                return

            logger.info(f"Полученные данные предметов для героя {hero_name}: {hero_items}")
            start_game_items = hero_items.get('start_game_items', {})
            if not start_game_items:
                await update.message.reply_text(f'Не удалось получить популярные предметы для {HEROES[hero_name]["localized_name"]}.')
                return
            
            messages = [f"Популярные предметы в начале игры для {HEROES[hero_name]['localized_name']}:"]
            for item_id, count in start_game_items.items():
                item_name = ITEMS.get(str(item_id), f'Unknown Item ID: {item_id}')
                messages.append(f"Item: {item_name}, Count: {count}")
            
            await update.message.reply_text("\n".join(messages))

        del context.user_data['awaiting_hero_name']
    else:
        player_id = update.message.text.strip()
        if player_id == "/back":
            await request_player_id(update, context)
            return

        if not player_id.isdigit():
            await update.message.reply_text('Пожалуйста, введите действительный Player ID.')
            return

        context.user_data['player_id'] = player_id
        await update.message.reply_text(f'Player ID {player_id} успешно сохранен!')
        await show_commands(update, context)


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await request_player_id(update, context)

def main() -> None:
    get_heroes()
    get_items()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lastmatches", lastmatches))
    application.add_handler(CommandHandler("topheroes_pickrate", topheroes_pickrate))
    application.add_handler(CommandHandler("topheroes_winrate", topheroes_winrate))
    application.add_handler(CommandHandler("herostats", herostats))
    application.add_handler(CommandHandler("heroitems", heroitems))
    application.add_handler(CommandHandler("back", back))
    application.add_handler(MessageHandler(filters.Regex('^Ввести Player ID$'), request_player_id))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
