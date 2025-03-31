import asyncio
import websockets
import json
import sqlite3
from datetime import datetime

# Store active connections
connections = {}

def create_db_connection():
    return sqlite3.connect('lqr_group.db')

async def handle_voip_message(websocket, username, data):
    try:
        if data['type'] == 'call':
            target = data['target']
            if target in connections:
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

                await connections[target].send(json.dumps({
                    'type': 'incoming_call',
                    'from': username,
                    'call_id': call_id
                }))
            else:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'User is offline'
                }))

        elif data['type'] == 'accept_call':
            caller = data['caller']
            call_id = data['call_id']
            if caller in connections:
                # Update call log
                conn = create_db_connection()
                try:
                    c = conn.cursor()
                    c.execute('UPDATE call_logs SET status = "accepted" WHERE id = ?', (call_id,))
                    conn.commit()
                finally:
                    conn.close()

                await connections[caller].send(json.dumps({
                    'type': 'call_accepted',
                    'by': username,
                    'call_id': call_id
                }))

        elif data['type'] == 'reject_call':
            caller = data['caller']
            call_id = data['call_id']
            if caller in connections:
                # Update call log
                conn = create_db_connection()
                try:
                    c = conn.cursor()
                    c.execute('UPDATE call_logs SET status = "rejected" WHERE id = ?', (call_id,))
                    conn.commit()
                finally:
                    conn.close()

                await connections[caller].send(json.dumps({
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
            if target in connections:
                await connections[target].send(json.dumps(data))

    except Exception as e:
        print(f"Error handling VOIP message: {e}")
        try:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
        except:
            print("Could not send error message to client")

async def voip_server(websocket, path):
    username = None
    try:
        # Wait for initial connection message
        message = await websocket.recv()
        data = json.loads(message)
        
        username = data.get('username')
        if not username:
            print("No username provided")
            return

        print(f"New VOIP connection from user: {username}")
        connections[username] = websocket
        
        # Send connection confirmation
        await websocket.send(json.dumps({
            'type': 'system',
            'message': 'Connected to VOIP server'
        }))
        
        try:
            async for message in websocket:
                data = json.loads(message)
                await handle_voip_message(websocket, username, data)
        finally:
            if username in connections:
                del connections[username]
            print(f"VOIP user disconnected: {username}")

    except websockets.exceptions.ConnectionClosed:
        print(f"VOIP connection closed{' for ' + username if username else ''}")
    except Exception as e:
        print(f"Error in VOIP server: {e}")
    finally:
        if username and username in connections:
            del connections[username]

async def main():
    print("VOIP server starting on port 8766...")
    async with websockets.serve(voip_server, "localhost", 8766, ping_interval=20, ping_timeout=60):
        print("VOIP server running.")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("VOIP server stopped.")
    except Exception as e:
        print(f"Fatal error: {e}")