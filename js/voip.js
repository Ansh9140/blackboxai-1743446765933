class VoIPClient {
    constructor(username) {
        this.username = username;
        this.ws = null;
        this.pc = null;
        this.currentRoom = null;
        this.localStream = null;
        this.remoteStream = null;
        this.onCallCallback = null;
        this.onHangupCallback = null;
        this.onStreamCallback = null;
    }

    async connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket('ws://localhost:8766');

            this.ws.onopen = () => {
                this.ws.send(JSON.stringify({
                    type: 'connect',
                    username: this.username
                }));
                resolve();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            this.ws.onmessage = async (event) => {
                const data = JSON.parse(event.data);
                await this.handleSignalingMessage(data);
            };

            this.ws.onclose = () => {
                this.hangup();
                console.log('WebSocket connection closed');
            };
        });
    }

    async initializeCall() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            if (this.onStreamCallback) {
                this.onStreamCallback('local', this.localStream);
            }
        } catch (error) {
            console.error('Error accessing microphone:', error);
            throw error;
        }
    }

    async startCall(target) {
        await this.initializeCall();
        this.ws.send(JSON.stringify({
            type: 'call',
            target: target
        }));
    }

    async acceptCall(caller, roomId) {
        await this.initializeCall();
        this.currentRoom = roomId;
        this.ws.send(JSON.stringify({
            type: 'accept_call',
            caller: caller,
            room: roomId
        }));
        await this.createPeerConnection(true);
    }

    rejectCall(caller) {
        this.ws.send(JSON.stringify({
            type: 'reject_call',
            caller: caller
        }));
    }

    async createPeerConnection(isReceiver = false) {
        const configuration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' }
            ]
        };

        this.pc = new RTCPeerConnection(configuration);

        this.pc.onicecandidate = (event) => {
            if (event.candidate) {
                this.ws.send(JSON.stringify({
                    type: 'ice_candidate',
                    target: isReceiver ? this.caller : this.target,
                    candidate: event.candidate,
                    room: this.currentRoom
                }));
            }
        };

        this.pc.ontrack = (event) => {
            this.remoteStream = event.streams[0];
            if (this.onStreamCallback) {
                this.onStreamCallback('remote', this.remoteStream);
            }
        };

        this.localStream.getTracks().forEach(track => {
            this.pc.addTrack(track, this.localStream);
        });

        if (!isReceiver) {
            const offer = await this.pc.createOffer();
            await this.pc.setLocalDescription(offer);
            this.ws.send(JSON.stringify({
                type: 'offer',
                target: this.target,
                offer: offer,
                room: this.currentRoom
            }));
        }
    }

    async handleSignalingMessage(data) {
        switch(data.type) {
            case 'incoming_call':
                this.caller = data.from;
                this.currentRoom = data.room;
                if (this.onCallCallback) {
                    this.onCallCallback(data.from);
                }
                break;

            case 'call_accepted':
                this.currentRoom = data.room;
                await this.createPeerConnection();
                break;

            case 'call_rejected':
                if (this.onHangupCallback) {
                    this.onHangupCallback('rejected');
                }
                this.cleanup();
                break;

            case 'ice_candidate':
                if (this.pc) {
                    await this.pc.addIceCandidate(new RTCIceCandidate(data.candidate));
                }
                break;

            case 'offer':
                await this.pc.setRemoteDescription(new RTCSessionDescription(data.offer));
                const answer = await this.pc.createAnswer();
                await this.pc.setLocalDescription(answer);
                this.ws.send(JSON.stringify({
                    type: 'answer',
                    target: data.from,
                    answer: answer,
                    room: this.currentRoom
                }));
                break;

            case 'answer':
                await this.pc.setRemoteDescription(new RTCSessionDescription(data.answer));
                break;

            case 'hangup':
                if (this.onHangupCallback) {
                    this.onHangupCallback('remote');
                }
                this.cleanup();
                break;

            case 'error':
                console.error('Signaling error:', data.message);
                break;
        }
    }

    hangup() {
        if (this.currentRoom) {
            this.ws.send(JSON.stringify({
                type: 'hangup',
                room: this.currentRoom
            }));
        }
        this.cleanup();
    }

    cleanup() {
        if (this.pc) {
            this.pc.close();
            this.pc = null;
        }
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        this.remoteStream = null;
        this.currentRoom = null;
        this.caller = null;
        this.target = null;
    }

    onIncomingCall(callback) {
        this.onCallCallback = callback;
    }

    onCallEnded(callback) {
        this.onHangupCallback = callback;
    }

    onStream(callback) {
        this.onStreamCallback = callback;
    }

    disconnect() {
        this.hangup();
        if (this.ws) {
            this.ws.close();
        }
    }
}