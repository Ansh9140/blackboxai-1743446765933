import asyncio
import websockets
import json
from collections import defaultdict
import sqlite3
from datetime import datetime

# Store active connections and their types
chat_connections = {}
voip_connections = {}

# Store chat rooms and their members
chat_rooms = defaultdict(set)

def create_db_connection():
    return sqlite3.connect('lqr_group.db')

async def save_chat_message(room_id, username, message):
    conn = create_db_connection()
    try:
        c = conn.cursor()
        c.execute('''
            INSERT INTO chat_messages (room_id, user_id, message)
            SELECT ?, id, ?
            FROM users WHERE username = ?
        ''', (room_id, message, username))
        conn.commit()
    finally:
        conn.close()

async def get_chat_history(room_id, limit=50):
    conn = create_db_connection()
    try:
        c = conn.cursor()
        c.execute('''
            SELECT u.username, m.message, m.created_at
            FROM chat_messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.room_id = ?
            ORDER BY m.created_at DESC
            LIMIT ?
        ''', (room_id, limit))
        messages = c.fetchall()
        return [{'username': m[0], 'content': m[1], 'timestamp': m[2]} for m in messages]
    finally:
        conn.close()

async def handle_chat_message(websocket, username, data):
    if data['type'] == 'join_room':
        room_id = data['room']
        chat_rooms[room_id].add(username)
        # Send room history
        history = await get_chat_history(room_id)
        await websocket.send(json.dumps({
            'type': 'history',
            'messages': history
        }))
        # Notify others
        for member in chat_rooms[room_id]:
            if member != username and member in chat_connections:
                await chat_connections[member].send(json.dumps({
                    'type': 'system',
                    'content': f'{username} joined the room'
                }))

    elif data['type'] == 'leave_room':
        room_id = data['room']
        chat_rooms[room_id].discard(username)
        # Notify others
        for member in chat_rooms[room_id]:
            if member in chat_connections:
                await chat_connections[member].send(json.dumps({
                    'type': 'system',
                    'content': f'{username} left the room'
                }))

    elif data['type'] == 'message':
        room_id = data['room']
        content = data['content']
        # Save to database
        await save_chat_message(room_id, username, content)
        # Broadcast to room members
        message = {
            'type': 'message',
            'username': username,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        for member in chat_rooms[room_id]:
            if member in chat_connections:
                await chat_connections[member].send(json.dumps(message))

async def handle_voip_message(websocket, username, data):
    if data['type'] == 'call':
        target = data['target']
        if target in voip_connections:
            # Check if target accepts calls
            conn = create_db_connection()
            try:
                c = conn.cursor()
                c.execute('SELECT accept_calls FROM users WHERE username = ?', (target,))
                result = c.fetchone()
                if not result or not result[0]:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'User is not accepting calls'
                    }))
                    return
            finally:
                conn.close()

            # Check if user is blocked
            conn = create_db_connection()
            try:
                c = conn.cursor()
                c.execute('''
                    SELECT COUNT(*) FROM blocked_users b
                    JOIN users u1 ON b.blocker_id = u1.id
                    JOIN users u2 ON b.blocked_id = u2.id
                    WHERE (u1.username = ? AND u2.username = ?) OR
                          (u1.username = ? AND u2.username = ?)
                ''', (username, target, target, username))
                if c.fetchone()[0] > 0:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Call blocked'
                    }))
                    return
            finally:
                conn.close()

            # Create call log
            conn = create_db_connection()
            try:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO call_logs (caller_id, receiver_id, status)
                    SELECT u1.id, u2.id, 'pending'
                    FROM users u1, users u2
                    WHERE u1.username = ? AND u2.username = ?
                ''', (username, target))
                call_id = c.lastrowid
                conn.commit()
            finally:
                conn.close()

            await voip_connections[target].send(json.dumps({
                'type': 'incoming_call',
                'from': username,
                'call_id': call_id
            }))

    elif data['type'] == 'accept_call':
        caller = data['caller']
        call_id = data['call_id']
        if caller in voip_connections:
            # Update call log
            conn = create_db_connection()
            try:
                c = conn.cursor()
                c.execute('UPDATE call_logs SET status = "accepted" WHERE id = ?', (call_id,))
                conn.commit()
            finally:
                conn.close()

            await voip_connections[caller].send(json.dumps({
                'type': 'call_accepted',
                'by': username,
                'call_id': call_id
            }))

    elif data['type'] == 'reject_call':
        caller = data['caller']
        call_id = data['call_id']
        if caller in voip_connections:
            # Update call log
            conn = create_db_connection()
            try:
                c = conn.cursor()
                c.execute('UPDATE call_logs SET status = "rejected" WHERE id = ?', (call_id,))
                conn.commit()
            finally:
                conn.close()

            await voip_connections[caller].send(json.dumps({
                'type': 'call_rejected',
                'by': username
            }))

    elif data['type'] == 'end_call':
        call_id = data['call_id']
        duration = data.get('duration', 0)
        # Update call log
        conn = create_db_connection()
        try:
            c = conn.cursor()
            c.execute('''
                UPDATE call_logs 
                SET status = "ended",
                    ended_at = CURRENT_TIMESTAMP,
                    duration = ?
                WHERE id = ?
            ''', (duration, call_id))
            conn.commit()
        finally:
            conn.close()

    elif data['type'] in ['ice_candidate', 'offer', 'answer']:
        target = data['target']
        if target in voip_connections:
            await voip_connections[target].send(json.dumps(data))

async def websocket_handler(websocket, path):
    try:
        # Wait for initial connection message
        message = await websocket.recv()
        data = json.loads(message)
        
        if not data.get('username'):
            return

        username = data['username']
        connection_type = data.get('type', 'chat')

        if connection_type == 'chat':
            chat_connections[username] = websocket
            try:
                async for message in websocket:
                    data = json.loads(message)
                    await handle_chat_message(websocket, username, data)
            finally:
                if username in chat_connections:
                    del chat_connections[username]
                for room in chat_rooms.values():
                    room.discard(username)

        elif connection_type == 'voip':
            voip_connections[username] = websocket
            try:
                async for message in websocket:
                    data = json.loads(message)
                    await handle_voip_message(websocket, username, data)
            finally:
                if username in voip_connections:
                    del voip_connections[username]

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"Error: {e}")

async def main():
    async with websockets.serve(websocket_handler, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())