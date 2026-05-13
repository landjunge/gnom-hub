// Gnom-Hub Frontend Logic

const API_BASE = '/api'; // Assuming Nginx proxy or direct fetch if served via Hub

let port = 3002;

// In a real app we'd fetch the port from environment or a config endpoint.
// For this local prototype, we try to hit the API endpoints on localhost:PORT
async function discoverPort() {
    for (let p = 3002; p <= 3015; p++) {
        try {
            const res = await fetch(`http://127.0.0.1:${p}/api/stats`);
            if (res.ok) {
                port = p;
                console.log("Connected to Gnom-Hub on port", port);
                return;
            }
        } catch (e) {
            // port not active
        }
    }
    console.error("Could not find active Gnom-Hub port.");
}

async function apiCall(endpoint, options = {}) {
    try {
        const res = await fetch(`http://127.0.0.1:${port}/api${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        return await res.json();
    } catch (e) {
        console.error("API Error:", e);
        return null;
    }
}

function logActivity(msg) {
    const log = document.getElementById('activity-log');
    const li = document.createElement('li');
    li.innerHTML = `<span>${msg}</span>`;
    log.prepend(li);
    if(log.children.length > 5) log.removeChild(log.lastChild);
}

async function loadSystemStats() {
    const stats = await apiCall('/stats');
    if (stats) {
        document.getElementById('stat-agents').innerText = stats.total_agents;
        document.getElementById('stat-memory').innerText = stats.total_memories;
        
        // Update memory ring pseudo-calc
        const percent = Math.min(100, Math.round((stats.total_memories / 100) * 100)); // Just a mock calc
        document.getElementById('memory-percent').innerText = `${percent}%`;
        document.getElementById('memory-circle').setAttribute('stroke-dasharray', `${percent}, 100`);
        
        document.getElementById('mem-kb').innerText = stats.total_memories;
        document.getElementById('mem-sd').innerText = stats.total_agents * 2;
        document.getElementById('mem-ac').innerText = Math.floor(stats.total_memories * 0.4);
    }
}

async function loadAgents() {
    const container = document.getElementById('agents-container');
    const res = await apiCall('/agents');
    
    if (!res || !Array.isArray(res)) {
        container.innerHTML = '<div class="loading">Keine Agenten gefunden.</div>';
        return;
    }
    
    container.innerHTML = '';
    res.forEach(agent => {
        const isOnline = agent.status === 'online';
        
        let openUiBtn = "";
        const portMatch = agent.description && agent.description.match(/\b(\d{4,5})\b/);
        if (portMatch) {
            const agentPort = portMatch[1];
            openUiBtn = `<button class="btn-secondary" onclick="openAgentFrame('${agent.name}', 'http://127.0.0.1:${agentPort}')" style="margin-right: 5px;">Open UI</button>`;
        }
        
        const memoryBtn = `<button class="btn-secondary" onclick="viewAgentMemory('${agent.name}')" style="margin-right: 5px;">View Memory</button>`;
        
        const descText = agent.description ? agent.description : "Keine Details hinterlegt";

        const card = document.createElement('div');
        card.className = 'glass-card agent-card';
        card.innerHTML = `
            <div class="agent-header">
                <div class="agent-icon">🤖</div>
                <div class="status-badge ${isOnline ? 'online' : 'offline'}">${agent.status.toUpperCase()}</div>
            </div>
            <div>
                <h3 style="margin-bottom: 0.3rem">${agent.name}</h3>
                <div class="agent-stats" style="font-size: 0.85rem; color: #ccc;">${descText}</div>
            </div>
            <div class="agent-actions">
                ${openUiBtn}
                ${memoryBtn}
                <button class="btn-secondary" onclick="toggleAgentStatus('${agent.id}', '${agent.status}')">${isOnline ? 'Stop' : 'Start'}</button>
                <button class="btn-secondary" onclick="deleteAgent('${agent.id}')" style="color: #ff5252; border-color: #ff5252;">Delete</button>
            </div>
        `;
        container.appendChild(card);
    });
}

window.toggleAgentStatus = async (id, currentStatus) => {
    const newStatus = currentStatus === 'online' ? 'offline' : 'online';
    await apiCall(`/agents/${id}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus })
    });
    logActivity(`Agent ${id.substring(0,5)} set to ${newStatus}`);
    await refreshAll();
};

window.deleteAgent = async (id) => {
    if(confirm("Agent und sein gesamtes Memory löschen?")) {
        await apiCall(`/agents/${id}`, { method: 'DELETE' });
        logActivity(`Agent ${id.substring(0,5)} deleted`);
        await refreshAll();
    }
};

async function refreshAll() {
    await loadSystemStats();
    await loadAgents();
}

// Modal Logic
const modal = document.getElementById('modal-deploy');
document.getElementById('btn-deploy-agent').addEventListener('click', () => {
    modal.classList.add('active');
});

document.getElementById('btn-cancel-deploy').addEventListener('click', () => {
    modal.classList.remove('active');
});

document.getElementById('btn-confirm-deploy').addEventListener('click', async () => {
    const name = document.getElementById('new-agent-name').value;
    const desc = document.getElementById('new-agent-desc').value;
    
    if(!name) return alert("Name ist Pflicht!");
    
    const res = await apiCall('/agents', {
        method: 'POST',
        body: JSON.stringify({ name, description: desc })
    });
    
    if(res && res.id) {
        modal.classList.remove('active');
        document.getElementById('new-agent-name').value = '';
        document.getElementById('new-agent-desc').value = '';
        logActivity(`Deployed new agent: ${name}`);
        await refreshAll();
    } else {
        alert("Fehler! Möglicherweise existiert dieser Name bereits oder die Eingabe ist ungültig.");
    }
});

