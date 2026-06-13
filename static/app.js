const API_BASE = window.location.origin;
const SESSION_KEY = 'raahat_user';
let supabaseClient = null;

async function apiFetch(path, { method = 'GET', body = null, timeout = 15000 } = {}) {
    let token = null;
    if (path !== '/api/config' && path !== '/api/login' && path !== '/api/signup') {
        try {
            if (typeof supabase !== 'undefined' && typeof supabase.createClient === 'function') {
                const client = await getSupabaseClient();
                const { data } = await client.auth.getSession();
                token = data?.session?.access_token;
            }
        } catch (err) {
            console.warn('Could not fetch token for API request:', err);
        }
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    const options = {
        method,
        headers: {
            Accept: 'application/json',
        },
        signal: controller.signal,
    };

    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    if (body !== null) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }

    return fetch(API_BASE + path, options)
        .then(async (response) => {
            clearTimeout(timeoutId);
            const rawText = await response.text();
            let parsed = null;
            if (rawText) {
                try {
                    parsed = JSON.parse(rawText);
                } catch (_error) {
                    parsed = null;
                }
            }
            if (!response.ok) {
                const message = (parsed && (parsed.detail || parsed.message || parsed.error)) || response.statusText || 'Request failed';
                const error = new Error(message);
                error.status = response.status;
                error.body = parsed;
                throw error;
            }
            return parsed;
        })
        .catch((error) => {
            if (error && error.name === 'AbortError') {
                throw new Error('Request timed out. Please try again.');
            }
            throw error;
        });
}

function saveSession(user) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(user));
    if (user && user.user_id) {
        localStorage.setItem('raahat_user_id', user.user_id);
    }
    // Log this to backend
    try {
        fetch('/api/debug-log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: 'saveSession called',
                data: {
                    user_id: user?.user_id,
                    username: user?.username,
                    has_access_token: !!user?.access_token,
                    access_token_len: user?.access_token ? user.access_token.length : 0,
                    access_token_prefix: user?.access_token ? user.access_token.substring(0, 15) : 'none'
                }
            })
        });
    } catch (e) {}
}

function loadSession() {
    try {
        const raw = localStorage.getItem(SESSION_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (_error) {
        return null;
    }
}

function clearSession() {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem('raahat_user_id');
}

async function completeOAuthLogin() {
    if (window.location.pathname !== '/login') {
        return false;
    }

    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const errorDescription = params.get('error_description') || params.get('error');

    if (!code && !errorDescription) {
        return false;
    }

    if (errorDescription) {
        showStatus(errorDescription, 'error');
        return true;
    }

    try {
        const client = await getSupabaseClient();
        const { data, error } = await client.auth.exchangeCodeForSession(code);
        if (error) throw error;

        // Retrieve session dynamically to ensure we get the fresh tokens
        const sessionRes = await client.auth.getSession();
        const session = sessionRes.data?.session || data?.session;

        // Log this session info to backend
        try {
            await fetch('/api/debug-log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: 'OAuth complete: session retrieved',
                    data: {
                        has_session: !!session,
                        access_token_len: session?.access_token ? session.access_token.length : 0,
                        access_token_prefix: session?.access_token ? session.access_token.substring(0, 15) : 'none',
                        user_id: session?.user?.id,
                        email: session?.user?.email,
                    }
                })
            });
        } catch (e) {}

        const email = session?.user?.email || session?.user?.user_metadata?.email;
        if (!email) {
            throw new Error('Google sign-in did not return an email address.');
        }

        const syncResult = await apiFetch('/api/sync-user', {
            method: 'POST',
            body: { email },
            timeout: 20000,
        });

        if (!syncResult?.user_id) {
            throw new Error('Unable to create a local session.');
        }

        saveSession({
            user_id: syncResult.user_id,
            username: syncResult.username || email,
            name: syncResult.name || '',
            access_token: session?.access_token,
            refresh_token: session?.refresh_token,
        });

        await new Promise(resolve => setTimeout(resolve, 1500));

        if (syncResult && (syncResult.is_new_signup || syncResult.needs_name)) {
            navigate('/onboarding');
        } else {
            navigate('/chat');
        }
        return true;
    } catch (error) {
        console.error('OAuth completion failed:', error);
        showStatus(error.message || 'Google sign-in failed.', 'error');
        return true;
    }
}

