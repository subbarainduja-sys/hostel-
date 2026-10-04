const generateButton = document.getElementById("generateQR");
const qrWrapper = document.getElementById("qr-wrapper");
const timer = document.getElementById("qr-timer");
let countdownInterval;

async function generateQR() {
    clearInterval(countdownInterval);
    qrWrapper.innerHTML = "<p>Generating QR...</p>";

    try {
        const response = await fetch("/api/generate-qr");
        const data = await response.json();

        const image = document.createElement("img");
        image.src = data.image;
        qrWrapper.innerHTML = "";
        qrWrapper.appendChild(image);

        let remaining = 60;
        timer.textContent = "QR expires in " + remaining + " seconds";

        countdownInterval = setInterval(function () {
            remaining--;
            if (remaining <= 0) {
                clearInterval(countdownInterval);
                timer.textContent = "QR expired. Generate a new QR.";
                qrWrapper.innerHTML = '<div class="qr-placeholder">QR Expired</div>';
                return;
            }
            timer.textContent = "QR expires in " + remaining + " seconds";
        }, 1000);
    } catch (error) {
        console.error(error);
        qrWrapper.innerHTML = "<p>Unable to generate QR.</p>";
    }
}

if (generateButton) {
    generateButton.addEventListener("click", generateQR);
}
