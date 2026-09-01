/**
 * AIML SMART ATTENDANCE MANAGEMENT SYSTEM
 * JavaScript Utilities & Live IST Clock
 */

document.addEventListener('DOMContentLoaded', () => {
    // Update live IST Clock
    function updateISTClock() {
        const clockElement = document.getElementById('live-ist-clock');
        if (!clockElement) return;

        const now = new Date();
        const options = {
            timeZone: 'Asia/Kolkata',
            hour12: true,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        };
        const istFormatted = new Intl.DateTimeFormat('en-IN', options).format(now);
        clockElement.innerText = istFormatted + ' (IST)';
    }

    updateISTClock();
    setInterval(updateISTClock, 1000);

    // Auto dismiss flash alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });
});