async function restoreSessionFromSupabase() {
    try {
        if (typeof supabase === 'undefined' || typeof supabase.createClient !== 'function') {
            return null;
        }

        const client = await getSupabaseClient();
        const { data, error } = await client.auth.getSession();
        const session = data?.session;
        const email = session?.user?.email;

        if (error || !email) {
            return null;
        }

        try {
            const syncResult = await apiFetch('/api/sync-user', {
                method: 'POST',
                body: { email },
                timeout: 20000,
            });

            if (syncResult?.user_id) {
                const sessionRecord = {
                    user_id: syncResult.user_id,
                    username: syncResult.username || email,
                    name: syncResult.name || '',
                    access_token: session?.access_token,
                    refresh_token: session?.refresh_token,
                };
                saveSession(sessionRecord);
                return sessionRecord;
            }
        } catch (syncError) {
            console.error('Supabase session sync failed:', syncError);
        }

        return null;
    } catch (syncError) {
        console.error('Supabase restore failed:', syncError);
    }

    return null;
}

function emailLooksValid(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || '').trim());
}

function setButtonLoading(button, loading, loadingText) {
    if (!button) return '';
    if (loading) {
        if (!button.dataset.originalHtml) {
            button.dataset.originalHtml = button.innerHTML;
        }
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        button.innerHTML = loadingText || 'Loading...';
        return button.dataset.originalHtml;
    }

    button.disabled = false;
    button.removeAttribute('aria-busy');
    if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
        delete button.dataset.originalHtml;
    }
    return '';
}

function showStatus(message, kind = 'info') {
    const statusEl = document.getElementById('auth-message');
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.classList.remove('hidden');
    statusEl.classList.toggle('border-error', kind === 'error');
    statusEl.classList.toggle('text-error', kind === 'error');
    statusEl.classList.toggle('border-outline-variant/30', kind !== 'error');
    statusEl.classList.toggle('text-sage-deep', kind !== 'error');
}

function hideStatus() {
    const statusEl = document.getElementById('auth-message');
    if (!statusEl) return;
    statusEl.classList.add('hidden');
    statusEl.textContent = '';
}

function navigate(path) {
    window.location.href = `${window.location.origin}${path}`;
}

function bindTextControl(selector, labelText, handler) {
    Array.from(document.querySelectorAll(selector)).forEach((element) => {
        const text = (element.textContent || '').trim().toLowerCase();
        if (labelText && text !== labelText.toLowerCase()) return;
        element.addEventListener('click', (event) => {
            event.preventDefault();
            handler(element);
        });
    });
}

