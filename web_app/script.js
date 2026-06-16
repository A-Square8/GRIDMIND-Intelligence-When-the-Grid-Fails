const chatContainer = document.getElementById("chat_container");
const userInput = document.getElementById("user_input");
const sendBtn = document.getElementById("send_btn");
const clearBtn = document.getElementById("clear_btn");
const topKInput = document.getElementById("top_k");
const newSessionBtn = document.getElementById("new_session_btn");
const confidenceBadge = document.getElementById("confidence_badge");
const sidebarToggle = document.getElementById("sidebar_toggle");
const sidebar = document.getElementById("sidebar");
const plannerBtn = document.getElementById("planner_btn");
const plannerContainer = document.getElementById("planner_container");
const plannerCloseBtn = document.getElementById("planner_close_btn");
const generatePlanBtn = document.getElementById("generate_plan_btn");
const situationInput = document.getElementById("situation_input");
const planDisplay = document.getElementById("plan_display");
const conversationList = document.getElementById("conversation_list");

let currentMeta = null;


function addMessage(content, isUser) {
    const div = document.createElement("div");
    div.className = "message " + (isUser ? "user" : "assistant");
    div.textContent = content;
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return div;
}


async function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;

    userInput.value = "";
    addMessage(text, true);

    const responseDiv = document.createElement("div");
    responseDiv.className = "message assistant";

    const statusDiv = document.createElement("div");
    statusDiv.className = "system-status";
    statusDiv.textContent = "[SYS] Analyzing vectors...";
    responseDiv.appendChild(statusDiv);

    const contentDiv = document.createElement("div");
    responseDiv.appendChild(contentDiv);
    chatContainer.appendChild(responseDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const top_k = parseInt(topKInput.value);
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, top_k }),
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        statusDiv.textContent = "[SYS] Streaming output...";

        let fullText = "";
        let metaParsed = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            fullText += decoder.decode(value, { stream: true });

            if (!metaParsed && fullText.includes("__META_END__\n")) {
                const metaEndIdx = fullText.indexOf("__META_END__\n") + "__META_END__\n".length;
                const metaBlock = fullText.substring(0, metaEndIdx);
                fullText = fullText.substring(metaEndIdx);
                metaParsed = true;

                try {
                    const jsonStr = metaBlock.replace("__META__:", "").replace("__META_END__\n", "");
                    const metaObj = JSON.parse(jsonStr);
                    currentMeta = metaObj;
                    updateStatusDisplay(statusDiv, metaObj);
                    updateConfidenceBadge(metaObj.confidence);
                    updateUrgencyTheme(metaObj.urgency);
                } catch (e) {
                    console.error("Meta parse error", e);
                }
            }

            if (metaParsed) {
                contentDiv.innerHTML = marked.parse(fullText);
            }
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    } catch (err) {
        statusDiv.textContent = "[ERR] Connection failed";
        contentDiv.textContent = err.message;
    }

    loadConversations();
}


function updateStatusDisplay(statusDiv, meta) {
    let html = "[SYS] Stream complete.";
    html += '<br><span class="meta-mode">MODE:</span> ' + meta.mode;
    html += ' | <span class="meta-urgency-' + meta.urgency + '">URGENCY: ' + meta.urgency + "</span>";

    if (meta.confidence && meta.confidence !== "PASS") {
        html += ' | <span class="meta-urgency-HIGH">CONFIDENCE: ' + meta.confidence + "</span>";
    }

    if (meta.procedures_matched > 0) {
        html += " | PROCEDURES: " + meta.procedures_matched;
    }

    if (meta.concepts_linked) {
        html += " | CONCEPTS: linked";
    }

    statusDiv.innerHTML = html;
}


function updateConfidenceBadge(confidence) {
    confidenceBadge.className = "confidence-badge";
    if (confidence === "PASS") {
        confidenceBadge.className += " pass";
        confidenceBadge.textContent = "HIGH CONFIDENCE";
    } else if (confidence === "LOW_CONFIDENCE") {
        confidenceBadge.className += " low";
        confidenceBadge.textContent = "LOW CONFIDENCE";
    } else if (confidence === "NO_MATCH") {
        confidenceBadge.className += " none";
        confidenceBadge.textContent = "NO MATCH";
    }
}


