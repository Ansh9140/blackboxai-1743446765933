import sqlite3
from sqlite3 import Error
import hashlib
import uuid
from datetime import datetime

def create_connection():
    try:
        conn = sqlite3.connect('lqr_group.db')
        return conn
    except Error as e:
        print(e)
    return None

def init_database():
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            
            # Create users table
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    mobile TEXT NOT NULL,
                    telegram TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    accept_calls BOOLEAN DEFAULT 1
                )
            ''')
            
            # Create sessions table
            c.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create chat_rooms table
            c.execute('''
                CREATE TABLE IF NOT EXISTS chat_rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create chat_messages table
            c.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES chat_rooms (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create call_logs table
            c.execute('''
                CREATE TABLE IF NOT EXISTS call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    duration INTEGER,
                    FOREIGN KEY (caller_id) REFERENCES users (id),
                    FOREIGN KEY (receiver_id) REFERENCES users (id)
                )
            ''')
            
            # Create blocked_users table
            c.execute('''
                CREATE TABLE IF NOT EXISTS blocked_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    blocker_id INTEGER NOT NULL,
                    blocked_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (blocker_id) REFERENCES users (id),
                    FOREIGN KEY (blocked_id) REFERENCES users (id)
                )
            ''')

            # Create default chat rooms if they don't exist
            default_rooms = ['General', 'Support', 'Off-Topic']
            for room in default_rooms:
                c.execute('INSERT OR IGNORE INTO chat_rooms (name) VALUES (?)', (room,))
            
            conn.commit()
            print("Database initialized successfully")
        except Error as e:
            print(e)
        finally:
            conn.close()

def register_user(username, email, password, mobile, telegram):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            c.execute('''
                INSERT INTO users (username, email, password, mobile, telegram)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, hashed_password, mobile, telegram))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def verify_login(username, password):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            c.execute('''
                SELECT id, username, status FROM users 
                WHERE username = ? AND password = ?
            ''', (username, hashed_password))
            user = c.fetchone()
            if user:
                return {'id': user[0], 'username': user[1], 'status': user[2]}
            return None
        except Error as e:
            print(e)
            return None
        finally:
            conn.close()
    return None

def create_session(user_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            session_id = str(uuid.uuid4())
            c.execute('INSERT INTO sessions (session_id, user_id) VALUES (?, ?)',
                     (session_id, user_id))
            conn.commit()
            return session_id
        except Error as e:
            print(e)
            return None
        finally:
            conn.close()
    return None

def verify_session(session_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                SELECT u.id, u.username, u.status
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_id = ?
            ''', (session_id,))
            result = c.fetchone()
            if result:
                return {'id': result[0], 'username': result[1], 'status': result[2]}
            return None
        except Error as e:
            print(e)
            return None
        finally:
            conn.close()
    return None

def delete_session(session_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def get_all_users():
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('SELECT id, username, email, status FROM users')
            users = c.fetchall()
            return [{'id': u[0], 'username': u[1], 'email': u[2], 'status': u[3]} for u in users]
        except Error as e:
            print(e)
            return []
        finally:
            conn.close()
    return []

def approve_user(user_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('UPDATE users SET status = "approved" WHERE id = ?', (user_id,))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def reject_user(user_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('UPDATE users SET status = "rejected" WHERE id = ?', (user_id,))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def verify_admin_login(username, password):
    # For demo purposes, hardcoded admin credentials
    admin_username = "admin"
    admin_password = "admin123"
    return username == admin_username and password == admin_password

def get_chat_messages(room_id, limit=50):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                SELECT m.id, m.message, m.created_at, u.username
                FROM chat_messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.room_id = ?
                ORDER BY m.created_at DESC
                LIMIT ?
            ''', (room_id, limit))
            messages = c.fetchall()
            return [{'id': m[0], 'message': m[1], 'created_at': m[2], 'username': m[3]} for m in messages]
        except Error as e:
            print(e)
            return []
        finally:
            conn.close()
    return []

def save_chat_message(room_id, user_id, message):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                INSERT INTO chat_messages (room_id, user_id, message)
                VALUES (?, ?, ?)
            ''', (room_id, user_id, message))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def log_call(caller_id, receiver_id, status):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                INSERT INTO call_logs (caller_id, receiver_id, status)
                VALUES (?, ?, ?)
            ''', (caller_id, receiver_id, status))
            conn.commit()
            return c.lastrowid
        except Error as e:
            print(e)
            return None
        finally:
            conn.close()
    return None

def end_call(call_id, duration):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                UPDATE call_logs 
                SET ended_at = CURRENT_TIMESTAMP,
                    duration = ?
                WHERE id = ?
            ''', (duration, call_id))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def get_call_logs(user_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                SELECT 
                    l.id,
                    caller.username as caller,
                    receiver.username as receiver,
                    l.status,
                    l.started_at,
                    l.ended_at,
                    l.duration
                FROM call_logs l
                JOIN users caller ON l.caller_id = caller.id
                JOIN users receiver ON l.receiver_id = receiver.id
                WHERE l.caller_id = ? OR l.receiver_id = ?
                ORDER BY l.started_at DESC
            ''', (user_id, user_id))
            logs = c.fetchall()
            return [{
                'id': l[0],
                'caller': l[1],
                'receiver': l[2],
                'status': l[3],
                'started_at': l[4],
                'ended_at': l[5],
                'duration': l[6]
            } for l in logs]
        except Error as e:
            print(e)
            return []
        finally:
            conn.close()
    return []

def block_user(blocker_id, blocked_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                INSERT INTO blocked_users (blocker_id, blocked_id)
                VALUES (?, ?)
            ''', (blocker_id, blocked_id))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def unblock_user(blocker_id, blocked_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                DELETE FROM blocked_users
                WHERE blocker_id = ? AND blocked_id = ?
            ''', (blocker_id, blocked_id))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def is_blocked(user_id, target_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                SELECT COUNT(*) FROM blocked_users
                WHERE (blocker_id = ? AND blocked_id = ?) OR
                      (blocker_id = ? AND blocked_id = ?)
            ''', (user_id, target_id, target_id, user_id))
            count = c.fetchone()[0]
            return count > 0
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def toggle_call_acceptance(user_id, accept):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''
                UPDATE users
                SET accept_calls = ?
                WHERE id = ?
            ''', (1 if accept else 0, user_id))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

def get_call_preferences(user_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('SELECT accept_calls FROM users WHERE id = ?', (user_id,))
            result = c.fetchone()
            return bool(result[0]) if result else True
        except Error as e:
            print(e)
            return True
        finally:
            conn.close()
    return True

# Initialize the database when the module is imported
init_database()