function ensureAuthViews() {
    const loginForm = document.getElementById('login-form');
    if (!loginForm || document.getElementById('signup-form')) {
        return;
    }

    const card = loginForm.closest('.w-full.max-w-md');
    if (!card) return;

    const tabRow = document.createElement('div');
    tabRow.className = 'flex gap-2 mb-stack-md';
    tabRow.innerHTML = `
        <button type="button" id="show-login" class="flex-1 bg-sage-deep text-white rounded-full py-2 font-label-md text-label-md">Sign In</button>
        <button type="button" id="show-signup" class="flex-1 bg-surface-container-low text-sage-deep rounded-full py-2 font-label-md text-label-md">Sign Up</button>
    `;

    const statusEl = document.createElement('div');
    statusEl.id = 'auth-message';
    statusEl.className = 'hidden mb-stack-md rounded-lg border border-outline-variant/30 bg-surface-container-low px-4 py-3 font-label-md text-label-md text-sage-deep';

    loginForm.parentNode.insertBefore(tabRow, loginForm);
    loginForm.parentNode.insertBefore(statusEl, loginForm);

    const signupForm = document.createElement('form');
    signupForm.id = 'signup-form';
    signupForm.className = 'hidden space-y-stack-md mt-stack-lg';
    signupForm.action = '#';
    signupForm.method = 'POST';
    signupForm.innerHTML = `
        <div class="relative">
            <label class="block font-label-md text-label-md text-on-surface-variant mb-stack-sm" for="signup-email">Email Address</label>
            <div class="relative">
                <span class="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-outline-variant pointer-events-none">mail</span>
                <input class="w-full bg-surface-container-lowest border border-outline-variant rounded-lg pl-10 pr-4 py-3 font-body-md text-body-md text-on-surface focus:border-lavender-dark focus:ring-2 focus:ring-lavender-soft transition-all placeholder-outline-variant/70 shadow-sm" id="signup-email" name="signup-email" placeholder="you@example.com" required type="email" />
            </div>
        </div>
        <div class="relative">
            <label class="block font-label-md text-label-md text-on-surface-variant mb-stack-sm" for="signup-password">Password</label>
            <div class="relative">
                <span class="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-outline-variant pointer-events-none">lock</span>
                <input class="w-full bg-surface-container-lowest border border-outline-variant rounded-lg pl-10 pr-4 py-3 font-body-md text-body-md text-on-surface focus:border-lavender-dark focus:ring-2 focus:ring-lavender-soft transition-all placeholder-outline-variant/70 shadow-sm" id="signup-password" name="signup-password" placeholder="Create a strong password" required type="password" />
            </div>
        </div>
        <button id="signup-submit" class="w-full bg-lavender-dark text-white font-label-md text-label-md py-3 rounded-full hover:bg-sage-deep shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-0.5" type="submit">Create Account</button>
    `;

    loginForm.parentNode.insertBefore(signupForm, loginForm.nextSibling);

    const createAccountLink = Array.from(document.querySelectorAll('button, a')).find((element) => {
        return element.textContent && element.textContent.trim().toLowerCase().includes('create an account');
    });
    if (createAccountLink) {
        createAccountLink.setAttribute('type', 'button');
        createAccountLink.addEventListener('click', () => setAuthView('signup'));
    }

    const showLoginButton = document.getElementById('show-login');
    const showSignupButton = document.getElementById('show-signup');
    if (showLoginButton) showLoginButton.addEventListener('click', () => setAuthView('login'));
    if (showSignupButton) showSignupButton.addEventListener('click', () => setAuthView('signup'));

    setAuthView('login');
}

function setAuthView(view) {
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');
    const showLoginButton = document.getElementById('show-login');
    const showSignupButton = document.getElementById('show-signup');
    const viewMap = {
        login: loginForm,
        signup: signupForm,
    };

    Object.values(viewMap).forEach((form) => {
        if (form) form.classList.add('hidden');
    });

    const activeForm = viewMap[view];
    if (activeForm) activeForm.classList.remove('hidden');

    const buttons = [showLoginButton, showSignupButton];
    buttons.forEach((button) => {
        if (!button) return;
        button.classList.remove('bg-sage-deep', 'text-white');
        button.classList.add('bg-surface-container-low', 'text-sage-deep');
    });

    const activeButton = {
        login: showLoginButton,
        signup: showSignupButton,
    }[view];

    if (activeButton) {
        activeButton.classList.add('bg-sage-deep', 'text-white');
        activeButton.classList.remove('bg-surface-container-low', 'text-sage-deep');
    }
}

function bindLoginForm() {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        hideStatus();

        const email = document.getElementById('email')?.value?.trim() || '';
        const password = document.getElementById('password')?.value?.trim() || '';
        const submitButton = document.getElementById('login-submit') || loginForm.querySelector('button[type="submit"]');

        if (!emailLooksValid(email)) {
            showStatus('Enter a valid email address.', 'error');
            return;
        }
        if (!password) {
            showStatus('Enter your password.', 'error');
            return;
        }

        setButtonLoading(submitButton, true, 'Signing in...');
        try {
            const result = await apiFetch('/api/login', {
                method: 'POST',
                body: { username: email, password },
                timeout: 20000,
            });
            if (result && result.user_id) {
                saveSession({
                    user_id: result.user_id,
                    username: result.username || email,
                    name: result.name || '',
                    access_token: result.session?.access_token,
                    refresh_token: result.session?.refresh_token,
                });
                if (result && result.is_new_signup) {
                    navigate('/onboarding');
                } else {
                    navigate('/chat');
                }
                return;
            }
            throw new Error('Login succeeded but no session was returned.');
        } catch (error) {
            console.error('Login failed:', error);
            showStatus(error.message || 'Login failed.', 'error');
        } finally {
            setButtonLoading(submitButton, false);
        }
    });
}

