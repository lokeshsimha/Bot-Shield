const socket = io();

document.addEventListener('DOMContentLoaded', function () {
    const body = document.body;

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        body.classList.add('dark-theme');
    }
});

let totalSessions = 0;
let flaggedSessions = 0;

socket.on('new_behavior', (data) => {
    totalSessions++;
    if (data.status === 'Bot') flaggedSessions++;

    document.getElementById('totalSessions').textContent = totalSessions;
    document.getElementById('flaggedSessions').textContent = flaggedSessions;

    const tableBody = document.getElementById('activityTable');
    const row = document.createElement('tr');
    row.className = data.status.toLowerCase() === 'bot' ? 'activity-row-bot' : 'activity-row-human';
    row.innerHTML = `
        <td>${data.username}</td>
        <td>${data.typing_speed.toFixed(2)} ms/keystroke</td>
        <td>${data.scroll_speed ? data.scroll_speed.toFixed(2) : '0'} px/s</td>
        <td class="status-${data.status.toLowerCase()}">${data.status}</td>
        <td>${data.timestamp}</td>
    `;
    tableBody.insertBefore(row, tableBody.firstChild);
    if (tableBody.children.length > 10) tableBody.removeChild(tableBody.lastChild);

    updateStatusCard(data.status);
    document.getElementById('lastUpdate').textContent = `Last updated: ${new Date().toLocaleString()}`;
});

function updateStatusCard(status) {
    const detectionCard = document.getElementById('detectionCard');
    const statusIcon = document.getElementById('statusIcon');
    const botStatus = document.getElementById('botStatus');
    
    if (status.toLowerCase() === 'bot') {
        detectionCard.classList.remove('human-detected');
        detectionCard.classList.add('bot-detected');
        statusIcon.textContent = '🤖';
        botStatus.textContent = 'Bot Detected';
        botStatus.className = 'metric-value status-bot';
    } else {
        detectionCard.classList.remove('bot-detected');
        detectionCard.classList.add('human-detected');
        statusIcon.textContent = '👤';
        botStatus.textContent = 'Human User';
        botStatus.className = 'metric-value status-human';
    }
}

fetch('/api/dashboard')
    .then(response => response.json())
    .then(data => {
        totalSessions = data.total_sessions;
        flaggedSessions = data.flagged_sessions;
        
        document.getElementById('totalSessions').textContent = totalSessions;
        document.getElementById('flaggedSessions').textContent = flaggedSessions;
        document.getElementById('typingSpeed').textContent = `${data.average_typing_speed.toFixed(1)} ms/keystroke`;
        document.getElementById('scrollSpeed').textContent = `${data.average_scroll_speed.toFixed(1)} px/s`;

        const tableBody = document.getElementById('activityTable');
        data.recent_activities.forEach(activity => {
            const row = document.createElement('tr');
            row.className = activity.status.toLowerCase() === 'bot' ? 'activity-row-bot' : 'activity-row-human';
            row.innerHTML = `
                <td>${activity.username}</td>
                <td>${activity.typing_speed.toFixed(2)} ms/keystroke</td>
                <td>${activity.scroll_speed.toFixed(2)} px/s</td>
                <td class="status-${activity.status.toLowerCase()}">${activity.status}</td>
                <td>${activity.timestamp}</td>
            `;
            tableBody.appendChild(row);
        });

        updateStatusCard(data.recent_activities[0].status);
        document.getElementById('lastUpdate').textContent = `Last updated: ${new Date().toLocaleString()}`;
    })
    .catch(error => console.error('Error:', error));