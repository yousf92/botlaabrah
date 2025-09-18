import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time

# تکایە لێرەدا تۆکنەکەی خۆت دابنێ
# الرجاء وضع توكن البوت الخاص بك هنا
TOKEN = "8258693873:AAHKjyr8kUwcTORuOA1mLkJsLh0GZja9YiQ"

bot = telebot.TeleBot(TOKEN)

games = {}

# --- دوال مساعدة ---

def create_board(size):
    """إنشاء لوحة اللعب مع زر الاستسلام"""
    markup = InlineKeyboardMarkup()
    markup.row_width = size
    for i in range(size):
        row_buttons = []
        for j in range(size):
            row_buttons.append(InlineKeyboardButton(" ", callback_data=f"play_{i}_{j}"))
        markup.add(*row_buttons)
    
    markup.add(InlineKeyboardButton("🏳️ استسلام (Resign)", callback_data="resign"))
    return markup

def check_winner(board):
    """التحقق من وجود فائز"""
    size = len(board)
    for i in range(size):
        if len(set(board[i])) == 1 and board[i][0] != " ": return board[i][0]
        column = [board[r][i] for r in range(size)]
        if len(set(column)) == 1 and column[0] != " ": return column[0]
    diag1 = [board[i][i] for i in range(size)]
    if len(set(diag1)) == 1 and diag1[0] != " ": return diag1[0]
    diag2 = [board[i][size - 1 - i] for i in range(size)]
    if len(set(diag2)) == 1 and diag2[0] != " ": return diag2[0]
    return None

def game_timeout_checker(chat_id, message_id):
    """پشکنینی یارییەکان دوای ٥ خولەک"""
    time.sleep(300)
    if message_id in games and games[message_id]['player_o_id'] is None:
        try:
            bot.edit_message_text(
                "انتهى وقت انتظار هذه اللعبة وتم إلغاؤها.",
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None
            )
            del games[message_id]
        except Exception as e:
            print(f"Error in timeout: {e}")

# --- أوامر البوت ---

@bot.message_handler(commands=['start', 'help'])
def show_help(message):
    help_text = (
        "مرحباً بك في بوت لعبة إكس-أو!\n\n"
        "**طرق بدء اللعبة:**\n"
        "1️⃣ `/new_game` - لبدء لعبة مفتوحة لأي شخص.\n"
        "2️⃣ `/yala_ta3al` - قم بالرد على رسالة شخص ما بهذا الأمر لدعوته للعب.\n\n"
        "🔹 `/help` - لعرض هذه الرسالة."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['new_game', 'yala_ta3al'])
def start_game_handler(message):
    chat_id = message.chat.id
    command = message.text.split()[0]
    
    invited_player_id = None
    invited_player_name = None
    
    if command == '/yala_ta3al':
        if message.reply_to_message:
            invited_player_id = message.reply_to_message.from_user.id
            invited_player_name = message.reply_to_message.from_user.first_name
            if invited_player_id == message.from_user.id:
                bot.reply_to(message, "لا يمكنك أن تلعب مع نفسك!")
                return
        else:
            bot.reply_to(message, "لبدء لعبة مع شخص معين، يجب أن ترد على إحدى رسائله باستخدام الأمر `/yala_ta3al`.")
            return

    board_size = 3
    markup = create_board(board_size)
    
    if invited_player_id:
        text = (
            f"بدأت لعبة إكس-أو (٣x٣)!\n"
            f"اللاعب {message.from_user.first_name} (X) دعا {invited_player_name} (O) للعب.\n"
            f"الدور لـ {message.from_user.first_name} (X)."
        )
    else: # /new_game
        text = (
            f"بدأت لعبة إكس-أو (٣x٣)!\n"
            f"اللاعب {message.from_user.first_name} (X) يبدأ.\n"
            f"بانتظار انضمام اللاعب الثاني (O)..."
        )
    
    msg = bot.send_message(chat_id, text, reply_markup=markup)
    message_id = msg.message_id

    games[message_id] = {
        'chat_id': chat_id,
        'board': [[" " for _ in range(board_size)] for _ in range(board_size)],
        'turn': 'X',
        'player_x_id': message.from_user.id,
        'player_x_name': message.from_user.first_name,
        'player_o_id': invited_player_id,
        'player_o_name': invited_player_name,
        'board_size': board_size
    }
    
    if invited_player_id is None:
        timeout_thread = threading.Thread(target=game_timeout_checker, args=(chat_id, message_id))
        timeout_thread.start()

