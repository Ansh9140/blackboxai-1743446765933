import asyncio
import websockets
import json

# Store active connections and chat rooms
connections = {}
chat_rooms = {
    'General': set(),
    'Support': set(),
    'Off-Topic': set()
}

async def broadcast_to_room(room_name, message, exclude=None):
    for username in chat_rooms[room_name]:
        if username != exclude and username in connections:
            try:
                await connections[username].send(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to {username}: {e}")

async def handle_chat_message(websocket, username, data):
    try:
        print(f"Handling message from {username}: {data}")
        if data['type'] == 'join_room':
            room_name = data['room']
            if room_name not in chat_rooms:
                raise ValueError(f"Invalid room: {room_name}")
                
            chat_rooms[room_name].add(username)
            print(f"User {username} joined room {room_name}")
            
            # Notify others
            await broadcast_to_room(room_name, {
                'type': 'system',
                'content': f'{username} joined the room'
            }, username)

        elif data['type'] == 'leave_room':
            room_name = data['room']
            if room_name not in chat_rooms:
                raise ValueError(f"Invalid room: {room_name}")
                
            chat_rooms[room_name].discard(username)
            print(f"User {username} left room {room_name}")
            
            # Notify others
            await broadcast_to_room(room_name, {
                'type': 'system',
                'content': f'{username} left the room'
            })

        elif data['type'] == 'message':
            room_name = data['room']
            if room_name not in chat_rooms:
                raise ValueError(f"Invalid room: {room_name}")
                
            content = data['content']
            print(f"Message from {username} in room {room_name}: {content}")
            
            # Broadcast to room members
            message = {
                'type': 'message',
                'username': username,
                'content': content,
                'timestamp': data.get('timestamp', '')
            }
            await broadcast_to_room(room_name, message)

    except Exception as e:
        print(f"Error handling message: {e}")
        try:
            await websocket.send(json.dumps({
                'type': 'error',
                'content': str(e)
            }))
        except:
            print("Could not send error message to client")

async def websocket_handler(websocket, path):
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
            for room_name, users in chat_rooms.items():
                if username in users:
                    users.discard(username)
                    # Notify others that user has left
                    await broadcast_to_room(room_name, {
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
        for users in chat_rooms.values():
            if username in users:
                users.discard(username)

async def main():
    port = 8764  # Changed port to avoid conflicts
    print(f"Chat server starting on port {port}...")
    
    async with websockets.serve(websocket_handler, "0.0.0.0", port):
        print(f"Chat server running on 0.0.0.0:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Chat server stopped.")
    except Exception as e:
        print(f"Fatal error: {e}")