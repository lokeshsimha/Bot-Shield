// Initialize DOM elements
const typingBox = document.getElementById("typing-box");
const typingSpeedDisplay = document.getElementById("typing-speed");
const timerDisplay = document.getElementById("timer");
const scrollSpeedDisplay = document.getElementById("scroll-speed");

// Initialize tracking variables
let botDetected = false;
let typingSpeeds = []; // Array to store recent typing speeds
let pasteCount = 0;
let suspiciousCount = 0;
let lastKeypressTime = Date.now();
let lastKeyPressTime = Date.now(); // Variable to track last key press time
let redirectTimeout = null;
let timerStarted = false; // Flag to ensure the timer runs only once
let timeLeft = 30; // Make timeLeft a global variable
let scrollSpeeds = [];
let lastScrollTop = window.scrollY;
let lastTimestamp = Date.now();

// Start 30-second timer
function startTimer() {
    if (timerStarted) return;
    timerStarted = true;

    timerDisplay.textContent = `Time Remaining: ${timeLeft}s`;

    const timer = setInterval(() => {
        timeLeft--;
        timerDisplay.textContent = `Time Remaining: ${timeLeft}s`;

        if (timeLeft <= 0) {
            clearInterval(timer);
            timerDisplay.textContent = 'Time Complete';
            
            // Calculate and send final typing speed and scroll speed
            const avgTypingSpeed = typingSpeeds.length > 0 ? typingSpeeds.reduce((a, b) => a + b, 0) / typingSpeeds.length : 0;
            const avgScrollSpeed = scrollSpeeds.length > 0 ? scrollSpeeds.reduce((a, b) => a + b, 0) / scrollSpeeds.length : 0;
            sendBehaviorData(avgTypingSpeed, avgScrollSpeed);
            
            // Open dashboard in new tab
            window.open('/dashboard', '_blank');
        }
    }, 1000);
}

// Track typing speed
if (typingBox) {
    typingBox.addEventListener("paste", (event) => {
        pasteCount++;
        if (pasteCount >= 2) { // Flag as bot if more than 2 paste operations
            sendBehaviorData(0, 0);
        }
    });

    typingBox.addEventListener("keydown", (event) => {
        const now = Date.now();
        const timeBetweenKeystrokes = now - lastKeypressTime;
        lastKeypressTime = now;

        // Only consider reasonable typing speeds
        if (timeBetweenKeystrokes >= 10 && timeBetweenKeystrokes <= 1000) {
            typingSpeeds.push(timeBetweenKeystrokes);

            // Keep only last 15 keystrokes for better pattern detection
            if (typingSpeeds.length > 15) {
                typingSpeeds.shift();
            }

            // Calculate and display average typing speed
            const avgSpeed = typingSpeeds.reduce((a, b) => a + b, 0) / typingSpeeds.length;
            typingSpeedDisplay.textContent = `Typing Speed: ${avgSpeed.toFixed(2)} ms/keystroke`;
            
            // Check for bot-like behavior after collecting enough samples
            if (typingSpeeds.length >= 10) {
                checkForBot();
            }
        }
    });
}

// Add typing speed tracking functionality
document.addEventListener('keydown', () => {
    const currentTime = Date.now();
    const timeDiff = currentTime - lastKeyPressTime;
    
    if (timeDiff > 0) {
        const currentSpeed = timeDiff; // ms/keystroke
        typingSpeeds.push(currentSpeed);
        if (typingSpeeds.length > 5) {
            typingSpeeds.shift();
        }
        
        // Calculate average typing speed
        const avgTypingSpeed = typingSpeeds.reduce((a, b) => a + b, 0) / typingSpeeds.length;
        typingSpeedDisplay.textContent = `Typing Speed: ${avgTypingSpeed.toFixed(2)} ms/keystroke`;
    }
    
    lastKeyPressTime = currentTime;
});

// Add scroll speed tracking
window.addEventListener('scroll', () => {
    const currentScrollTop = window.scrollY;
    const currentTime = Date.now();
    const timeDiff = (currentTime - lastTimestamp) / 1000; // Convert to seconds
    
    if (timeDiff > 0) {
        const distance = Math.abs(currentScrollTop - lastScrollTop);
        const currentSpeed = distance / timeDiff; // px/s
        
        scrollSpeeds.push(currentSpeed);
        if (scrollSpeeds.length > 5) {
            scrollSpeeds.shift();
        }
        
        const avgScrollSpeed = scrollSpeeds.reduce((a, b) => a + b, 0) / scrollSpeeds.length;
        scrollSpeedDisplay.textContent = `Scroll Speed: ${avgScrollSpeed.toFixed(2)} px/s`;
        
        // Send scroll speed to backend
        sendBehaviorData(0, avgScrollSpeed);
        
        // Check for bot-like scroll behavior
        if (avgScrollSpeed > 5000) {
            if (!botDetected) {
                botDetected = true;
                sendBehaviorData(0, avgScrollSpeed);
                alert("Bot behavior detected. You will be logged out for security reasons.");
                window.location.href = '/logout';
            }
        }
    }
    
    lastScrollTop = currentScrollTop;
    lastTimestamp = currentTime;
});

// Check for bot-like behavior
function checkForBot() {
    if (typingSpeeds.length < 10) return;

    const avg = typingSpeeds.reduce((a, b) => a + b, 0) / typingSpeeds.length;
    const variance = Math.sqrt(
        typingSpeeds.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / typingSpeeds.length
    );

    // Check for suspicious patterns
    const isCurrentlySuspicious = variance < 5 || avg < 50;

    if (isCurrentlySuspicious) {
        suspiciousCount++;
        if (suspiciousCount >= 3) { // Require 3 consecutive suspicious patterns
            sendBehaviorData(avg, 0);
        }
    } else {
        // Reset suspicious count if normal behavior is detected
        if (suspiciousCount > 0) {
            suspiciousCount = 0;
            // Send normal behavior data only when status changes
            const avgScrollSpeed = scrollSpeeds.length > 0 ? scrollSpeeds.reduce((a, b) => a + b, 0) / scrollSpeeds.length : 0;
            sendBehaviorData(avg, avgScrollSpeed);
        }
    }
}

// Send behavior data to server
function sendBehaviorData(typingSpeed, scrollSpeed) {
    fetch('/api/behavior', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            typing_speed: typingSpeed,
            scroll_speed: scrollSpeed,
            suspicious_count: suspiciousCount,
            paste_count: pasteCount,
            is_logout: false
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.prediction === 'Bot' && !botDetected) {
            botDetected = true;
            alert("Bot behavior detected. You will be logged out for security reasons.");
            window.location.href = '/logout';
        }
    })
    .catch(error => console.error('Error:', error));
}

// Start the timer when the page loads
startTimer();