function bindSignupForm() {
    const signupForm = document.getElementById('signup-form');
    if (!signupForm) return;

    signupForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        hideStatus();

        const email = document.getElementById('signup-email')?.value?.trim() || '';
        const password = document.getElementById('signup-password')?.value?.trim() || '';
        const submitButton = document.getElementById('signup-submit');

        if (!emailLooksValid(email)) {
            showStatus('Enter a valid email address.', 'error');
            return;
        }
        if (password.length < 8) {
            showStatus('Password must be at least 8 characters.', 'error');
            return;
        }

        setButtonLoading(submitButton, true, 'Creating account...');
        try {
            const result = await apiFetch('/api/signup', {
                method: 'POST',
                body: { username: email, password },
                timeout: 25000,
            });
            if (result && result.user_id) {
                saveSession({
                    user_id: result.user_id,
                    username: result.username || email,
                    name: result.name || '',
                    access_token: result.session?.access_token,
                    refresh_token: result.session?.refresh_token,
                });
                if (result && result.is_new_signup) {
                    navigate('/onboarding');
                } else {
                    navigate('/chat');
                }
                return;
            }
            showStatus('Account created. Please sign in.', 'info');
            setAuthView('login');
        } catch (error) {
            console.error('Signup failed:', error);
            showStatus(error.message || 'Signup failed.', 'error');
        } finally {
            setButtonLoading(submitButton, false);
        }
    });
}

let configPromise = null;

function fetchConfig() {
    if (!configPromise) {
        configPromise = apiFetch('/api/config')
            .then(config => {
                window.SUPABASE_URL = config.supabase_url;
                window.SUPABASE_KEY = config.supabase_key;
                return config;
            })
            .catch(err => {
                console.error('Failed to fetch Supabase config:', err);
                configPromise = null;
                throw err;
            });
    }
    return configPromise;
}

async function getSupabaseClient() {
    if (supabaseClient) {
        return supabaseClient;
    }

    if (!window.SUPABASE_URL || !window.SUPABASE_KEY) {
        const config = await fetchConfig();
        if (!config.supabase_url || !config.supabase_key) {
            throw new Error('Supabase configuration is missing from the server.');
        }
    }

    if (typeof supabase === 'undefined' || typeof supabase.createClient !== 'function') {
        throw new Error('Supabase client library is not loaded.');
    }

    supabaseClient = supabase.createClient(window.SUPABASE_URL, window.SUPABASE_KEY);

    try {
        const { data: activeSession } = await supabaseClient.auth.getSession();
        if (!activeSession?.session) {
            const localSession = loadSession();
            if (localSession && localSession.access_token) {
                await supabaseClient.auth.setSession({
                    access_token: localSession.access_token,
                    refresh_token: localSession.refresh_token || '',
                });
            }
        }
    } catch (err) {
        console.warn('Failed to sync session to Supabase Client:', err);
    }

    return supabaseClient;
}

function bindGoogleAuth() {
    const googleButton =
        document.getElementById('google-auth-btn') ||
        Array.from(document.querySelectorAll('button')).find(
            (button) =>
                (button.textContent || '').includes('Continue with Google')
        );

    const appleButton =
        Array.from(document.querySelectorAll('button')).find(
            (button) =>
                (button.textContent || '').includes('Continue with Apple')
        );

    if (appleButton) {
        appleButton.remove();
    }

    if (!googleButton) return;

    googleButton.addEventListener('click', async () => {
        hideStatus();

        setButtonLoading(
            googleButton,
            true,
            'Opening Google...'
        );

        try {
            const client = await getSupabaseClient();
            const { data, error } =
                await client.auth.signInWithOAuth({
                    provider: 'google',
                    options: {
                        // Keep Google on the existing callback URL; the callback forwards into the login flow.
                        redirectTo: `${window.location.origin}/auth/callback`
                    }
                });

            if (error) throw error;

        } catch (error) {
            console.error('Google auth failed:', error);

            showStatus(
                error.message || 'Google sign-in failed.',
                'error'
            );

            setButtonLoading(
                googleButton,
                false
            );
        }
    });
}

