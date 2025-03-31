import asyncio
import websockets
import json
from collections import defaultdict

# Store active connections
connections = {}
# Store chat rooms and their members
chat_rooms = defaultdict(set)
# Store messages for each room (keep last 50 messages)
room_messages = defaultdict(lambda: [])
MAX_MESSAGES = 50

async def register(websocket, username):
    connections[username] = websocket

async def unregister(username):
    if username in connections:
        del connections[username]
        # Remove user from all rooms
        for room in chat_rooms:
            chat_rooms[room].discard(username)

async def handle_join_room(username, room_id):
    chat_rooms[room_id].add(username)
    # Send last 50 messages to the user
    if username in connections:
        await connections[username].send(json.dumps({
            'type': 'history',
            'room': room_id,
            'messages': room_messages[room_id][-50:]
        }))
        # Notify others in the room
        await broadcast_to_room(room_id, {
            'type': 'system',
            'content': f'{username} joined the room'
        }, exclude=username)

async def handle_leave_room(username, room_id):
    chat_rooms[room_id].discard(username)
    await broadcast_to_room(room_id, {
        'type': 'system',
        'content': f'{username} left the room'
    })

async def broadcast_to_room(room_id, message, exclude=None):
    if room_id in chat_rooms:
        for username in chat_rooms[room_id]:
            if username != exclude and username in connections:
                await connections[username].send(json.dumps(message))

async def handle_message(username, room_id, content):
    message = {
        'type': 'message',
        'room': room_id,
        'username': username,
        'content': content,
        'timestamp': asyncio.get_event_loop().time()
    }
    room_messages[room_id].append(message)
    if len(room_messages[room_id]) > MAX_MESSAGES:
        room_messages[room_id] = room_messages[room_id][-MAX_MESSAGES:]
    await broadcast_to_room(room_id, message)

async def chat_server(websocket, path):
    try:
        # Wait for the initial connection message with username
        message = await websocket.recv()
        data = json.loads(message)
        
        if data['type'] == 'connect':
            username = data['username']
            await register(websocket, username)
            
            try:
                async for message in websocket:
                    data = json.loads(message)
                    
                    if data['type'] == 'join':
                        await handle_join_room(username, data['room'])
                    elif data['type'] == 'leave':
                        await handle_leave_room(username, data['room'])
                    elif data['type'] == 'message':
                        await handle_message(username, data['room'], data['content'])
            finally:
                await unregister(username)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"Error: {e}")

async def main():
    async with websockets.serve(chat_server, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())