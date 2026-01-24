/**
 * Modern Travel UI Library
 * Handles UI interactions, themes, and animations.
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initDropdowns();
    initModals();
});

/**
 * Theme Management
 * Persists theme preference in localStorage
 */
function initTheme() {
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme === 'dark') {
        body.classList.add('dark-mode');
        updateThemeIcon('dark');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            const isDark = body.classList.contains('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            updateThemeIcon(isDark ? 'dark' : 'light');
        });
    }
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('#themeToggle i');
    if (!icon) return;
    if (theme === 'dark') {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    } else {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
    }
}

/**
 * Sidebar Management
 * Handles mobile toggle and collapsed state
 */
function initSidebar() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.querySelector('.sidebar');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            if (window.innerWidth > 1024) {
                sidebar.classList.toggle('collapsed');
            } else {
                sidebar.classList.toggle('active');
            }
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 1024 && sidebar && sidebar.classList.contains('active')) {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        }
    });
}

/**
 * Dropdown Management
 */
function initDropdowns() {
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const menu = toggle.nextElementSibling;
            if (menu) menu.classList.toggle('show');
        });
    });

    window.addEventListener('click', () => {
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
    });
}

/**
 * Modal Helper (Optional)
 */
function initModals() {
    // Logic for custom modals if needed
}

/**
 * Tab Switching Logic (Reusable)
 */
window.openTab = function (tabId, btn) {
    // Hide all tab content
    const contents = document.querySelectorAll('.tab-content');
    contents.forEach(content => content.classList.remove('active'));

    // Deactivate all tab buttons in the same container
    const tabBtns = btn.parentElement.querySelectorAll('.tab-btn');
    tabBtns.forEach(b => b.classList.remove('active'));

    // Show selected tab and activate button
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
}
