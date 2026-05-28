// Centralized API helper for RAAHAT frontend
const API_BASE = window.location.origin; // same origin by default

async function apiFetch(path, { method = 'GET', body = null, timeout = 15000 } = {}) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    const opts = { method, headers: { 'Accept': 'application/json' }, signal: controller.signal };
    if (body) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
    }
    try {
        const res = await fetch(API_BASE + path, opts);
        clearTimeout(id);
        const text = await res.text();
        let json = null;
        try { json = text ? JSON.parse(text) : null; } catch (e) { json = null; }
        if (!res.ok) {
            const msg = (json && (json.detail || json.error || json.message)) || res.statusText || 'Request failed';
            const err = new Error(msg);
            err.status = res.status;
            err.body = json;
            throw err;
        }
        return json;
    } catch (e) {
        if (e.name === 'AbortError') throw new Error('Request timed out');
        throw e;
    }
}

// Session helpers
const SESSION_KEY = 'raahat_user';
function saveSession(user) { localStorage.setItem(SESSION_KEY, JSON.stringify(user)); }
function loadSession() { try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch (e) { return null; } }
function clearSession() { localStorage.removeItem(SESSION_KEY); }

// Page wiring
document.addEventListener('DOMContentLoaded', () => {
    // Login form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = (document.getElementById('email') || {}).value?.trim();
            const password = (document.getElementById('password') || {}).value?.trim();
            if (!email || !password) { alert('Please enter email and password'); return; }
            const submitBtn = loginForm.querySelector('button[type=submit]');
            submitBtn.disabled = true;
            const original = submitBtn.innerHTML;
            submitBtn.innerHTML = 'Signing in...';
            try {
                const res = await apiFetch('/api/login', { method: 'POST', body: { username: email, password } });
                if (res && res.user_id) {
                    saveSession({ user_id: res.user_id, username: res.username });
                    window.location.href = '/dashboard';
                } else {
                    alert('Login succeeded but no session returned.');
                    window.location.href = '/dashboard';
                }
            } catch (err) {
                console.error('Login error', err);
                alert(err.message || 'Login failed');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = original;
            }
        });
    }

    // Chat page wiring
    const messagesEl = document.getElementById('messages');
    const inputEl = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    if (messagesEl && inputEl && sendBtn) {
        const renderMessage = (role, text) => {
            const wrapper = document.createElement('div');
            wrapper.className = role === 'user' ? 'flex justify-end' : 'flex justify-start';
            let inner = document.createElement('div');
            inner.className = role === 'user' ? 'max-w-[70%] bg-sage-deep text-white p-stack-md rounded-2xl rounded-br-sm shadow' : 'flex gap-3 max-w-[80%]';
            if (role === 'ai') {
                // ai structure
                const avatar = document.createElement('div');
                avatar.className = 'w-8 h-8 rounded-full bg-lavender-soft flex-shrink-0 flex items-center justify-center text-lavender-dark mt-1';
                avatar.innerHTML = '<span class="material-symbols-outlined text-[16px]">psychiatry</span>';
                const box = document.createElement('div');
                box.className = 'bg-lavender-soft/40 p-stack-md rounded-2xl rounded-bl-sm shadow-sm border border-lavender-soft/50';
                const p = document.createElement('p');
                p.className = 'font-body-md text-body-md text-on-surface';
                p.textContent = text;
                box.appendChild(p);
                inner.appendChild(avatar);
                inner.appendChild(box);
            } else {
                const p = document.createElement('div');
                p.className = 'max-w-[70%] bg-sage-deep text-white p-stack-md rounded-2xl rounded-br-sm shadow-[0_4px_15px_rgba(45,90,84,0.15)]';
                p.textContent = text;
                inner = p;
            }
            wrapper.appendChild(inner);
            messagesEl.appendChild(wrapper);
            // auto-scroll
            messagesEl.scrollTop = messagesEl.scrollHeight;
        };

        const session = loadSession();
        if (!session || !session.user_id) {
            // redirect to login
            console.warn('No active session; redirecting to login');
            window.location.href = '/login';
            return;
        }

        // load history
        (async () => {
            try {
                const res = await apiFetch('/api/history?user_id=' + encodeURIComponent(session.user_id));
                if (res && Array.isArray(res.history)) {
                    messagesEl.innerHTML = ''; // clear sample content
                    res.history.forEach(m => {
                        renderMessage(m.role === 'ai' ? 'ai' : 'user', m.content || m.message || '');
                    });
                }
            } catch (err) {
                console.error('History load failed', err);
                const errNode = document.createElement('div');
                errNode.className = 'p-3 text-center text-error';
                errNode.textContent = 'Could not load history. You can still chat.';
                messagesEl.prepend(errNode);
            }
        })();

        let sending = false;
        const sendMessage = async () => {
            if (sending) return;
            let text = inputEl.value || '';
            text = text.trim();
            if (!text) return;
            if (text.length > 2000) { alert('Message too long'); return; }
            // optimistic render
            renderMessage('user', text);
            inputEl.value = '';
            sending = true;
            sendBtn.disabled = true;
            try {
                const res = await apiFetch('/api/chat', { method: 'POST', body: { user_id: session.user_id, message: text }, timeout: 60000 });
                if (res && res.response) {
                    renderMessage('ai', res.response);
                } else {
                    renderMessage('ai', 'Sorry, I could not get a response right now.');
                }
            } catch (err) {
                console.error('Chat error', err);
                const errBox = document.createElement('div');
                errBox.className = 'p-2 text-error text-center';
                errBox.textContent = 'Message failed to send. Please try again.';
                messagesEl.appendChild(errBox);
            } finally {
                sending = false;
                sendBtn.disabled = false;
            }
        };

        sendBtn.addEventListener('click', sendMessage);
        inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); sendMessage(); } });
    }
});
