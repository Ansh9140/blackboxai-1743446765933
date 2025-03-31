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
                // Get the current hostname and port
                const wsUrl = `ws://${window.location.hostname}:8765`;
                console.log('WebSocket URL:', wsUrl);
                this.ws = new WebSocket(wsUrl);

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

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}