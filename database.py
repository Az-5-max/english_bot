import sqlite3

DB_PATH = 'english_card.db'


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_en TEXT UNIQUE NOT NULL,
            word_ru TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_words (
            user_id INTEGER,
            word_id INTEGER,
            is_deleted INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, word_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (word_id) REFERENCES words(id)
        )
    ''')

    cur.execute("SELECT COUNT(*) FROM words")
    if cur.fetchone()[0] == 0:
        words = [
            ('Peace', 'Мир'), ('Love', 'Любовь'), ('Hello', 'Привет'),
            ('Goodbye', 'До свидания'), ('Cat', 'Кот'), ('Dog', 'Собака'),
            ('House', 'Дом'), ('Car', 'Машина'), ('Red', 'Красный'), ('Blue', 'Синий')
        ]
        cur.executemany("INSERT INTO words (word_en, word_ru) VALUES (?, ?)", words)

    conn.commit()
    conn.close()


def add_user(telegram_id, username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
                (telegram_id, username))
    conn.commit()
    conn.close()


def get_user_words(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT w.id, w.word_en, w.word_ru 
        FROM words w
        JOIN user_words uw ON w.id = uw.word_id
        JOIN users u ON uw.user_id = u.id
        WHERE u.telegram_id = ? AND uw.is_deleted = 0
    ''', (telegram_id,))
    rows = cur.fetchall()
    conn.close()
    return [{'id': row[0], 'word_en': row[1], 'word_ru': row[2]} for row in rows]


def add_word_to_user(telegram_id, word_en, word_ru):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM words WHERE word_en = ?", (word_en,))
    word = cur.fetchone()
    if not word:
        cur.execute("INSERT INTO words (word_en, word_ru) VALUES (?, ?)", (word_en, word_ru))
        word_id = cur.lastrowid
    else:
        word_id = word[0]

    cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    user_id = cur.fetchone()[0]

    cur.execute("INSERT OR REPLACE INTO user_words (user_id, word_id, is_deleted) VALUES (?, ?, 0)",
                (user_id, word_id))
    conn.commit()
    conn.close()
    return True


def delete_user_word(telegram_id, word_en):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM words WHERE word_en = ?", (word_en,))
    word = cur.fetchone()
    if not word:
        conn.close()
        return False

    cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return False

    cur.execute("UPDATE user_words SET is_deleted = 1 WHERE user_id = ? AND word_id = ?",
                (user[0], word[0]))
    conn.commit()
    conn.close()
    return True


def get_user_words_count(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM user_words uw
        JOIN users u ON uw.user_id = u.id
        WHERE u.telegram_id = ? AND uw.is_deleted = 0
    ''', (telegram_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


init_db()