document.getElementById('btn-scan-network').addEventListener('click', async () => {
    logActivity('Scanning network & sockets...');
    const btn = document.getElementById('btn-scan-network');
    btn.innerText = 'Scanning...';
    btn.disabled = true;
    
    const res = await apiCall('/agents/scan');
    btn.innerText = 'Scan Network';
    btn.disabled = false;
    
    if (res && (res.open_ports || res.socket_files)) {
        const ports = res.open_ports || [];
        const sockets = res.socket_files || [];
        logActivity(`Found ${ports.length} ports, ${sockets.length} sockets.`);
        
        let html = "";
        if (ports.length > 0) html += `<strong style="color: #4CAF50;">Ports (TCP):</strong><br>${ports.join(', ')}<br><br>`;
        if (sockets.length > 0) {
            html += `<strong style="color: #2196F3;">Unix-Sockets:</strong><br>`;
            sockets.forEach(s => {
                html += `<span style="cursor:pointer; border-bottom: 1px dashed #fff;" title="Klicken zum Kopieren" onclick="navigator.clipboard.writeText('${s}').then(() => alert('Socket kopiert!'))">${s} 📋</span><br>`;
            });
        }
        if (ports.length === 0 && sockets.length === 0) html = "Keine aktiven Agenten-Schnittstellen gefunden.";
        
        document.getElementById('scan-results-content').innerHTML = html;
        document.getElementById('modal-scan').classList.add('active');
    } else {
        logActivity('Scan failed.');
    }
});

document.getElementById('btn-close-scan').addEventListener('click', () => {
    document.getElementById('modal-scan').classList.remove('active');
});

// Sidebar Navigation Logic
document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        
        // Update active class
        document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
        e.target.parentElement.classList.add('active');
        
        // Hide all views
        document.getElementById('view-dashboard').style.display = 'none';
        document.getElementById('view-memory').style.display = 'none';
        
        // Show target view
        const target = e.target.getAttribute('href');
        if (target === '#dashboard' || target === '#agents') {
            document.getElementById('view-dashboard').style.display = 'grid';
        } else if (target === '#memory') {
            document.getElementById('view-memory').style.display = 'block';
            loadMemory();
        }
    });
});

async function loadMemory(query = "") {
    const list = document.getElementById('memory-list');
    list.innerHTML = '<div class="loading">Lade Memories...</div>';
    
    // Fetch agents for name lookup
    const agents = await apiCall('/agents');
    const agentMap = {};
    if (agents && Array.isArray(agents)) {
        agents.forEach(a => agentMap[a.id] = a.name);
    }
    
    // Gnom-Hub search_memory API endpoint
    const res = await apiCall(`/memory/search?q=${encodeURIComponent(query)}`);
    
    if (!res || !Array.isArray(res) || res.length === 0) {
        list.innerHTML = '<div style="color:#ccc; padding:10px;">Der Memory-Stream ist noch leer.</div>';
        return;
    }
    
    list.innerHTML = '';
    res.forEach(mem => {
        const div = document.createElement('div');
        div.style.cssText = "background: rgba(255,255,255,0.05); padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 3px solid #f39c12;";
        
        const agentName = agentMap[mem.agent_id] || (mem.agent_id ? mem.agent_id.substring(0,8) + "..." : "Unknown");
        const date = new Date(mem.timestamp).toLocaleString();
        div.innerHTML = `
            <div style="font-size: 0.8rem; color: #aaa; margin-bottom: 5px; font-weight: bold;">
                <span style="color: #4CAF50;">[${agentName}]</span> | ${date}
            </div>
            <div style="white-space: pre-wrap; font-family: monospace; font-size: 0.9rem;">${mem.content}</div>
        `;
        list.appendChild(div);
    });
}

window.viewAgentMemory = (agentName) => {
    // Jump to memory tab and pre-fill search with agent name
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    document.querySelector('a[href="#memory"]').parentElement.classList.add('active');
    
    document.getElementById('view-dashboard').style.display = 'none';
    document.getElementById('view-agent-ui').style.display = 'none';
    document.getElementById('view-memory').style.display = 'block';
    
    const searchInput = document.getElementById('memory-search-input');
    searchInput.value = agentName;
    loadMemory(agentName);
};

window.openAgentFrame = (name, url) => {
    document.getElementById('view-dashboard').style.display = 'none';
    document.getElementById('view-memory').style.display = 'none';
    
    document.getElementById('agent-frame-title').innerText = `${name} Interface`;
    document.getElementById('agent-iframe').src = url;
    document.getElementById('view-agent-ui').style.display = 'block';
    
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
};

window.closeAgentFrame = () => {
    document.getElementById('agent-iframe').src = "";
    document.getElementById('view-agent-ui').style.display = 'none';
    document.getElementById('view-dashboard').style.display = 'grid';
    
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    document.querySelector('a[href="#dashboard"]').parentElement.classList.add('active');
};

document.getElementById('memory-search-input').addEventListener('input', (e) => {
    loadMemory(e.target.value);
});

// Init
(async function init() {
    await discoverPort();
    await refreshAll();
})();
