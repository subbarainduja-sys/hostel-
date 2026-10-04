document.addEventListener("DOMContentLoaded", function () {
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = "0";
            setTimeout(function () { alert.remove(); }, 500);
        }, 5000);
    });
});
