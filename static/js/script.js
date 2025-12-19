/* --------------------------------------------------
   1. VIEW SWITCHING & ANIMATIONS
-------------------------------------------------- */

function switchView(view) {
    const loginBox = document.getElementById('login-box');
    const registerBox = document.getElementById('register-box');

    if (view === 'register') {
        loginBox.style.opacity = '0';
        setTimeout(() => {
            loginBox.classList.add('d-none');
            registerBox.classList.remove('d-none');
            void registerBox.offsetWidth; 
            registerBox.style.opacity = '1';
        }, 200); 
    } else {
        registerBox.style.opacity = '0';
        setTimeout(() => {
            registerBox.classList.add('d-none');
            loginBox.classList.remove('d-none');
            void loginBox.offsetWidth;
            loginBox.style.opacity = '1';
        }, 200);
    }
}

/* --------------------------------------------------
   2. FORM HANDLING
-------------------------------------------------- */

function handleLogin(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Signing in...';
    btn.disabled = true;

    setTimeout(() => {
        alert("Login Successful! (Redirecting to Dashboard...)");
        btn.innerHTML = originalText;
        btn.disabled = false;
    }, 1500);
}

function handleRegister(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    
    const country = document.getElementById('regCountry').value;
    const state = document.getElementById('regState').value;

    if (!country || !state) {
        alert("Please select a valid Country and State.");
        return;
    }

    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating account...';
    btn.disabled = true;

    setTimeout(() => {
        alert(`Account Created for ${country}, ${state}! Please Log In.`);
        btn.innerHTML = originalText;
        btn.disabled = false;
        switchView('login');
    }, 1500);
}

/* --------------------------------------------------
   3. API LOGIC: Fetch Countries & States (Tom Select)
-------------------------------------------------- */

let countryTom, stateTom;

document.addEventListener('DOMContentLoaded', () => {
    if(document.getElementById('regCountry')) {
        
        // 1. Initialize Tom Select on Country
        countryTom = new TomSelect("#regCountry", {
            create: false,
            sortField: { field: "text", direction: "asc" },
            placeholder: "Select Country...",
            maxOptions: null
        });

        // 2. Initialize Tom Select on State
        stateTom = new TomSelect("#regState", {
            create: false,
            sortField: { field: "text", direction: "asc" },
            placeholder: "Select State...",
            valueField: 'value',
            labelField: 'text'
        });
        
        // --- FIX FOR COUNTRY DROPDOWN ---
        // When Country changes -> Remove Cursor (blur) AND Load States
        countryTom.on('change', (value) => {
            countryTom.blur(); 
            loadStates(value);
        });

        // --- FIX FOR STATE DROPDOWN ---
        // When State changes -> Remove Cursor (blur) immediately
        stateTom.on('change', () => {
            stateTom.blur(); 
        });
        
        stateTom.disable();

        // 3. Start Fetching Countries
        fetchCountries();
    }
});

function fetchCountries() {
    fetch('https://countriesnow.space/api/v0.1/countries/iso')
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                const countries = data.data.map(c => ({ value: c.name, text: c.name }));
                
                countryTom.clearOptions();
                countryTom.addOption(countries);
                countryTom.refreshOptions();
            }
        })
        .catch(err => console.error("Error loading countries:", err));
}

function loadStates(selectedCountry) {
    if (!selectedCountry) return;

    // Reset State Dropdown
    stateTom.clear();
    stateTom.clearOptions();
    stateTom.disable();
    stateTom.settings.placeholder = "Loading...";
    stateTom.sync();

    fetch('https://countriesnow.space/api/v0.1/countries/states', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ country: selectedCountry }),
    })
    .then(response => response.json())
    .then(data => {
        stateTom.settings.placeholder = "Select State";
        stateTom.enable();

        if (!data.error && data.data.states.length > 0) {
            const states = data.data.states.map(s => ({ value: s.name, text: s.name }));
            stateTom.addOption(states);
        } else {
            stateTom.addOption({ value: "N/A", text: "No states found / Not applicable" });
            stateTom.setValue("N/A");
        }
        stateTom.sync();
    })
    .catch(err => console.error("Error loading states:", err));
}