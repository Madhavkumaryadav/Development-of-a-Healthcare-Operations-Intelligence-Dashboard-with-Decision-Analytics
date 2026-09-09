"""Application-wide Streamlit login gate."""

from __future__ import annotations

import time

import streamlit as st

from src.admin_auth import authenticate

MAX_FAILURES = 5
LOCKOUT_SECONDS = 60


def _inject_cursor_trail() -> None:
    """Inject a lightweight canvas-based 'pulse trail' cursor effect.

    Runs in a zero-height component iframe but attaches its canvas to the
    *parent* document (same-origin, so this works fine inside Streamlit),
    so the effect covers the whole app rather than a little iframe box.
    """
    st.markdown(
        """
        <iframe height="0" width="0" style="border:none; visibility:hidden; position:absolute;">
        <script>
        (function () {
            const doc = window.parent.document;
            if (doc.getElementById('hs-cursor-fx')) { return; }

            const canvas = doc.createElement('canvas');
            canvas.id = 'hs-cursor-fx';
            Object.assign(canvas.style, {
                position: 'fixed', top: '0', left: '0',
                width: '100vw', height: '100vh',
                pointerEvents: 'none', zIndex: '2147483647'
            });
            doc.body.appendChild(canvas);

            const ctx = canvas.getContext('2d');
            const dpr = window.parent.devicePixelRatio || 1;

            function resize() {
                canvas.width = window.parent.innerWidth * dpr;
                canvas.height = window.parent.innerHeight * dpr;
                canvas.style.width = window.parent.innerWidth + 'px';
                canvas.style.height = window.parent.innerHeight + 'px';
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            }
            resize();
            window.parent.addEventListener('resize', resize);

            let points = [];
            let lastT = 0;
            const palette = ['#0F6B78', '#16855B', '#17324D', '#C98A00'];

            doc.addEventListener('mousemove', (e) => {
                const now = performance.now();
                if (now - lastT > 14) {
                    points.push({ x: e.clientX, y: e.clientY, t: now });
                    lastT = now;
                }
            });

            function tick(now) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                points = points.filter(p => now - p.t < 650);

                // connecting line, like a waveform / data trace
                if (points.length > 1) {
                    ctx.beginPath();
                    ctx.moveTo(points[0].x, points[0].y);
                    for (let i = 1; i < points.length; i++) {
                        ctx.lineTo(points[i].x, points[i].y);
                    }
                    ctx.strokeStyle = 'rgba(15, 107, 120, 0.22)';
                    ctx.lineWidth = 1.5;
                    ctx.stroke();
                }

                points.forEach((p, i) => {
                    const age = (now - p.t) / 650;
                    const r = 4.5 * (1 - age) + 0.8;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
                    ctx.fillStyle = palette[i % palette.length];
                    ctx.globalAlpha = 1 - age;
                    ctx.fill();
                });
                ctx.globalAlpha = 1;

                requestAnimationFrame(tick);
            }
            requestAnimationFrame(tick);
        
        </script>
        </iframe>
        """,
        unsafe_allow_html=True,
    )