function updateUrgencyTheme(urgency) {
    const main = document.querySelector(".main");
    main.classList.remove("urgency-border-HIGH", "urgency-border-MEDIUM");
    if (urgency === "HIGH") {
        main.classList.add("urgency-border-HIGH");
    } else if (urgency === "MEDIUM") {
        main.classList.add("urgency-border-MEDIUM");
    }
}


sendBtn.addEventListener("click", handleSend);

userInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSend();
    } else if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});

document.addEventListener("keydown", function (e) {
    if (e.ctrlKey && e.key === "k") {
        e.preventDefault();
        clearMemory();
    }
    if (e.ctrlKey && e.key === "n") {
        e.preventDefault();
        newSession();
    }
});


clearBtn.addEventListener("click", clearMemory);

async function clearMemory() {
    await fetch("/api/clear_memory", { method: "POST" });
    chatContainer.innerHTML = "";
    addMessage("[SYS] Memory and database history cleared.", false);
    loadConversations();
}

const clearCacheBtn = document.getElementById("clear_cache_btn");
if (clearCacheBtn) {
    clearCacheBtn.addEventListener("click", async function() {
        await fetch("/api/clear_cache", { method: "POST" });
        addMessage("[SYS] Semantic cache cleared.", false);
        fetchStats();
    });
}


newSessionBtn.addEventListener("click", newSession);

async function newSession() {
    await fetch("/api/conversations/new", { method: "POST" });
    chatContainer.innerHTML = "";
    confidenceBadge.className = "confidence-badge";
    document.querySelector(".main").classList.remove("urgency-border-HIGH", "urgency-border-MEDIUM");
    addMessage("[SYS] New session started.", false);
    loadConversations();
}


document.querySelectorAll(".prompt-chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
        userInput.value = this.dataset.prompt;
        userInput.focus();
    });
});


sidebarToggle.addEventListener("click", function () {
    sidebar.classList.toggle("open");
    sidebar.classList.toggle("collapsed");
});


async function loadConversations() {
    try {
        const res = await fetch("/api/conversations");
        const conversations = await res.json();
        conversationList.innerHTML = "";

        conversations.forEach(function (conv) {
            const item = document.createElement("div");
            item.className = "conv-item";
            item.textContent = conv.title || "Untitled";
            item.title = conv.title || "Untitled";
            item.addEventListener("click", function () {
                loadConversation(conv.id);
            });
            conversationList.appendChild(item);
        });
    } catch (e) {
        console.error("Failed to load conversations", e);
    }
}


async function loadConversation(conversationId) {
    try {
        const res = await fetch("/api/conversations/load", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ conversation_id: conversationId }),
        });
        const data = await res.json();

        chatContainer.innerHTML = "";

        if (data.messages) {
            data.messages.forEach(function (msg) {
                const div = document.createElement("div");
                div.className = "message " + (msg.role === "user" ? "user" : "assistant");
                if (msg.role === "assistant") {
                    div.innerHTML = marked.parse(msg.content);
                } else {
                    div.textContent = msg.content;
                }
                chatContainer.appendChild(div);
            });
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        document.querySelectorAll(".conv-item").forEach(function (item) {
            item.classList.remove("active");
        });
    } catch (e) {
        console.error("Failed to load conversation", e);
    }
}


plannerBtn.addEventListener("click", function () {
    const chatVisible = chatContainer.style.display !== "none";
    if (chatVisible) {
        chatContainer.style.display = "none";
        document.getElementById("quick_prompts").style.display = "none";
        plannerContainer.style.display = "block";
        loadActivePlan();
    }
});

plannerCloseBtn.addEventListener("click", function () {
    plannerContainer.style.display = "none";
    chatContainer.style.display = "flex";
    document.getElementById("quick_prompts").style.display = "flex";
});

