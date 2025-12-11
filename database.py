import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            tg_username TEXT,
            mc_nick TEXT,
            call_as TEXT,
            age INTEGER,
            extra TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            edited_at TIMESTAMP,
            is_edited INTEGER DEFAULT 0,
            admin_message_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_form(data, admin_message_id=None):
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO forms (user_id, name, tg_username, mc_nick, call_as, age, extra, status, admin_message_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        data["user_id"],
        data["name"],
        data["tg_username"],
        data["mc_nick"],
        data["call_as"],
        data["age"],
        data["extra"],
        admin_message_id
    ))

    form_id = cur.lastrowid
    conn.commit()
    conn.close()
    return form_id


def get_all_forms():
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM forms ORDER BY id DESC")
    rows = cur.fetchall()

    conn.close()
    return rows


def get_user_form(user_id):
    """Получить последнюю анкету пользователя"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM forms 
        WHERE user_id = ? 
        ORDER BY id DESC 
        LIMIT 1
    """, (user_id,))
    
    row = cur.fetchone()
    conn.close()
    return row


def update_form_field(user_id, field_name, value):
    """Обновить конкретное поле анкеты"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    # Сначала получаем ID последней анкеты пользователя
    cur.execute("""
        SELECT id FROM forms 
        WHERE user_id = ? 
        ORDER BY id DESC 
        LIMIT 1
    """, (user_id,))
    
    result = cur.fetchone()
    if result:
        form_id = result[0]
        
        # Теперь обновляем конкретное поле
        query = f"""
            UPDATE forms 
            SET {field_name} = ?, edited_at = ?, is_edited = 1
            WHERE id = ?
        """
        
        cur.execute(query, (value, datetime.now(), form_id))
    
    conn.commit()
    conn.close()


def delete_form(form_id):
    """Удалить анкету по ID"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM forms WHERE id = ?", (form_id,))
    
    conn.commit()
    conn.close()


def delete_user_form(user_id):
    """Удалить анкету пользователя"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM forms WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()


def update_form_status(user_id, status):
    """Обновить статус анкеты"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE forms 
        SET status = ? 
        WHERE user_id = ?
    """, (status, user_id))
    
    conn.commit()
    conn.close()


def ban_user(user_id):
    """Забанить пользователя"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO banned_users (user_id) 
        VALUES (?)
    """, (user_id,))
    
    conn.commit()
    conn.close()


def is_banned(user_id):
    """Проверить, забанен ли пользователь"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    
    conn.close()
    return result is not None


def unban_user(user_id):
    """Разбанить пользователя"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()


def get_admin_message_id(user_id):
    """Получить ID сообщения в админ-чате для анкеты пользователя"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT admin_message_id FROM forms 
        WHERE user_id = ? 
        ORDER BY id DESC 
        LIMIT 1
    """, (user_id,))
    
    result = cur.fetchone()
    conn.close()
    return result[0] if result and result[0] else None


def update_admin_message_id(user_id, message_id):
    """Обновить ID сообщения в админ-чате"""
    conn = sqlite3.connect("forms.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE forms 
        SET admin_message_id = ? 
        WHERE user_id = ?
        AND id = (SELECT id FROM forms WHERE user_id = ? ORDER BY id DESC LIMIT 1)
    """, (message_id, user_id, user_id))
    
    conn.commit()
    conn.close()

init_db()