let startTime = Date.now();
let timerInterval;
let scrollSpeedDisplay = document.getElementById("scroll-speed");
let typingSpeedDisplay = document.getElementById("typing-speed");
let timerDisplay = document.getElementById("timer");
let typingBox = document.getElementById("typing-box");

let metrics = {
    user_id: "user1",
    avg_mouse_x: 0,
    avg_mouse_y: 0,
    num_clicks: 0,
    scroll_speed: 0,
    typing_speed: 0
};

let mouseX = [];
let mouseY = [];
let keyPressTimes = [];
let lastScrollTop = window.scrollY;
let lastTimestamp = Date.now();

// Timer Logic
function startTimer(duration) {
    let timeLeft = duration;
    timerInterval = setInterval(() => {
        timeLeft--;
        timerDisplay.textContent = `Time Remaining: ${timeLeft}s`;
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            sendMetrics();
        }
    }, 1000);
}


document.addEventListener("mousemove", (e) => {
    mouseX.push(e.clientX);
    mouseY.push(e.clientY);
});


document.addEventListener("click", () => {
    metrics.num_clicks++;
});


typingBox.addEventListener("keydown", () => {
    const now = Date.now();
    if (keyPressTimes.length > 0) {
        const typingSpeed = now - keyPressTimes[keyPressTimes.length - 1];
        metrics.typing_speed =
            metrics.typing_speed === 0
                ? typingSpeed
                : (metrics.typing_speed + typingSpeed) / 2;

        typingSpeedDisplay.textContent = `Typing Speed: ${metrics.typing_speed.toFixed(2)} ms/keystroke`;
    }
    keyPressTimes.push(now);
});


window.addEventListener("scroll", () => {
    const currentScrollTop = window.scrollY;
    const currentTime = Date.now();

    const distance = Math.abs(currentScrollTop - lastScrollTop);
    const timeElapsed = (currentTime - lastTimestamp) / 1000;
    const scrollSpeed = timeElapsed > 0 ? (distance / timeElapsed).toFixed(2) : 0;

    metrics.scroll_speed =
        metrics.scroll_speed === 0
            ? parseFloat(scrollSpeed)
            : (metrics.scroll_speed + parseFloat(scrollSpeed)) / 2;

    scrollSpeedDisplay.textContent = `Scroll Speed: ${metrics.scroll_speed.toFixed(2)} px/s`;

    lastScrollTop = currentScrollTop;
    lastTimestamp = currentTime;
});


function sendMetrics() {
    if (mouseX.length > 0 && mouseY.length > 0) {
        metrics.avg_mouse_x = mouseX.reduce((a, b) => a + b, 0) / mouseX.length;
        metrics.avg_mouse_y = mouseY.reduce((a, b) => a + b, 0) / mouseY.length;
    }

    fetch("/track", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(metrics)
    })
        .then((response) => response.json())
        .then((data) => {
            console.log("Metrics sent:", data);
        })
        .catch((error) => console.error("Error sending metrics:", error));
}


startTimer(30);
