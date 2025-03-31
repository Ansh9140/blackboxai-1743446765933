async function checkSession() {
    try {
        const response = await fetch('/api/check-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            window.location.href = 'login.html';
            return null;
        }

        const data = await response.json();
        if (!data.valid || !data.username) {
            window.location.href = 'login.html';
            return null;
        }

        return data.username;
    } catch (error) {
        console.error('Session check failed:', error);
        window.location.href = 'login.html';
        return null;
    }
}

async function logout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            credentials: 'same-origin'
        });
        window.location.href = 'login.html';
    } catch (error) {
        console.error('Logout failed:', error);
        window.location.href = 'login.html';
    }
}

// Check session when page loads
document.addEventListener('DOMContentLoaded', async function() {
    const username = await checkSession();
    if (username) {
        // Update all elements with class 'current-username'
        document.querySelectorAll('.current-username').forEach(el => {
            el.textContent = username;
        });
    }
});