# --- وەڵامدانەوەی کرتەی دوگمەکان ---

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    if call.data.startswith('play_'):
        handle_play_move(call)
    elif call.data == 'resign':
        handle_resign(call)

def handle_resign(call):
    message_id = call.message.message_id
    user = call.from_user
    if message_id not in games:
        bot.answer_callback_query(call.id, "هذه اللعبة قد انتهت بالفعل.", show_alert=True)
        return
    game = games[message_id]
    if user.id == game['player_x_id']:
        winner_name = game.get('player_o_name', "اللاعب O")
    elif user.id == game['player_o_id']:
        winner_name = game['player_x_name']
    else:
        bot.answer_callback_query(call.id, "أنت لست جزءاً من هذه اللعبة.", show_alert=True)
        return
    text = f"استسلم اللاعب {user.first_name}!\nالفائز هو: {winner_name}\nلبدء لعبة جديدة: /new_game"
    bot.edit_message_text(text, game['chat_id'], message_id, reply_markup=None)
    del games[message_id]

def handle_play_move(call):
    message_id = call.message.message_id
    user = call.from_user
    if message_id not in games:
        bot.answer_callback_query(call.id, "هذه اللعبة قد انتهت أو تم إلغاؤها.", show_alert=True)
        return
    game = games[message_id]
    
    if game['player_o_id'] is None and user.id != game['player_x_id']:
        game['player_o_id'] = user.id
        game['player_o_name'] = user.first_name
        bot.answer_callback_query(call.id, f"{user.first_name} انضم كلاعب 'O'!")

    if (game['turn'] == 'X' and user.id != game['player_x_id']) or \
       (game['turn'] == 'O' and user.id != game['player_o_id']):
        bot.answer_callback_query(call.id, "ليس دورك!", show_alert=True)
        return

    _, r_str, c_str = call.data.split('_')
    row, col = int(r_str), int(c_str)

    if game['board'][row][col] == " ":
        game['board'][row][col] = game['turn']
        winner = check_winner(game['board'])
        if winner:
            winner_name = game['player_x_name'] if winner == 'X' else game['player_o_name']
            text = f"انتهت اللعبة!\nالفائز: {winner_name} ({winner})\nلبدء لعبة جديدة: /new_game"
            bot.edit_message_text(text, game['chat_id'], message_id, reply_markup=None)
            del games[message_id]
            return
        if all(cell != " " for row_board in game['board'] for cell in row_board):
            text = "انتهت اللعبة بالتعادل!\nلبدء لعبة جديدة: /new_game"
            bot.edit_message_text(text, game['chat_id'], message_id, reply_markup=None)
            del games[message_id]
            return

        game['turn'] = 'O' if game['turn'] == 'X' else 'X'
        markup = create_board(game['board_size'])
        for i in range(game['board_size']):
            for j in range(game['board_size']):
                markup.keyboard[i][j].text = game['board'][i][j]
        next_player_name = game['player_x_name'] if game['turn'] == 'X' else game['player_o_name']
        text = f"اللعبة بين {game['player_x_name']} (X) و {game['player_o_name']} (O).\nالدور الآن لـ {next_player_name} ({game['turn']})."
        bot.edit_message_text(text, game['chat_id'], message_id, reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "هذه الخانة ممتلئة!", show_alert=True)

print("البوت جاهز وبدأ بالعمل...")
bot.polling()
