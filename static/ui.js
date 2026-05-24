// --- 1. AURA CURSOR ---
function initAuraCursor() {
    const cursor = document.createElement('div');
    cursor.id = 'aura-cursor';
    document.body.classList.add('custom-cursor-enabled');
    document.body.appendChild(cursor);

    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let cursorX = mouseX;
    let cursorY = mouseY;

    // Smooth following logic
    function loop() {
        cursorX += (mouseX - cursorX) * 0.2;
        cursorY += (mouseY - cursorY) * 0.2;
        cursor.style.transform = `translate(${cursorX}px, ${cursorY}px)`;
        requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);

    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    // Expand on interactive elements
    const interactives = document.querySelectorAll('a, button, input, textarea, .cursor-pointer, .glass-card, .glass-panel');
    interactives.forEach(el => {
        el.addEventListener('mouseenter', () => cursor.classList.add('hovering'));
        el.addEventListener('mouseleave', () => cursor.classList.remove('hovering'));
    });
}

// --- 2. SPOTLIGHT CARDS ---
function initSpotlight() {
    const cards = document.querySelectorAll('.spotlight-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

// --- 3. 3D TILT ---
function initTilt() {
    const tiltElements = document.querySelectorAll('.tilt-element');
    tiltElements.forEach(el => {
        el.addEventListener('mousemove', (e) => {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            // Calculate rotation (max 10 degrees)
            const xRotation = ((y - rect.height / 2) / rect.height) * -20;
            const yRotation = ((x - rect.width / 2) / rect.width) * 20;

            el.style.transform = `perspective(1000px) rotateX(${xRotation}deg) rotateY(${yRotation}deg) scale3d(1.02, 1.02, 1.02)`;
        });

        el.addEventListener('mouseleave', () => {
            el.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
        });
    });
}

// --- 4. PAGE TRANSITIONS ---
// Intercept all same-origin link clicks and apply exit animation
function initTransitions() {
    document.addEventListener('click', (e) => {
        // Find closest anchor tag
        const link = e.target.closest('a');
        if (link && link.href) {
            const url = new URL(link.href);
            const isHashOnlyLink = url.origin === window.location.origin && url.pathname === window.location.pathname && url.search === '' && url.hash;
            // If it's a local navigation and not opening in new tab
            if (url.origin === window.location.origin && link.target !== '_blank' && !link.hasAttribute('download') && !isHashOnlyLink) {
                e.preventDefault();
                document.body.classList.add('page-exit');
                setTimeout(() => {
                    window.location.href = link.href;
                }, 400); // Matches CSS exit animation duration
            }
        }
    });
}

// Custom navigate function for JS-based redirects
window.navigateWithTransition = function (url) {
    // Create loading overlay
    const loader = document.createElement('div');

    loader.style.position = 'fixed';
    loader.style.inset = '0';
    loader.style.background = '#0f172a';
    loader.style.display = 'flex';
    loader.style.alignItems = 'center';
    loader.style.justifyContent = 'center';
    loader.style.zIndex = '99999';
    loader.style.opacity = '0';
    loader.style.transition = 'opacity 0.3s ease';

    loader.innerHTML = `
        <div style="
            width:48px;
            height:48px;
            border:3px solid rgba(249,115,22,0.2);
            border-top-color:#f97316;
            border-radius:50%;
            animation:spin 0.8s linear infinite;
        "></div>
    `;

    document.body.appendChild(loader);

    requestAnimationFrame(() => {
        loader.style.opacity = '1';
        document.body.classList.add('page-exit');
    });

    setTimeout(() => {
        window.location.href = url;
    }, 250);
};

// Initialize everything on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    initAuraCursor();
    initSpotlight();
    initTilt();
    initTransitions();
});
