from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
import database as db
import os

class RequestHandler(SimpleHTTPRequestHandler):
    def _send_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == '/api/users':
            users = db.get_all_users()
            self._send_response(200, {'users': users})
            return

        # Serve static files
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        try:
            # Handle session check first, before any JSON parsing
            if self.path == '/api/check-session':
                try:
                    cookies = {}
                    if 'Cookie' in self.headers:
                        for cookie in self.headers['Cookie'].split(';'):
                            try:
                                name, value = cookie.strip().split('=', 1)
                                cookies[name] = value
                            except ValueError:
                                continue

                    session_id = cookies.get('session_id')
                    if not session_id:
                        self._send_response(401, {'error': 'No session found'})
                        return

                    user = db.verify_session(session_id)
                    if user and user['status'] == 'approved':
                        self._send_response(200, {'valid': True, 'username': user['username']})
                    else:
                        self._send_response(401, {'error': 'Invalid session'})
                except Exception as e:
                    print(f"Session check error: {str(e)}")
                    self._send_response(401, {'error': 'Session check failed'})
                return

            # For other endpoints, parse JSON data
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode())
                except json.JSONDecodeError:
                    self._send_response(400, {'error': 'Invalid JSON data'})
                    return
            else:
                data = {}

            if self.path == '/api/login':
                username = data.get('username')
                password = data.get('password')

                if not all([username, password]):
                    self._send_response(400, {'error': 'Username and password are required'})
                    return

                user = db.verify_login(username, password)
                if user:
                    if user['status'] == 'approved':
                        session_id = db.create_session(user['id'])
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Set-Cookie', f'session_id={session_id}; Path=/; SameSite=Lax; HttpOnly')
                        self.end_headers()
                        self.wfile.write(json.dumps({'message': 'Login successful', 'username': user['username']}).encode())
                    elif user['status'] == 'pending':
                        self._send_response(403, {'error': 'Account pending approval'})
                    else:
                        self._send_response(403, {'error': 'Account rejected'})
                else:
                    self._send_response(401, {'error': 'Invalid credentials'})
                return

            elif self.path == '/api/logout':
                cookies = {}
                if 'Cookie' in self.headers:
                    for cookie in self.headers['Cookie'].split(';'):
                        try:
                            name, value = cookie.strip().split('=', 1)
                            cookies[name] = value
                        except ValueError:
                            continue

                session_id = cookies.get('session_id')
                if session_id:
                    db.delete_session(session_id)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Set-Cookie', 'session_id=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax; HttpOnly')
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'Logged out successfully'}).encode())
                return

            elif self.path == '/api/register':
                required_fields = ['username', 'email', 'password', 'mobile', 'telegram']
                if not all(field in data for field in required_fields):
                    self._send_response(400, {'error': 'All fields are required'})
                    return

                if db.register_user(**{field: data[field] for field in required_fields}):
                    self._send_response(200, {'message': 'Registration successful'})
                else:
                    self._send_response(400, {'error': 'Registration failed'})
                return

            elif self.path.startswith('/api/admin/'):
                action = self.path.split('/')[-1]
                if action == 'login':
                    username = data.get('username')
                    password = data.get('password')

                    if not all([username, password]):
                        self._send_response(400, {'error': 'Username and password are required'})
                        return

                    if db.verify_admin_login(username, password):
                        self._send_response(200, {'message': 'Login successful'})
                    else:
                        self._send_response(401, {'error': 'Invalid credentials'})
                    return
                else:
                    user_id = data.get('user_id')
                    if not user_id:
                        self._send_response(400, {'error': 'User ID is required'})
                        return

                    if action == 'approve':
                        if db.approve_user(user_id):
                            self._send_response(200, {'message': 'User approved'})
                        else:
                            self._send_response(400, {'error': 'Failed to approve user'})
                    elif action == 'reject':
                        if db.reject_user(user_id):
                            self._send_response(200, {'message': 'User rejected'})
                        else:
                            self._send_response(400, {'error': 'Failed to reject user'})
                    return

            self._send_response(404, {'error': 'Not found'})

        except Exception as e:
            print(f"Error processing request: {str(e)}")
            self._send_response(500, {'error': 'Internal server error'})

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f'Server running on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()