def _login_styles() -> None:
    st.markdown(
        """
        <style>
        /* ---------- page shell ---------- */
        [data-testid="stAppViewContainer"] {
            background: #0a0f1a;
        }
        [data-testid="stHeader"] {
            background: transparent;
            visibility: hidden;
            height: 0;
        }
        [data-testid="stSidebar"] { display: none; }

        /* ---------- animated background orbs ---------- */
        .login-bg {
            position: fixed;
            inset: 0;
            overflow: hidden;
            z-index: 0;
            pointer-events: none;
        }
        .login-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.4;
            animation: orb-float 20s ease-in-out infinite;
        }
        .login-orb-1 {
            width: 600px; height: 600px;
            background: radial-gradient(circle, #17324D 0%, #0F6B78 50%, transparent 70%);
            top: -200px; left: -150px;
        }
        .login-orb-2 {
            width: 500px; height: 500px;
            background: radial-gradient(circle, #0F6B78 0%, #16855B 50%, transparent 70%);
            bottom: -150px; right: -100px;
            animation-delay: -7s;
        }
        .login-orb-3 {
            width: 400px; height: 400px;
            background: radial-gradient(circle, #C98A00 0%, #C43D3D 50%, transparent 70%);
            top: 30%; right: -100px;
            animation-delay: -14s;
            opacity: 0.2;
        }
        @keyframes orb-float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            25% { transform: translate(30px, -40px) scale(1.05); }
            50% { transform: translate(-20px, 20px) scale(0.95); }
            75% { transform: translate(40px, 30px) scale(1.02); }
        }
        .login-particle {
            position: absolute;
            width: 4px; height: 4px;
            background: rgba(15, 107, 120, 0.35);
            border-radius: 50%;
            animation: particle-float linear infinite;
        }
        @keyframes particle-float {
            0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { transform: translateY(-100px) rotate(720deg); opacity: 0; }
        }

        /* ---------- the real card: Streamlit's own block-container ---------- */
        .block-container {
            position: relative;
            z-index: 10;
            max-width: 440px !important;
            margin: 6vh auto 0 auto !important;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 20px;
            padding: 42px 44px 38px !important;
            box-shadow:
                0 30px 80px rgba(0, 0, 0, 0.4),
                0 10px 30px rgba(0, 0, 0, 0.2),
                0 0 0 1px rgba(255, 255, 255, 0.1) inset;
            backdrop-filter: blur(20px);
            animation: card-entrance 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @keyframes card-entrance {
            from { opacity: 0; transform: translateY(30px) scale(0.96); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        /* ---------- brand header ---------- */
        .login-brand {
            display: flex; align-items: center; justify-content: center;
            gap: 14px; margin-bottom: 28px;
        }
        .login-brand-icon {
            width: 52px; height: 52px;
            border-radius: 16px;
            background: linear-gradient(135deg, #17324D 0%, #0F6B78 50%, #16855B 100%);
            display: flex; align-items: center; justify-content: center;
            font-size: 1.6rem;
            box-shadow: 0 8px 20px rgba(15, 107, 120, 0.3);
            animation: brand-pulse 2.4s ease-in-out infinite;
        }
        @keyframes brand-pulse {
            0%, 100% { box-shadow: 0 8px 20px rgba(15, 107, 120, 0.3); }
            50% { box-shadow: 0 8px 28px rgba(15, 107, 120, 0.55), 0 0 0 6px rgba(15, 107, 120, 0.08); }
        }
        .login-brand-text {
            font-size: 1.6rem; font-weight: 800;
            background: linear-gradient(135deg, #17324D 0%, #0F6B78 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.03em;
        }

        /* ---------- typography ---------- */
        .login-title {
            font-size: 1.75rem; font-weight: 800; color: #17324D;
            text-align: center; margin: 0 0 6px; letter-spacing: -0.02em;
        }
        .login-subtitle {
            font-size: 0.9rem; color: #64748B; text-align: center;
            margin-bottom: 28px; line-height: 1.5;
        }
        .input-label {
            display: block; font-size: 0.78rem; font-weight: 700;
            color: #475569; margin: 0 0 6px 2px;
            letter-spacing: 0.04em; text-transform: uppercase;
        }

        /* ---------- real Streamlit inputs, styled ---------- */
        div[data-testid="stForm"] {
            border: none; padding: 0; background: transparent;
        }
        div[data-testid="stTextInput"] {
            margin-bottom: 4px;
            border-radius: 12px;
            transition: box-shadow 0.25s ease, transform 0.25s ease;
        }
        div[data-testid="stTextInput"]:focus-within {
            box-shadow: 0 0 0 4px rgba(15, 107, 120, 0.12);
            transform: translateY(-1px);
        }
        .stTextInput input {
            padding: 14px 16px !important;
            font-size: 1rem;
            color: #17324D;
            background: #F8FAFC;
            border: 2px solid #E2E8F0 !important;
            border-radius: 12px !important;
            transition: all 0.25s ease;
            font-weight: 500;
        }
        .stTextInput input:focus {
            border-color: #0F6B78 !important;
            background: #FFFFFF;
        }

        /* ---------- submit button ---------- */
        div[data-testid="stFormSubmitButton"] button {
            width: 100%;
            padding: 15px 24px !important;
            font-size: 1rem; font-weight: 700;
            background: linear-gradient(135deg, #17324D 0%, #0F6B78 100%) !important;
            border: none !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 14px rgba(15, 107, 120, 0.3);
            transition: all 0.25s ease;
            letter-spacing: 0.02em;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(15, 107, 120, 0.4);
        }
        div[data-testid="stFormSubmitButton"] button:active {
            transform: translateY(0);
            box-shadow: 0 2px 8px rgba(15, 107, 120, 0.3);
        }
        div[data-testid="stFormSubmitButton"] button p {
            color: white !important; font-weight: 700 !important;
        }

        /* ---------- messages ---------- */
        .login-error {
            background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
            border-left: 4px solid #C43D3D;
            border-radius: 10px; padding: 12px 16px; margin-bottom: 20px;
            font-size: 0.88rem; color: #991B1B; font-weight: 600;
            animation: shake 0.4s ease-in-out;
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            20% { transform: translateX(-6px); }
            40% { transform: translateX(6px); }
            60% { transform: translateX(-4px); }
            80% { transform: translateX(4px); }
        }
        .login-lockout {
            background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
            border-left: 4px solid #C98A00;
            border-radius: 10px; padding: 12px 16px; margin-bottom: 20px;
            font-size: 0.88rem; color: #92400E; font-weight: 600;
        }
        .login-footer {
            margin-top: 28px; text-align: center;
            font-size: 0.72rem; color: #94A3B8; letter-spacing: 0.05em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _login_background() -> None:
    particles_html = "".join(
        f'<div class="login-particle" style="left:{i * 5}%; '
        f'animation-delay:{i * 0.7}s; animation-duration:{12 + (i % 5)}s;"></div>'
        for i in range(20)
    )
    st.markdown(
        f"""
        <div class="login-bg">
            <div class="login-orb login-orb-1"></div>
            <div class="login-orb login-orb-2"></div>
            <div class="login-orb login-orb-3"></div>
            {particles_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def require_login() -> None:
    """Stop page execution until an account has authenticated successfully."""
    if st.session_state.get("authenticated"):
        with st.sidebar:
            st.caption(f"Signed in as {st.session_state.get('admin_full_name', 'user')}")
            if st.button("Sign out", key="global_sign_out", use_container_width=True):
                for key in ("authenticated", "admin_logged_in", "admin_username", "admin_full_name", "admin_department"):
                    st.session_state.pop(key, None)
                st.rerun()
        return

    _login_styles()
    _login_background()
    _inject_cursor_trail()

    st.markdown(
        """
        <div class="login-brand">
            <div class="login-brand-icon">🩺</div>
            <div class="login-brand-text">HealthSentinel</div>
        </div>
        <h1 class="login-title">Sign in to your account</h1>
        <p class="login-subtitle">Secure public-health analytics workspace<br>
        Sign in with an authorized account to continue.</p>
        """,
        unsafe_allow_html=True,
    )

    now = time.time()
    locked_until = float(st.session_state.get("login_locked_until", 0))
    is_locked = now < locked_until

    if is_locked:
        remaining = int(locked_until - now) + 1
        st.markdown(
            f'<div class="login-lockout">🔒 Too many failed attempts. '
            f'Try again in {remaining} seconds.</div>',
            unsafe_allow_html=True,
        )

    with st.form("global_login_form"):
        st.markdown('<span class="input-label">Username</span>', unsafe_allow_html=True)
        username = st.text_input(
            "Username",
            autocomplete="username",
            label_visibility="collapsed",
            key="login_username",
            disabled=is_locked,
        )

        st.markdown('<span class="input-label">Password</span>', unsafe_allow_html=True)
        password = st.text_input(
            "Password",
            type="password",
            autocomplete="current-password",
            label_visibility="collapsed",
            key="login_password",
            disabled=is_locked,
        )

        submitted = st.form_submit_button(
            "Sign in",
            type="primary",
            use_container_width=True,
            icon="🔐",
            disabled=is_locked,
        )

    if submitted and not is_locked:
        account = authenticate(username.strip(), password)
        if account:
            st.session_state.update({
                "authenticated": True,
                "admin_logged_in": True,
                "admin_username": account["username"],
                "admin_full_name": account["full_name"],
                "admin_department": account["department"],
                "login_failures": 0,
            })
            st.session_state.pop("login_password", None)
            st.rerun()

        failures = int(st.session_state.get("login_failures", 0)) + 1
        st.session_state["login_failures"] = failures
        st.session_state.pop("login_password", None)

        if failures >= MAX_FAILURES:
            st.session_state["login_locked_until"] = time.time() + LOCKOUT_SECONDS
            st.markdown(
                '<div class="login-error">🔒 Too many failed attempts. '
                'Login is temporarily locked.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="login-error">❌ Invalid username or password. '
                'Please try again.</div>',
                unsafe_allow_html=True,
            )
        st.rerun()

    st.markdown(
        '<div class="login-footer">Infosys Public Health Analytics · Internal Use</div>',
        unsafe_allow_html=True,
    )
    st.stop()