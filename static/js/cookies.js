document.addEventListener("DOMContentLoaded", function() {
    // 1. Create the banner HTML dynamically (or select it if it's in your HTML)
    const banner = document.getElementById('cookie-banner');
    
    if (!localStorage.getItem('cookieConsent') && banner) {
        banner.classList.remove('d-none'); // Show it
    }

    const acceptBtn = document.getElementById('accept-cookies');
    if (acceptBtn) {
        acceptBtn.addEventListener('click', function() {
            localStorage.setItem('cookieConsent', 'true');
            banner.classList.add('d-none'); // Hide it
        });
    }
});