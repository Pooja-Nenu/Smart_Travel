/**
 * Switch between Login and Register views with animation
 * @param {string} view - 'login' or 'register'
 */
function switchView(view) {
    const loginBox = document.getElementById('login-box');
    const registerBox = document.getElementById('register-box');

    if (view === 'register') {
        // Fade out login
        loginBox.style.opacity = '0';
        setTimeout(() => {
            loginBox.classList.add('d-none');
            registerBox.classList.remove('d-none');
            // Trigger reflow
            void registerBox.offsetWidth; 
            // Fade in register
            registerBox.style.opacity = '1';
        }, 200); // Wait 200ms for fade out
    } else {
        // Fade out register
        registerBox.style.opacity = '0';
        setTimeout(() => {
            registerBox.classList.add('d-none');
            loginBox.classList.remove('d-none');
            // Trigger reflow
            void loginBox.offsetWidth;
            // Fade in login
            loginBox.style.opacity = '1';
        }, 200);
    }
}

function handleLogin(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    
    // Simulate Loading
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Signing in...';
    btn.disabled = true;

    setTimeout(() => {
        // In real app: Validate credentials via API here
        alert("Login Successful! (Redirecting to Dashboard...)");
        
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
        
        // Redirect (Uncomment later)
        // window.location.href = 'dashboard.html';
    }, 1500);
}

function handleRegister(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;

    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating account...';
    btn.disabled = true;

    setTimeout(() => {
        alert("Account Created! Please Log In.");
        btn.innerHTML = originalText;
        btn.disabled = false;
        switchView('login');
    }, 1500);
}