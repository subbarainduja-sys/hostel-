const video = document.getElementById("camera");
const canvas = document.getElementById("canvas");
const startButton = document.getElementById("startCamera");
const captureButton = document.getElementById("captureFace");
const stopButton = document.getElementById("stopCamera");
const result = document.getElementById("faceResult");

let stream = null;

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "user" },
            audio: false
        });
        video.srcObject = stream;
        captureButton.disabled = false;
        result.textContent = "Camera started. Position your face clearly.";
    } catch (error) {
        console.error(error);
        result.textContent = "Camera permission was denied or camera is unavailable.";
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
        video.srcObject = null;
    }
    captureButton.disabled = true;
    result.textContent = "Camera stopped.";
}

async function captureFace() {
    if (!stream) {
        result.textContent = "Please start the camera first.";
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const image = canvas.toDataURL("image/jpeg", 0.85);
    result.textContent = "Processing face...";

    try {
        const response = await fetch("/api/face-capture", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: image })
        });

        const data = await response.json();

        if (data.success) {
            result.innerHTML = "✅ " + data.message;
            stopCamera();
        } else {
            result.innerHTML = "⚠️ " + data.message;
        }
    } catch (error) {
        console.error(error);
        result.textContent = "Unable to process the face.";
    }
}

startButton.addEventListener("click", startCamera);
captureButton.addEventListener("click", captureFace);
stopButton.addEventListener("click", stopCamera);
