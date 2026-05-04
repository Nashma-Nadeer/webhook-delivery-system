document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("webhook-form");
    const tbody = document.getElementById("tasks-body");
    const btn = document.getElementById("submit-btn");
    const statusMsg = document.getElementById("form-status");

    // Fetch and render tasks
    async function fetchTasks() {
        try {
            const res = await fetch("/api/tasks");
            const tasks = await res.json();
            renderTasks(tasks);
        } catch (err) {
            console.error("Failed to fetch tasks", err);
        }
    }

    // Fetch and render stats
    async function fetchStats() {
        try {
            const res = await fetch("/api/stats");
            const stats = await res.json();
            document.getElementById("stat-total").textContent = stats.total;
            document.getElementById("stat-success").textContent = stats.success;
            document.getElementById("stat-failed").textContent = stats.failed;
            document.getElementById("stat-retrying").textContent = stats.retrying;
        } catch (err) {
            console.error("Failed to fetch stats", err);
        }
    }

    function renderTasks(tasks) {
        tbody.innerHTML = "";
        tasks.forEach(task => {
            const tr = document.createElement("tr");
            
            // Format time
            const date = new Date(task.created_at);
            const timeStr = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
            
            // Shorten ID
            const shortId = task.task_id.substring(0, 8);

            // Shorten URL
            let shortUrl = task.target_url;
            if(shortUrl.length > 30) shortUrl = shortUrl.substring(0, 30) + "...";

            tr.innerHTML = `
                <td class="task-id">${shortId}</td>
                <td><span class="status-badge status-${task.status}">${task.status}</span></td>
                <td>${task.retry_count}</td>
                <td title="${task.target_url}">${shortUrl}</td>
                <td>${timeStr}</td>
            `;
            
            // Add a subtle entrance animation for new rows
            tr.style.animation = "fadeIn 0.5s ease";
            tbody.appendChild(tr);
        });
    }

    // Handle Form Submit
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const target_url = document.getElementById("target_url").value;
        const payloadStr = document.getElementById("payload").value;
        
        let payload;
        try {
            payload = JSON.parse(payloadStr);
        } catch (err) {
            showStatus("Invalid JSON payload", "error");
            return;
        }

        btn.disabled = true;
        btn.textContent = "Enqueueing...";

        try {
            const res = await fetch("/send-webhook", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target_url, payload })
            });
            
            if (res.ok) {
                showStatus("Task successfully queued!", "success");
                fetchTasks(); // instantly update table
            } else {
                const data = await res.json();
                showStatus(data.error || "Failed to queue task", "error");
            }
        } catch (err) {
            showStatus("Network error", "error");
        } finally {
            btn.disabled = false;
            btn.textContent = "Enqueue Task";
        }
    });

    function showStatus(msg, type) {
        statusMsg.textContent = msg;
        statusMsg.className = `status-msg ${type}`;
        setTimeout(() => {
            statusMsg.className = "status-msg hidden";
        }, 3000);
    }

    // Initial fetch and start polling every 2 seconds
    fetchTasks();
    fetchStats();
    setInterval(() => {
        fetchTasks();
        fetchStats();
    }, 2000);
});
