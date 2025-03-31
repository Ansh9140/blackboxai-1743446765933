class ChatClient {
    constructor(username) {
        this.username = username;
        this.ws = null;
        this.currentRoom = null;
        this.onMessageCallback = null;
        this.onSystemMessageCallback = null;
        this.onHistoryCallback = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.isReconnecting = false;
    }

    async connect() {
        return new Promise((resolve, reject) => {
            try {
                console.log('Connecting to chat server...');
                this.ws = new WebSocket('ws://localhost:8765');

                this.ws.onopen = () => {
                    console.log('Connected to chat server');
                    this.reconnectAttempts = 0;
                    this.isReconnecting = false;
                    
                    // Send initial connection message with username
                    this.ws.send(JSON.stringify({
                        username: this.username
                    }));

                    if (this.onSystemMessageCallback) {
                        this.onSystemMessageCallback({
                            content: 'Connected to chat server'
                        });
                    }
                    resolve();
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    if (this.onSystemMessageCallback) {
                        this.onSystemMessageCallback({
                            content: 'Connection error. Please try again.'
                        });
                    }
                    reject(error);
                };

                this.ws.onclose = () => {
                    console.log('WebSocket connection closed');
                    if (!this.isReconnecting) {
                        this.handleDisconnect();
                    }
                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        console.log('Received message:', data);
                        this.handleMessage(data);
                    } catch (error) {
                        console.error('Error handling message:', error);
                    }
                };
            } catch (error) {
                console.error('Connection error:', error);
                reject(error);
            }
        });
    }

    handleMessage(data) {
        switch(data.type) {
            case 'message':
                if (this.onMessageCallback) {
                    this.onMessageCallback(data);
                }
                break;
            case 'system':
                if (this.onSystemMessageCallback) {
                    this.onSystemMessageCallback(data);
                }
                break;
            case 'history':
                if (this.onHistoryCallback) {
                    this.onHistoryCallback(data.messages);
                }
                break;
            case 'error':
                console.error('Server error:', data.content);
                if (this.onSystemMessageCallback) {
                    this.onSystemMessageCallback({
                        content: `Error: ${data.content}`
                    });
                }
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    async handleDisconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.isReconnecting = true;
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            if (this.onSystemMessageCallback) {
                this.onSystemMessageCallback({
                    content: `Connection lost. Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
                });
            }

            await new Promise(resolve => setTimeout(resolve, 2000));
            
            try {
                await this.connect();
                if (this.currentRoom) {
                    await this.joinRoom(this.currentRoom);
                }
            } catch (error) {
                console.error('Reconnection failed:', error);
                this.isReconnecting = false;
            }
        } else {
            console.error('Max reconnection attempts reached');
            this.isReconnecting = false;
            if (this.onSystemMessageCallback) {
                this.onSystemMessageCallback({
                    content: 'Connection lost. Please refresh the page.'
                });
            }
        }
    }

    async joinRoom(roomId) {
        if (!this.isConnected()) {
            throw new Error('Not connected to chat server');
        }
        
        console.log('Joining room:', roomId);
        if (this.currentRoom) {
            await this.leaveRoom();
        }
        this.currentRoom = roomId;
        this.ws.send(JSON.stringify({
            type: 'join_room',
            room: roomId
        }));
    }

    async leaveRoom() {
        if (!this.isConnected()) {
            throw new Error('Not connected to chat server');
        }
        
        if (this.currentRoom) {
            console.log('Leaving room:', this.currentRoom);
            this.ws.send(JSON.stringify({
                type: 'leave_room',
                room: this.currentRoom
            }));
            this.currentRoom = null;
        }
    }

    sendMessage(content) {
        if (!this.isConnected()) {
            throw new Error('Not connected to chat server');
        }
        
        if (!this.currentRoom) {
            throw new Error('Not in a room');
        }
        
        if (!content.trim()) {
            return;
        }
        
        console.log('Sending message:', content);
        this.ws.send(JSON.stringify({
            type: 'message',
            room: this.currentRoom,
            content: content
        }));
    }

    onMessage(callback) {
        this.onMessageCallback = callback;
    }

    onSystemMessage(callback) {
        this.onSystemMessageCallback = callback;
    }

    onHistory(callback) {
        this.onHistoryCallback = callback;
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Helper function to format timestamps
function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Helper function to create message elements
function createMessageElement(message, isSystem = false) {
    const div = document.createElement('div');
    
    if (isSystem) {
        div.className = 'text-center text-gray-400 text-sm py-2';
        div.textContent = message.content;
    } else {
        const isSelf = message.username === window.chatClient?.username;
        div.className = `flex ${isSelf ? 'justify-end' : 'justify-start'} mb-4`;
        div.innerHTML = `
            <div class="${isSelf ? 'bg-purple-600' : 'bg-gray-700'} rounded-lg px-4 py-2 max-w-[70%]">
                ${!isSelf ? `<div class="text-sm text-purple-400">${message.username}</div>` : ''}
                <div class="text-white break-words">${message.content}</div>
                <div class="text-xs text-gray-400 text-right">${formatTime(message.timestamp)}</div>
            </div>
        `;
    }
    
    return div;
}