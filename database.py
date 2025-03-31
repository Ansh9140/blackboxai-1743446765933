import sqlite3
from sqlite3 import Error
import hashlib
import os

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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create sessions table
            c.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create admin table
            c.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default admin if not exists
            admin_password = hashlib.sha256("admin123!".encode()).hexdigest()
            c.execute('''
                INSERT OR IGNORE INTO admins (username, password)
                VALUES (?, ?)
            ''', ('admin', admin_password))
            
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

def create_session(user_id):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Generate a random session ID
            session_id = hashlib.sha256(os.urandom(32)).hexdigest()
            c.execute('''
                INSERT INTO sessions (user_id, session_id)
                VALUES (?, ?)
            ''', (user_id, session_id))
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

def verify_admin_login(username, password):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            c.execute('''
                SELECT id FROM admins 
                WHERE username = ? AND password = ?
            ''', (username, hashed_password))
            admin = c.fetchone()
            return admin is not None
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
            c.execute('''
                SELECT id, username, email, mobile, telegram, status, created_at 
                FROM users 
                ORDER BY created_at DESC
            ''')
            return c.fetchall()
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
            c.execute('''
                UPDATE users 
                SET status = 'approved' 
                WHERE id = ?
            ''', (user_id,))
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
            c.execute('''
                UPDATE users 
                SET status = 'rejected' 
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            return True
        except Error as e:
            print(e)
            return False
        finally:
            conn.close()
    return False

# Initialize the database when the module is imported
init_database()