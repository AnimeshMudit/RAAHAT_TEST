const API_BASE = window.location.origin;
const SESSION_KEY = 'raahat_user';
let supabaseClient = null;

function apiFetch(path, { method = 'GET', body = null, timeout = 15000 } = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    const options = {
        method,
        headers: {
            Accept: 'application/json',
        },
        signal: controller.signal,
    };

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
        const client = getSupabaseClient();
        const { data, error } = await client.auth.exchangeCodeForSession(code);
        if (error) throw error;

        const email = data?.session?.user?.email || data?.session?.user?.user_metadata?.email;
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
        });

        await new Promise(resolve => setTimeout(resolve, 1500));

        navigate('/chat');
        return true;
    } catch (error) {
        console.error('OAuth completion failed:', error);
        showStatus(error.message || 'Google sign-in failed.', 'error');
        return true;
    }
}

async function restoreSessionFromSupabase() {
    try {
        if (!window.SUPABASE_URL || !window.SUPABASE_KEY) {
            return null;
        }

        if (typeof supabase === 'undefined' || typeof supabase.createClient !== 'function') {
            return null;
        }

        const client = getSupabaseClient();
        const { data, error } = await client.auth.getSession();
        const email = data?.session?.user?.email;

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

    const loginPasswordRow = loginForm.querySelector('a[href="#"]');
    if (loginPasswordRow) {
        loginPasswordRow.outerHTML = '<span class="font-label-sm text-label-sm text-sage-muted">Forgot Password? Use OTP verification after sign up.</span>';
    }

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

    const otpForm = document.createElement('form');
    otpForm.id = 'otp-form';
    otpForm.className = 'hidden space-y-stack-md mt-stack-lg';
    otpForm.action = '#';
    otpForm.method = 'POST';
    otpForm.innerHTML = `
        <div class="relative">
            <label class="block font-label-md text-label-md text-on-surface-variant mb-stack-sm" for="otp-email">Email Address</label>
            <div class="relative">
                <span class="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-outline-variant pointer-events-none">mail</span>
                <input class="w-full bg-surface-container-lowest border border-outline-variant rounded-lg pl-10 pr-4 py-3 font-body-md text-body-md text-on-surface focus:border-lavender-dark focus:ring-2 focus:ring-lavender-soft transition-all placeholder-outline-variant/70 shadow-sm" id="otp-email" name="otp-email" placeholder="you@example.com" required type="email" />
            </div>
        </div>
        <div class="relative">
            <label class="block font-label-md text-label-md text-on-surface-variant mb-stack-sm" for="otp-token">Verification Code</label>
            <div class="relative">
                <span class="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-outline-variant pointer-events-none">verified</span>
                <input class="w-full bg-surface-container-lowest border border-outline-variant rounded-lg pl-10 pr-4 py-3 font-body-md text-body-md text-on-surface focus:border-lavender-dark focus:ring-2 focus:ring-lavender-soft transition-all placeholder-outline-variant/70 shadow-sm" id="otp-token" name="otp-token" placeholder="123456" required type="text" />
            </div>
        </div>
        <button id="otp-submit" class="w-full bg-sage-muted text-white font-label-md text-label-md py-3 rounded-full hover:bg-sage-deep shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-0.5" type="submit">Verify and Continue</button>
    `;

    loginForm.parentNode.insertBefore(signupForm, loginForm.nextSibling);
    signupForm.parentNode.insertBefore(otpForm, signupForm.nextSibling);

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
    const otpForm = document.getElementById('otp-form');
    const showLoginButton = document.getElementById('show-login');
    const showSignupButton = document.getElementById('show-signup');
    const viewMap = {
        login: loginForm,
        signup: signupForm,
        otp: otpForm,
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
                saveSession({ user_id: result.user_id, username: result.username || email });
                navigate('/chat');
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
        if (password.length < 6) {
            showStatus('Password must be at least 6 characters.', 'error');
            return;
        }

        setButtonLoading(submitButton, true, 'Creating account...');
        try {
            const result = await apiFetch('/api/signup', {
                method: 'POST',
                body: { username: email, password },
                timeout: 25000,
            });
            showStatus(result?.message || 'Verification code sent. Check your email.', 'info');
            const otpEmail = document.getElementById('otp-email');
            if (otpEmail) otpEmail.value = email;
            setAuthView('otp');
        } catch (error) {
            console.error('Signup failed:', error);
            showStatus(error.message || 'Signup failed.', 'error');
        } finally {
            setButtonLoading(submitButton, false);
        }
    });
}

function bindOtpForm() {
    const otpForm = document.getElementById('otp-form');
    if (!otpForm) return;

    otpForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        hideStatus();

        const email = document.getElementById('otp-email')?.value?.trim() || '';
        const token = document.getElementById('otp-token')?.value?.trim() || '';
        const submitButton = document.getElementById('otp-submit');

        if (!emailLooksValid(email)) {
            showStatus('Enter a valid email address.', 'error');
            return;
        }
        if (!token) {
            showStatus('Enter the verification code.', 'error');
            return;
        }

        setButtonLoading(submitButton, true, 'Verifying...');
        try {
            const result = await apiFetch('/api/verify-otp', {
                method: 'POST',
                body: { email, token },
                timeout: 25000,
            });
            if (result && result.user_id) {
                saveSession({ user_id: result.user_id, username: result.username || email });
                navigate('/chat');
                return;
            }
            throw new Error('Verification succeeded but no session was returned.');
        } catch (error) {
            console.error('OTP verification failed:', error);
            showStatus(error.message || 'OTP verification failed.', 'error');
        } finally {
            setButtonLoading(submitButton, false);
        }
    });
}

function getSupabaseClient() {
    if (supabaseClient) {
        return supabaseClient;
    }

    if (!window.SUPABASE_URL || !window.SUPABASE_KEY) {
        throw new Error('Supabase is not configured for this page.');
    }

    if (typeof supabase === 'undefined' || typeof supabase.createClient !== 'function') {
        throw new Error('Supabase client library is not loaded.');
    }

    supabaseClient = supabase.createClient(window.SUPABASE_URL, window.SUPABASE_KEY);
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
            const client = getSupabaseClient();
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
            const result = await apiFetch('/api/chat', {
                method: 'POST',
                body: { user_id: session.user_id, message },
                timeout: 60000,
            });
            messagesEl.appendChild(createMessageBubble('ai', result?.response || 'I am here with you.'));
        } catch (error) {
            console.error('Chat send failed:', error);
            const errorBubble = document.createElement('div');
            errorBubble.className = 'flex justify-start fade-in-up';
            errorBubble.innerHTML = '<div class="bg-error-container text-on-error-container px-4 py-3 rounded-2xl rounded-bl-sm max-w-[80%]">Message could not be sent. Please try again.</div>';
            messagesEl.appendChild(errorBubble);
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
        bindOtpForm();
        bindGoogleAuth();
    }

    if (window.location.pathname === '/login') {
        const oauthHandled = await completeOAuthLogin();
        if (oauthHandled) {
            return;
        }

        if (session && session.user_id) {
            navigate('/chat');
            return;
        }

        try {
            const restoredSession = await restoreSessionFromSupabase();
            if (restoredSession && restoredSession.user_id) {
                navigate('/chat');
                return;
            }
        } catch (error) {
            console.warn('Login session restore skipped:', error);
        }
    }

    if (loginForm && session && session.user_id) {
        navigate('/chat');
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
