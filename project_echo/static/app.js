let scrapedAudience = [];

document.addEventListener('DOMContentLoaded', () => {
    switchSection('dashboard');
});

// --- Page & Section Navigation ---
function switchSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar nav li').forEach(i => i.classList.remove('active'));

    document.getElementById(sectionId)?.classList.add('active');
    document.getElementById(`nav-${sectionId}`)?.classList.add('active');

    if (sectionId === 'accounts') loadAccounts();
    if (sectionId === 'audiences') { loadAccountsForScraper(); loadAndDisplayAudiences(); }
    if (sectionId === 'campaigns') { loadCampaigns(); loadAccountsForCampaign(); loadAndDisplayAudiences(); }
    if (sectionId === 'resources') { openResourceTab({ currentTarget: document.querySelector('#resources .tab-link') }, 'proxies'); loadProxies(); loadTags(); }

    const mainSections = ['dashboard', 'accounts', 'audiences', 'campaigns', 'resources', 'tasks', 'settings'];
    if (mainSections.includes(sectionId)) {
        document.getElementById('account-settings').style.display = 'none';
        const sectionToShow = document.getElementById(sectionId);
        if (sectionToShow) sectionToShow.style.display = 'block';
    }
}

function openResourceTab(evt, tabName) {
    document.querySelectorAll('.resource-tab-content').forEach(tc => tc.classList.remove('active'));
    document.querySelectorAll('#resources .tab-link').forEach(tl => tl.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    evt.currentTarget.classList.add('active');
}


function showAccountSettingsPage(account) {
    ['accounts', 'dashboard', 'audiences', 'campaigns', 'resources'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    document.getElementById('account-settings').style.display = 'block';
    openAccountSettings(account);
}

function showMainAccountsPage() {
    document.getElementById('account-settings').style.display = 'none';
    switchSection('accounts');
}

// --- Resource Management (Proxies & Tags) ---
function loadProxies() {
    fetch('/api/proxies').then(r => r.json()).then(proxies => {
        const tableBody = document.getElementById('proxies-table-body');
        tableBody.innerHTML = '';
        proxies.forEach(p => {
            tableBody.innerHTML += `<tr id="proxy-${p.id}">
                <td>${p.host}</td>
                <td>${p.port}</td>
                <td>${p.user || 'N/A'}</td>
                <td class="proxy-status">Not Checked</td>
                <td>
                    <button class="check-btn" onclick="checkProxy('${p.id}')">Check</button>
                    <button class="delete-btn" onclick="deleteProxy('${p.id}')">Delete</button>
                </td>
            </tr>`;
        });
    });
}

function addProxy() {
    const proxyData = {
        type: document.getElementById('proxy-add-type').value,
        host: document.getElementById('proxy-add-host').value,
        port: parseInt(document.getElementById('proxy-add-port').value, 10),
        user: document.getElementById('proxy-add-user').value,
        pass: document.getElementById('proxy-add-pass').value
    };
    if (!proxyData.host || !proxyData.port) return alert('Host and Port are required.');

    fetch('/api/proxies/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(proxyData) })
        .then(r => r.json()).then(data => { alert(data.message); if (data.status === 'ok') loadProxies(); });
}

function deleteProxy(proxyId) {
    if (!confirm('Delete this proxy?')) return;
    fetch('/api/proxies/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: proxyId }) })
        .then(r => r.json()).then(data => { alert(data.message); if (data.status === 'ok') loadProxies(); });
}

function checkProxy(proxyId) {
    const row = document.getElementById(`proxy-${proxyId}`);
    const statusCell = row.querySelector('.proxy-status');
    statusCell.innerText = 'Checking...';
    const proxy = {
        id: proxyId,
        type: row.cells[0].innerText, // Reconstruct from table for check
        host: row.cells[0].innerText,
        port: parseInt(row.cells[1].innerText, 10),
        user: row.cells[2].innerText === 'N/A' ? '' : row.cells[2].innerText,
        pass: '' // Pass is not stored in table, not needed for check either
    };

    fetch('/api/proxies/check', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(proxy) })
    .then(r => r.json()).then(data => { statusCell.innerText = data.proxy_status; });
}

function loadTags() {
    fetch('/api/tags').then(r => r.json()).then(tags => {
        const container = document.getElementById('tags-list');
        container.innerHTML = '';
        tags.forEach(tag => {
            container.innerHTML += `<div class="tag-item"><span>${tag}</span><button onclick="deleteTag('${tag}')">&times;</button></div>`;
        });
    });
}

function addTag() {
    const name = document.getElementById('tag-add-name').value;
    if (!name) return;
    fetch('/api/tags/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
        .then(r => r.json()).then(data => { alert(data.message); if (data.status === 'ok') { loadTags(); document.getElementById('tag-add-name').value = ''; } });
}

function deleteTag(tagName) {
    if (!confirm(`Delete tag "${tagName}"?`)) return;
    fetch('/api/tags/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: tagName }) })
        .then(r => r.json()).then(data => { alert(data.message); if (data.status === 'ok') loadTags(); });
}


// --- Account Settings Logic ---
async function openAccountSettings(account) {
    // ... (rest of the function)
    await populateProxyDropdown(account.settings?.proxy?.id);
    await populateTagSelector(account.settings?.tags || []);
}

async function populateProxyDropdown(selectedProxyId) {
    const select = document.getElementById('account-proxy-select');
    select.innerHTML = '<option value="">No Proxy</option>';
    const response = await fetch('/api/proxies');
    const proxies = await response.json();
    proxies.forEach(p => {
        const isSelected = p.id === selectedProxyId ? ' selected' : '';
        select.innerHTML += `<option value="${p.id}"${isSelected}>${p.host}:${p.port}</option>`;
    });
}

async function populateTagSelector(selectedTags) {
    const container = document.getElementById('account-tags-selector');
    container.innerHTML = '';
    const response = await fetch('/api/tags');
    const allTags = await response.json();
    allTags.forEach(tag => {
        const isChecked = selectedTags.includes(tag) ? ' checked' : '';
        container.innerHTML += `<label><input type="checkbox" value="${tag}"${isChecked}> ${tag}</label>`;
    });
}

function saveAccountSettings() {
    const phone = document.getElementById('settings-account-phone').value;
    const selectedProxyId = document.getElementById('account-proxy-select').value;
    const selectedTags = Array.from(document.querySelectorAll('#account-tags-selector input:checked')).map(i => i.value);

    // Find the full proxy object by its ID
    fetch('/api/proxies').then(r => r.json()).then(proxies => {
        const selectedProxy = proxies.find(p => p.id === selectedProxyId) || null;

        const settings = {
            // ... (profile and user-agent settings)
            proxy: selectedProxy,
            tags: selectedTags
        };

        fetch('/api/accounts/settings', { /* ... POST request ... */ });
    });
}
// --- The rest of app.js remains largely the same... ---
