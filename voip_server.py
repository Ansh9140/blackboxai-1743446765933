import asyncio
import websockets
import json
from collections import defaultdict

# Store active connections and their rooms
connections = {}
rooms = defaultdict(set)

async def register(websocket, username):
    connections[username] = websocket

async def unregister(username):
    if username in connections:
        # Remove from all rooms
        for room in rooms.values():
            room.discard(username)
        del connections[username]

async def handle_join_call(username, target):
    # Create a unique room ID for the call
    room_id = f"call_{min(username, target)}_{max(username, target)}"
    rooms[room_id].add(username)
    
    # If target is online, notify them
    if target in connections:
        await connections[target].send(json.dumps({
            'type': 'incoming_call',
            'from': username,
            'room': room_id
        }))
        return True
    return False

async def handle_call_accepted(username, caller, room_id):
    rooms[room_id].add(username)
    if caller in connections:
        await connections[caller].send(json.dumps({
            'type': 'call_accepted',
            'by': username,
            'room': room_id
        }))

async def handle_call_rejected(username, caller):
    if caller in connections:
        await connections[caller].send(json.dumps({
            'type': 'call_rejected',
            'by': username
        }))

async def handle_ice_candidate(username, target, candidate, room_id):
    if target in connections and target in rooms[room_id]:
        await connections[target].send(json.dumps({
            'type': 'ice_candidate',
            'from': username,
            'candidate': candidate
        }))

async def handle_offer(username, target, offer, room_id):
    if target in connections and target in rooms[room_id]:
        await connections[target].send(json.dumps({
            'type': 'offer',
            'from': username,
            'offer': offer
        }))

async def handle_answer(username, target, answer, room_id):
    if target in connections and target in rooms[room_id]:
        await connections[target].send(json.dumps({
            'type': 'answer',
            'from': username,
            'answer': answer
        }))

async def handle_hangup(username, room_id):
    if room_id in rooms:
        # Notify all users in the room
        for user in rooms[room_id].copy():
            if user != username and user in connections:
                await connections[user].send(json.dumps({
                    'type': 'hangup',
                    'from': username
                }))
        # Clear the room
        rooms[room_id].clear()

async def voip_server(websocket, path):
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
                    
                    if data['type'] == 'call':
                        success = await handle_join_call(username, data['target'])
                        if not success:
                            await websocket.send(json.dumps({
                                'type': 'error',
                                'message': 'User is offline'
                            }))
                    
                    elif data['type'] == 'accept_call':
                        await handle_call_accepted(username, data['caller'], data['room'])
                    
                    elif data['type'] == 'reject_call':
                        await handle_call_rejected(username, data['caller'])
                    
                    elif data['type'] == 'ice_candidate':
                        await handle_ice_candidate(username, data['target'], data['candidate'], data['room'])
                    
                    elif data['type'] == 'offer':
                        await handle_offer(username, data['target'], data['offer'], data['room'])
                    
                    elif data['type'] == 'answer':
                        await handle_answer(username, data['target'], data['answer'], data['room'])
                    
                    elif data['type'] == 'hangup':
                        await handle_hangup(username, data['room'])
            
            finally:
                await unregister(username)
    
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"Error: {e}")

async def main():
    async with websockets.serve(voip_server, "localhost", 8766):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())