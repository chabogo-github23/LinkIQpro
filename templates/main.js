document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileDropdownMenu = document.getElementById('mobile-dropdown-menu');
    const themeToggleButton = document.getElementById('theme-toggle');
    const body = document.body;

    // Mobile Menu Toggle
    if (mobileMenuButton && mobileDropdownMenu) {
        mobileMenuButton.addEventListener('click', function() {
            const isOpen = mobileDropdownMenu.classList.toggle('is-open');
            mobileMenuButton.classList.toggle('open');
            mobileMenuButton.setAttribute('aria-expanded', isOpen);
            mobileDropdownMenu.setAttribute('aria-hidden', !isOpen);
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!mobileDropdownMenu.contains(event.target) && !mobileMenuButton.contains(event.target)) {
                if (mobileDropdownMenu.classList.contains('is-open')) {
                    mobileDropdownMenu.classList.remove('is-open');
                    mobileMenuButton.classList.remove('open');
                    mobileMenuButton.setAttribute('aria-expanded', 'false');
                    mobileDropdownMenu.setAttribute('aria-hidden', 'true');
                }
            }
        });
    }

    // Theme Toggle
    if (themeToggleButton && body) {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            body.classList.add('dark-theme');
        }
        themeToggleButton.addEventListener('click', function() {
            body.classList.toggle('dark-theme');
            if (body.classList.contains('dark-theme')) {
                localStorage.setItem('theme', 'dark');
            } else {
                localStorage.setItem('theme', 'light');
            }
        });
    }
});