generatePlanBtn.addEventListener("click", async function () {
    const situation = situationInput.value.trim();
    if (!situation) return;

    generatePlanBtn.textContent = "GENERATING...";
    generatePlanBtn.disabled = true;

    try {
        const res = await fetch("/api/planner/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ situation }),
        });
        const plan = await res.json();
        renderPlan(plan);
    } catch (e) {
        planDisplay.innerHTML = '<div class="message">[ERR] Plan generation failed: ' + e.message + "</div>";
    }

    generatePlanBtn.textContent = "GENERATE PLAN";
    generatePlanBtn.disabled = false;
});


async function loadActivePlan() {
    try {
        const res = await fetch("/api/planner/active");
        const data = await res.json();
        if (data.tasks) {
            renderPlan(data);
            document.getElementById("planner_input_area").style.display = "none";
        }
    } catch (e) {
        console.error("Failed to load active plan", e);
    }
}


function renderPlan(plan) {
    if (!plan || !plan.tasks) {
        planDisplay.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 40px;">No active plan. Describe your situation above to generate one.</div>';
        return;
    }

    planDisplay.innerHTML = "";

    plan.tasks.forEach(function (task, index) {
        const taskEl = document.createElement("div");
        taskEl.className = "plan-task" + (task.status === "done" ? " done" : "");

        const checkbox = document.createElement("div");
        checkbox.className = "task-checkbox";
        checkbox.textContent = task.status === "done" ? "x" : "";
        checkbox.addEventListener("click", function () {
            toggleTask(index, task.status === "done" ? "pending" : "done");
        });

        const content = document.createElement("div");
        content.className = "task-content";

        const header = document.createElement("div");
        header.className = "task-header";
        header.innerHTML = '<span class="task-priority ' + task.priority + '">' + task.priority + "</span>" + '<span class="task-time">' + (task.time_window || "") + "</span>";

        const name = document.createElement("div");
        name.className = "task-name";
        name.textContent = task.task;

        const details = document.createElement("div");
        details.className = "task-details";
        details.textContent = task.details;

        content.appendChild(header);
        content.appendChild(name);
        content.appendChild(details);

        if (task.requires && task.requires.length > 0) {
            const requires = document.createElement("div");
            requires.className = "task-requires";
            requires.textContent = "Requires: " + task.requires.join(", ");
            content.appendChild(requires);
        }

        taskEl.appendChild(checkbox);
        taskEl.appendChild(content);
        planDisplay.appendChild(taskEl);
    });
}


async function toggleTask(index, status) {
    try {
        const res = await fetch("/api/planner/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_index: index, status }),
        });
        const plan = await res.json();
        if (plan.tasks) {
            renderPlan(plan);
        }
    } catch (e) {
        console.error("Failed to update task", e);
    }
}


async function fetchStats() {
    try {
        const res = await fetch("/api/system/stats");
        const stats = await res.json();

        const ollamaEl = document.getElementById("stat_ollama");
        if (stats.ollama_status === true) {
            ollamaEl.textContent = "ONLINE";
            ollamaEl.className = "stat-value online";
        } else {
            ollamaEl.textContent = "OFFLINE";
            ollamaEl.className = "stat-value offline";
        }

        document.getElementById("stat_uptime").textContent = stats.uptime_human || "--";
        document.getElementById("stat_ram").textContent = stats.ram_mb ? stats.ram_mb + " MB" : "--";
        document.getElementById("stat_cache").textContent = stats.cache_size !== undefined ? stats.cache_size + " entries" : "--";
        document.getElementById("stat_queries").textContent = stats.total_queries !== undefined ? stats.total_queries : "--";
    } catch (e) {
        document.getElementById("stat_ollama").textContent = "ERR";
        document.getElementById("stat_ollama").className = "stat-value offline";
    }
}


fetchStats();
loadConversations();
setInterval(fetchStats, 30000);
setInterval(loadConversations, 60000);