function bindLandingPage() {
    const session = loadSession();
    const heroStart = document.getElementById('landing-hero-start');
    const navStart = document.getElementById('landing-start-venting');
    const howItWorks = document.getElementById('landing-how-it-works');
    const privacyButton = document.getElementById('landing-privacy');
    const features = document.getElementById('landing-features');

    const goToPrimaryDestination = () => {
        navigate(session ? '/dashboard' : '/login');
    };

    [heroStart, navStart].forEach((button) => {
        if (!button) return;
        button.addEventListener('click', goToPrimaryDestination);
    });

    if (howItWorks && features) {
        howItWorks.addEventListener('click', () => {
            features.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    if (privacyButton) {
        privacyButton.addEventListener('click', () => {
            document.querySelector('footer')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    bindTextControl('button', 'Profile', () => {
        navigate(session ? '/dashboard' : '/login');
    });

    bindTextControl('a', 'Home', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    bindTextControl('a', 'Insights', () => {
        features?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    bindTextControl('a', 'Resources', () => {
        document.querySelector('footer')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    bindTextControl('a', 'Crisis', () => {
        privacyButton?.click();
    });
}

function createMessageBubble(role, text) {
    const wrapper = document.createElement('div');
    wrapper.className = role === 'user' ? 'flex justify-end fade-in-up' : 'flex justify-start fade-in-up';

    if (role === 'user') {
        const bubble = document.createElement('div');
        bubble.className = 'max-w-[70%] bg-sage-deep text-white p-stack-md rounded-2xl rounded-br-sm shadow-[0_4px_15px_rgba(45,90,84,0.15)]';
        const paragraph = document.createElement('p');
        paragraph.className = 'font-body-md text-body-md';
        paragraph.textContent = text;
        bubble.appendChild(paragraph);
        wrapper.appendChild(bubble);
        return wrapper;
    }

    const container = document.createElement('div');
    container.className = 'flex gap-3 max-w-[80%]';

    const avatar = document.createElement('div');
    avatar.className = 'w-8 h-8 rounded-full bg-lavender-soft flex-shrink-0 flex items-center justify-center text-lavender-dark mt-1';
    avatar.innerHTML = '<span class="material-symbols-outlined text-[16px]">psychiatry</span>';

    const bubble = document.createElement('div');
    bubble.className = 'bg-lavender-soft/40 p-stack-md rounded-2xl rounded-bl-sm shadow-sm border border-lavender-soft/50';
    const paragraph = document.createElement('p');
    paragraph.className = 'font-body-md text-body-md text-on-surface whitespace-pre-wrap';
    paragraph.textContent = text;
    bubble.appendChild(paragraph);

    container.appendChild(avatar);
    container.appendChild(bubble);
    wrapper.appendChild(container);
    return wrapper;
}

async function bindChatPage() {
    const messagesEl = document.getElementById('messages');
    const inputEl = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const crisisBtn = document.getElementById('crisis-btn');
    const welcomeBackBanner = document.getElementById('welcome-back-banner');

    if (!messagesEl || !inputEl || !sendBtn) return;

    let session = loadSession();
    if (!session || !session.user_id) {
        for (let i = 0; i < 5; i++) {
            session = await restoreSessionFromSupabase();

            if (session?.user_id) {
                break;
            }

            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    if (!session || !session.user_id) {
        navigate('/login');
        return;
    }

    try {
        await apiFetch('/api/user-profile?user_id=' + encodeURIComponent(session.user_id));
    } catch (error) {
        if (error.status === 400 || error.status === 404 || error.status === 401) {
            clearSession();
            navigate('/login');
            return;
        }
    }

    if (!session.name || !session.name.trim()) {
        navigate('/onboarding');
        return;
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            clearSession();
            navigate('/login');
        });
    }

    if (crisisBtn) {
        crisisBtn.addEventListener('click', () => {
            const safetyBanner = document.querySelector('div.bg-surface-container.w-full.mt-20');
            if (safetyBanner) {
                safetyBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            alert('If you are in immediate danger or may harm yourself, contact local emergency services now.');
        });
    }

    bindTextControl('button', 'Profile', () => {
        navigate('/chat');
    });

    bindTextControl('a', 'Home', () => {
        navigate('/');
    });

    bindTextControl('a', 'Insights', () => {
        navigate('/#landing-features');
    });

    bindTextControl('a', 'Resources', () => {
        navigate('/#landing-features');
    });

    let historyLoaded = false;
    let sending = false;
    let typingIndicator = null;
    let welcomeBackShown = false;

    const scrollToBottom = () => {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    };

    const showTyping = () => {
        if (typingIndicator) return;
        typingIndicator = document.createElement('div');
        typingIndicator.className = 'flex justify-start fade-in-up';
        typingIndicator.innerHTML = `
            <div class="flex gap-3 max-w-[80%]">
                <div class="w-8 h-8 rounded-full bg-lavender-soft flex-shrink-0 flex items-center justify-center text-lavender-dark mt-1">
                    <span class="material-symbols-outlined text-[16px]">psychiatry</span>
                </div>
                <div class="bg-lavender-soft/40 p-4 rounded-2xl rounded-bl-sm flex gap-1 items-center">
                    <div class="w-2 h-2 bg-lavender-dark/50 rounded-full animate-bounce"></div>
                    <div class="w-2 h-2 bg-lavender-dark/50 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                    <div class="w-2 h-2 bg-lavender-dark/50 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                </div>
            </div>
        `;
        messagesEl.appendChild(typingIndicator);
        scrollToBottom();
    };

    const hideTyping = () => {
        if (typingIndicator) {
            typingIndicator.remove();
            typingIndicator = null;
        }
    };

    const showWelcomeBackBanner = () => {
        if (!welcomeBackBanner || welcomeBackShown) return;
        welcomeBackBanner.textContent = "Welcome back. I'm glad to see you again.";
        welcomeBackBanner.style.display = 'flex';
        welcomeBackShown = true;
    };

    const hideWelcomeBackBanner = () => {
        if (!welcomeBackBanner) return;
        welcomeBackBanner.textContent = '';
        welcomeBackBanner.style.display = 'none';
    };

    const loadHistory = async () => {
        try {
            const result = await apiFetch('/api/history?user_id=' + encodeURIComponent(session.user_id), { timeout: 20000 });
            messagesEl.innerHTML = '';
            const history = result?.history || [];
            history.forEach((item) => {
                const role = item.role === 'ai' ? 'ai' : 'user';
                const text = item.content || item.message || '';
                messagesEl.appendChild(createMessageBubble(role, text));
            });
            if (history.length > 0) {
                showWelcomeBackBanner();
            } else {
                hideWelcomeBackBanner();
            }
            historyLoaded = true;
            scrollToBottom();
        } catch (error) {
            console.error('History load failed:', error);
            if (!historyLoaded) {
                hideWelcomeBackBanner();
                const note = document.createElement('div');
                note.className = 'flex justify-center';
                note.innerHTML = '<div class="bg-surface-container-low px-4 py-2 rounded-full text-sage-deep font-label-sm text-label-sm">History is unavailable right now. You can still send a new message.</div>';
                messagesEl.prepend(note);
            }
        }
    };

    const sendMessage = async () => {
        if (sending) return;
        const message = (inputEl.value || '').trim();
        if (!message) return;
        if (message.length > 2000) {
            alert('Please keep messages under 2000 characters.');
            return;
        }

        sending = true;
        sendBtn.disabled = true;
        showTyping();
        messagesEl.appendChild(createMessageBubble('user', message));
        inputEl.value = '';
        scrollToBottom();

        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: session.user_id, message }),
            });

            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }

            hideTyping();

            // Create streaming bubble
            const wrapper = document.createElement('div');
            wrapper.className = 'flex justify-start fade-in-up';

            const container = document.createElement('div');
            container.className = 'flex gap-3 max-w-[80%]';

            const avatar = document.createElement('div');
            avatar.className = 'w-8 h-8 rounded-full bg-lavender-soft flex-shrink-0 flex items-center justify-center text-lavender-dark mt-1';
            avatar.innerHTML = '<span class="material-symbols-outlined text-[16px]">psychiatry</span>';

            const bubble = document.createElement('div');
            bubble.className = 'bg-lavender-soft/40 p-stack-md rounded-2xl rounded-bl-sm shadow-sm border border-lavender-soft/50';
            const paragraph = document.createElement('p');
            paragraph.className = 'font-body-md text-body-md text-on-surface whitespace-pre-wrap';
            paragraph.textContent = '';
            bubble.appendChild(paragraph);

            container.appendChild(avatar);
            container.appendChild(bubble);
            wrapper.appendChild(container);
            
            messagesEl.appendChild(wrapper);
            scrollToBottom();

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            let aiResponseText = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep partial line in buffer

                for (const line of lines) {
                    const cleanLine = line.trim();
                    if (!cleanLine.startsWith('data: ')) continue;
                    
                    try {
                        const parsed = JSON.parse(cleanLine.substring(6));
                        if (parsed.text) {
                            aiResponseText += parsed.text;
                            paragraph.textContent = aiResponseText;
                            scrollToBottom();
                        } else if (parsed.error) {
                            console.error('Stream error:', parsed.error);
                        }
                    } catch (e) {
                        console.error('Failed to parse stream line:', cleanLine, e);
                    }
                }
            }

            if (buffer) {
                const cleanLine = buffer.trim();
                if (cleanLine.startsWith('data: ')) {
                    try {
                        const parsed = JSON.parse(cleanLine.substring(6));
                        if (parsed.text) {
                            aiResponseText += parsed.text;
                            paragraph.textContent = aiResponseText;
                            scrollToBottom();
                        }
                    } catch (e) {}
                }
            }
        } catch (error) {
            console.error('Chat stream failed, falling back to standard POST:', error);
            hideTyping();
            try {
                showTyping();
                const result = await apiFetch('/api/chat', {
                    method: 'POST',
                    body: { user_id: session.user_id, message },
                    timeout: 60000,
                });
                hideTyping();
                messagesEl.appendChild(createMessageBubble('ai', result?.response || 'I am here with you.'));
            } catch (fallbackError) {
                console.error('Fallback chat send failed:', fallbackError);
                hideTyping();
                const errorBubble = document.createElement('div');
                errorBubble.className = 'flex justify-start fade-in-up';
                errorBubble.innerHTML = '<div class="bg-error-container text-on-error-container px-4 py-3 rounded-2xl rounded-bl-sm max-w-[80%]">Message could not be sent. Please try again.</div>';
                messagesEl.appendChild(errorBubble);
            }
        } finally {
            hideTyping();
            sending = false;
            sendBtn.disabled = false;
            scrollToBottom();
        }
    };

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendMessage();
        }
    });

    loadHistory();
}

async function bindGeneralRouting() {
    const session = loadSession();
    const loginForm = document.getElementById('login-form');

    if (loginForm) {
        ensureAuthViews();
        bindLoginForm();
        bindSignupForm();
        bindGoogleAuth();
    }

    if (window.location.pathname === '/login') {
        const oauthHandled = await completeOAuthLogin();
        if (oauthHandled) {
            return;
        }

        if (session && session.user_id) {
            if (!session.name || !session.name.trim()) {
                navigate('/onboarding');
            } else {
                navigate('/chat');
            }
            return;
        }

        try {
            const restoredSession = await restoreSessionFromSupabase();
            if (restoredSession && restoredSession.user_id) {
                if (!restoredSession.name || !restoredSession.name.trim()) {
                    navigate('/onboarding');
                } else {
                    navigate('/chat');
                }
                return;
            }
        } catch (error) {
            console.warn('Login session restore skipped:', error);
        }
    }

    if (loginForm && session && session.user_id) {
        if (!session.name || !session.name.trim()) {
            navigate('/onboarding');
        } else {
            navigate('/chat');
        }
        return;
    }

    if (document.getElementById('landing-hero-start') || document.getElementById('landing-start-venting')) {
        bindLandingPage();
    }

    if (document.getElementById('messages') || document.getElementById('chat-input')) {
        bindChatPage();
    }
}

window.RAAHAT_API = {
    apiFetch,
    saveSession,
    loadSession,
    clearSession,
};

document.addEventListener('DOMContentLoaded', bindGeneralRouting);
