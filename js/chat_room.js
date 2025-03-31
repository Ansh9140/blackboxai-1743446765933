// Add room management methods to ChatClient
ChatClient.prototype.joinRoom = async function(roomName) {
    if (!this.isConnected()) {
        throw new Error('Not connected to chat server');
    }
    
    console.log('Joining room:', roomName);
    if (this.currentRoom) {
        await this.leaveRoom();
    }
    this.currentRoom = roomName;
    this.ws.send(JSON.stringify({
        type: 'join_room',
        room: roomName
    }));
};

ChatClient.prototype.leaveRoom = async function() {
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
};

ChatClient.prototype.sendMessage = function(content) {
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
};

ChatClient.prototype.onMessage = function(callback) {
    this.onMessageCallback = callback;
};

ChatClient.prototype.onSystemMessage = function(callback) {
    this.onSystemMessageCallback = callback;
};

ChatClient.prototype.onHistory = function(callback) {
    this.onHistoryCallback = callback;
};

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
