const API_URL = "";
const eventInput = document.getElementById("eventInput");
const simulateFailure = document.getElementById("simulateFailure");
const submitButton = document.getElementById("submitButton");
const submitResult = document.getElementById("submitResult");
const clientFilter = document.getElementById("clientFilter");

submitButton.addEventListener("click", submitEvent);
clientFilter.addEventListener("input", loadEvents);


async function submitEvent() {
    submitResult.textContent = "";

    let event;

    try {
        event = JSON.parse(eventInput.value);
    } catch {
        submitResult.textContent = "Invalid JSON.";
        submitResult.className = "error";
        return;
    }

    submitButton.disabled = true;

    try {
        const response = await fetch(`${API_URL}/events`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                event: event,
                simulate_failure: simulateFailure.checked
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Request failed");
        }

        submitResult.textContent =
            `${data.status}: ${data.message}`;

        submitResult.className =
            data.status === "processed"
                ? "success"
                : "";

        await refreshDashboard();

    } catch (error) {
        submitResult.textContent = error.message;
        submitResult.className = "error";

        await refreshDashboard();

    } finally {
        submitButton.disabled = false;
    }
}


async function loadEvents() {
    const client = clientFilter.value.trim();

    const url = client
        ? `${API_URL}/events?client_id=${encodeURIComponent(client)}`
        : `${API_URL}/events`;

    const response = await fetch(url);
    const events = await response.json();

    const container = document.getElementById("eventsList");

    if (events.length === 0) {
        container.textContent = "No processed events.";
        return;
    }

    container.innerHTML = events.map(event => `
        <div class="event">
            <strong>${escapeHtml(event.client_id)}</strong>
            <div>Metric: ${escapeHtml(event.metric)}</div>
            <div>Amount: ${event.amount}</div>
            <div>Timestamp: ${escapeHtml(event.timestamp)}</div>
        </div>
    `).join("");
}


async function loadAggregates() {
    const response = await fetch(`${API_URL}/aggregates`);
    const aggregates = await response.json();

    const container = document.getElementById("aggregatesList");

    if (aggregates.length === 0) {
        container.textContent = "No aggregate data.";
        return;
    }

    container.innerHTML = aggregates.map(item => `
        <div class="aggregate">
            <strong>${escapeHtml(item.client_id)}</strong>
            <div>Events: ${item.count}</div>
            <div>Total amount: ${item.total_amount}</div>
        </div>
    `).join("");
}


async function loadAttempts() {
    const response = await fetch(`${API_URL}/attempts`);
    const attempts = await response.json();

    const container = document.getElementById("attemptsList");

    if (attempts.length === 0) {
        container.textContent = "No attempts yet.";
        return;
    }

    container.innerHTML = attempts.map(attempt => `
        <div class="attempt">
            <span class="status">
                ${escapeHtml(attempt.status.toUpperCase())}
            </span>
            <div>Source: ${escapeHtml(attempt.source || "unknown")}</div>
            ${
                attempt.error_message
                    ? `<div class="error">
                        ${escapeHtml(attempt.error_message)}
                       </div>`
                    : ""
            }
            <small>${escapeHtml(attempt.created_at)}</small>
        </div>
    `).join("");

    updateStats(attempts);
}


function updateStats(attempts) {
    const counts = {
        processed: 0,
        failed: 0,
        duplicate: 0,
        rejected: 0
    };

    for (const attempt of attempts) {
        if (attempt.status in counts) {
            counts[attempt.status]++;
        }
    }

    document.getElementById("processedCount").textContent =
        counts.processed;

    document.getElementById("failedCount").textContent =
        counts.failed;

    document.getElementById("duplicateCount").textContent =
        counts.duplicate;

    document.getElementById("rejectedCount").textContent =
        counts.rejected;
}


async function refreshDashboard() {
    await Promise.all([
        loadEvents(),
        loadAggregates(),
        loadAttempts()
    ]);
}


function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}


refreshDashboard();