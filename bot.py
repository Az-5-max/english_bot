import random
import os
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from dotenv import load_dotenv
import database as db

load_dotenv()

print('Запуск Telegram бота...')

state_storage = StateMemoryStorage()
bot = TeleBot(os.getenv('TOKEN_BOT'), state_storage=state_storage)


class MyStates(StatesGroup):
    target_word = State()
    wait_add_word_en = State()
    wait_add_word_ru = State()
    wait_delete_word = State()


class Command:
    ADD_WORD = '➕ Добавить слово'
    DELETE_WORD = 'Удалить слово'
    NEXT = '⏭ Дальше'


def create_card_buttons(telegram_id):
    user_words = db.get_user_words(telegram_id)

    if len(user_words) < 4:
        return None, None

    target = random.choice(user_words)
    other_words = [w for w in user_words if w['id'] != target['id']]
    other_words = random.sample(other_words, min(3, len(other_words)))

    options_ru = [w['word_ru'] for w in other_words] + [target['word_ru']]
    random.shuffle(options_ru)

    buttons = [types.KeyboardButton(word_ru) for word_ru in options_ru]

    next_btn = types.KeyboardButton(Command.NEXT)
    add_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_btn, delete_btn])

    return buttons, target


@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    username = message.from_user.username or "Unknown"

    db.add_user(cid, username)

    user_words = db.get_user_words(cid)
    if len(user_words) == 0:
        initial_words = ['Peace', 'Love', 'Hello', 'Goodbye', 'Cat', 'Dog', 'House', 'Car', 'Red', 'Blue']
        for word in initial_words:
            db.add_word_to_user(cid, word, '')

    bot.send_message(cid, f"Привет, {username}!\n\n"
                          f"Нажми /cards, чтобы начать.\n"
                          f"Добавляй новые слова\n"
                          f"Удаляй выученные")


@bot.message_handler(commands=['cards'])
def create_cards(message):
    cid = message.chat.id

    buttons, target = create_card_buttons(cid)

    if not buttons:
        bot.send_message(cid, "⚠️ Добавь больше слов кнопкой '➕ Добавить слово'")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)

    bot.send_message(cid, f"Выбери перевод слова:\n🇬🇧 {target['word_en']}", reply_markup=markup)

    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target['word_en']
        data['target_ru'] = target['word_ru']


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word_start(message):
    bot.send_message(message.chat.id, "Введите слово на английском:")
    bot.set_state(message.from_user.id, MyStates.wait_add_word_en, message.chat.id)


@bot.message_handler(state=MyStates.wait_add_word_en)
def add_word_en(message):
    word_en = message.text.strip().lower()

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_word_en'] = word_en

    bot.send_message(message.chat.id, "🇷🇺 Теперь введите перевод на русский:")
    bot.set_state(message.from_user.id, MyStates.wait_add_word_ru, message.chat.id)


@bot.message_handler(state=MyStates.wait_add_word_ru)
def add_word_ru(message):
    word_ru = message.text.strip()

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        word_en = data['new_word_en']

    db.add_word_to_user(message.chat.id, word_en, word_ru)
    count = db.get_user_words_count(message.chat.id)

    bot.send_message(message.chat.id, f"✅ Слово '{word_en}' добавлено!\n📚 Теперь {count} слов(а).")
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word_start(message):
    user_words = db.get_user_words(message.chat.id)

    if not user_words:
        bot.send_message(message.chat.id, "Нет слов для удаления!")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2)
    for word in user_words[:10]:
        markup.add(types.KeyboardButton(f"❌ {word['word_en']}"))
    markup.add(types.KeyboardButton("Назад"))

    bot.send_message(message.chat.id, "🗑 Выберите слово для удаления:", reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.wait_delete_word, message.chat.id)


@bot.message_handler(state=MyStates.wait_delete_word)
def delete_word_confirm(message):
    text = message.text

    if text == " Назад":
        create_cards(message)
        return

    if text.startswith("❌ "):
        word_en = text[2:]
        db.delete_user_word(message.chat.id, word_en)
        count = db.get_user_words_count(message.chat.id)
        bot.send_message(message.chat.id, f"✅ Слово '{word_en}' удалено!\n Теперь {count} слов(а).")

    bot.delete_state(message.from_user.id, message.chat.id)
    create_cards(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def check_answer(message):
    cid = message.chat.id
    answer = message.text.strip()

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_en = data.get('target_word', '')
        target_ru = data.get('target_ru', '')

    if answer == target_ru:
        bot.send_message(cid, f"✅ Правильно! 🎉\n\n🇬🇧 {target_en} → 🇷🇺 {target_ru}\n\nНажми 'Дальше'")
    else:
        bot.send_message(cid, f"❌ Неправильно!\n\n🇬🇧 {target_en} → 🇷🇺 {target_ru}\n\nПопробуй ещё раз!")


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)