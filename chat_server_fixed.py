import asyncio
import websockets
import json
from collections import defaultdict
import sqlite3
from datetime import datetime

# Store active connections and chat rooms
connections = {}
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

async def get_room_id(room_name):
    conn = create_db_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT id FROM chat_rooms WHERE name = ?', (room_name,))
        result = c.fetchone()
        if result:
            return result[0]
        # Create room if it doesn't exist
        c.execute('INSERT INTO chat_rooms (name) VALUES (?)', (room_name,))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

async def broadcast_to_room(room_id, message, exclude=None):
    for username in chat_rooms[room_id]:
        if username != exclude and username in connections:
            try:
                await connections[username].send(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to {username}: {e}")

async def handle_chat_message(websocket, username, data):
    try:
        if data['type'] == 'join_room':
            room_name = data['room']
            room_id = await get_room_id(room_name)
            chat_rooms[room_id].add(username)
            print(f"User {username} joined room {room_name} (ID: {room_id})")
            
            # Send room history
            history = await get_chat_history(room_id)
            await websocket.send(json.dumps({
                'type': 'history',
                'messages': history
            }))
            
            # Notify others
            await broadcast_to_room(room_id, {
                'type': 'system',
                'content': f'{username} joined the room'
            }, username)

        elif data['type'] == 'leave_room':
            room_name = data['room']
            room_id = await get_room_id(room_name)
            chat_rooms[room_id].discard(username)
            print(f"User {username} left room {room_name} (ID: {room_id})")
            
            # Notify others
            await broadcast_to_room(room_id, {
                'type': 'system',
                'content': f'{username} left the room'
            })

        elif data['type'] == 'message':
            room_name = data['room']
            room_id = await get_room_id(room_name)
            content = data['content']
            print(f"Message from {username} in room {room_name}: {content}")
            
            # Save to database
            await save_chat_message(room_id, username, content)
            
            # Broadcast to room members
            message = {
                'type': 'message',
                'username': username,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            await broadcast_to_room(room_id, message)

    except Exception as e:
        print(f"Error handling message: {e}")
        try:
            await websocket.send(json.dumps({
                'type': 'error',
                'content': str(e)
            }))
        except:
            print("Could not send error message to client")

async def chat_server(websocket, path):
    username = None
    try:
        # Wait for initial connection message
        message = await websocket.recv()
        data = json.loads(message)
        
        username = data.get('username')
        if not username:
            print("No username provided")
            return

        print(f"New connection from user: {username}")
        connections[username] = websocket
        
        # Send connection confirmation
        await websocket.send(json.dumps({
            'type': 'system',
            'content': 'Connected to chat server'
        }))
        
        try:
            async for message in websocket:
                data = json.loads(message)
                await handle_chat_message(websocket, username, data)
        finally:
            if username in connections:
                del connections[username]
            for room_id in list(chat_rooms.keys()):
                if username in chat_rooms[room_id]:
                    chat_rooms[room_id].discard(username)
                    # Notify others that user has left
                    await broadcast_to_room(room_id, {
                        'type': 'system',
                        'content': f'{username} disconnected'
                    })
            print(f"User disconnected: {username}")

    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed{' for ' + username if username else ''}")
    except Exception as e:
        print(f"Error in chat server: {e}")
    finally:
        if username and username in connections:
            del connections[username]
        for room in chat_rooms.values():
            if username in room:
                room.discard(username)

async def main():
    print("Chat server starting on port 8765...")
    async with websockets.serve(chat_server, "localhost", 8765, ping_interval=20, ping_timeout=60):
        print("Chat server running.")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Chat server stopped.")
    except Exception as e:
        print(f"Fatal error: {e}")