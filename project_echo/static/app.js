let scrapedAudience = []; // Holds the result of a scrape before saving
let currentAccount = null; // Holds the account being edited

document.addEventListener('DOMContentLoaded', () => {
    // Load the dashboard by default
    switchSection('dashboard');
});

// --- Page & Section Navigation ---

function switchSection(sectionId) {
    // Hide all content sections and remove active class from sidebar items
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar nav li').forEach(i => i.classList.remove('active'));

    // Show the target section and set the corresponding sidebar item to active
    document.getElementById(sectionId)?.classList.add('active');
    document.getElementById(`nav-${sectionId}`)?.classList.add('active');

    // Based on the section, load the necessary data
    if (sectionId === 'accounts') loadAccounts();
    if (sectionId === 'audiences') { loadAccountsForScraper(); loadAndDisplayAudiences(); }
    if (sectionId === 'campaigns') { loadCampaigns(); loadAccountsForCampaign(); loadAndDisplayAudiences(); }
    if (sectionId === 'resources') { 
        // Default to the proxies tab when opening resources
        openResourceTab({ currentTarget: document.querySelector('#resources .tab-link[onclick*="proxies"]') }, 'proxies');
        loadProxies(); 
        loadTags(); 
    }
}

function openSettingsTab(evt, tabName) {
    document.querySelectorAll('#account-settings .tab-content').forEach(tc => tc.classList.remove('active'));
    document.querySelectorAll('#account-settings .tab-link').forEach(tl => tl.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    evt.currentTarget.classList.add('active');
}

function openResourceTab(evt, tabName) {
    document.querySelectorAll('#resources .resource-tab-content').forEach(tc => tc.classList.remove('active'));
    document.querySelectorAll('#resources .tab-link').forEach(tl => tl.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    evt.currentTarget.classList.add('active');
}

function showAccountSettingsPage(account) {
    currentAccount = account; // Store the account object
    switchSection('account-settings'); // Switch to the settings view
    document.getElementById('settings-account-display-phone').innerText = account.phone;
    document.getElementById('settings-account-phone').value = account.phone;

    // Reset and populate forms
    openSettingsTab({ currentTarget: document.querySelector('#account-settings .tab-link[onclick*="main-settings"]') }, 'main-settings');
    
    const settings = account.settings || {};
    const profile = settings.profile || {};
    document.getElementById('account-first-name').value = profile.first_name || '';
    document.getElementById('account-last-name').value = profile.last_name || '';
    document.getElementById('account-bio').value = profile.bio || '';
    
    const avatarPreview = document.getElementById('avatar-preview');
    if (profile.avatar_path && profile.avatar_path !== 'None') {
        avatarPreview.src = `/uploads/${profile.avatar_path.split('/').pop()}`;
        avatarPreview.style.display = 'block';
    } else {
        avatarPreview.style.display = 'none';
    }

    document.getElementById('account-user-agent-input').value = settings.user_agent || '';
    
    // Populate proxy and tag selectors
    populateProxyDropdown(settings.proxy ? settings.proxy.id : null);
    populateTagSelector(settings.tags || []);
}

function showMainAccountsPage() {
    currentAccount = null; // Clear the current account
    switchSection('accounts');
}

// --- Generic Helper ---
function apiPost(endpoint, body, callback) {
    fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message || data.status);
        if (callback) callback(data);
    })
    .catch(error => {
        console.error(`Error with ${endpoint}:`, error);
        alert(`An error occurred. Check the console for details.`);
    });
}

// --- Accounts Center ---

function loadAccounts() {
    fetch('/api/accounts').then(r => r.json()).then(accounts => {
        const tableBody = document.getElementById('accounts-table-body');
        tableBody.innerHTML = '';
        accounts.forEach(acc => {
            const tagsHtml = (acc.settings?.tags || []).map(t => `<span class="tag">${t}</span>`).join(' ');
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${acc.phone}</td>
                <td>${acc.username || 'N/A'}</td>
                <td>${tagsHtml}</td>
                <td>
                    <button onclick='showAccountSettingsPage(${JSON.stringify(acc)})'>Settings</button>
                    <button class="delete-btn" onclick="deleteAccount('${acc.phone}')">Delete</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    });
}

function addAccount() {
    const phone = prompt('Enter phone number (e.g., +1234567890):');
    if (!phone) return;

    apiPost('/api/accounts/add', { phone }, data => {
        if (data.message.includes('Verification code sent')) {
            const code = prompt('Enter verification code:');
            if (code) {
                apiPost('/api/accounts/finalize', { phone, code }, finalizeData => {
                     if (finalizeData.message.includes('password required')) {
                        const password = prompt('Enter 2FA password:');
                        if(password) apiPost('/api/accounts/finalize', { phone, password }, () => loadAccounts());
                    } else {
                        loadAccounts();
                    }
                });
            }
        } else if (data.message.includes('password required')) {
             const password = prompt('Enter 2FA password:');
             if(password) apiPost('/api/accounts/finalize', { phone, password }, () => loadAccounts());
        } else {
             loadAccounts();
        }
    });
}

function deleteAccount(phone) {
    if (confirm(`Are you sure you want to delete account ${phone}? This will also delete the session file.`)) {
        apiPost('/api/accounts/delete', { phone }, () => loadAccounts());
    }
}

// --- Account Settings ---

function handleAvatarUpload() {
    const input = document.getElementById('avatar-upload-input');
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('avatar', file);

    fetch('/api/accounts/upload_avatar', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            document.getElementById('account-avatar-path').value = data.path;
            const avatarPreview = document.getElementById('avatar-preview');
            avatarPreview.src = URL.createObjectURL(file);
            avatarPreview.style.display = 'block';
            alert('Avatar uploaded. Click "Save Settings" to keep the link, or "Apply to Telegram" to update your profile now.');
        } else {
            alert(`Upload failed: ${data.message}`);
        }
    });
}

function generateUserAgent() {
    const os = document.getElementById('ua-os').value;
    const chromeVersion = document.getElementById('ua-chrome-version').value;
    // This is a simplified template. A real-world generator would be more complex.
    const userAgent = `Mozilla/5.0 (${os}; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion} Safari/537.36`;
    document.getElementById('account-user-agent-input').value = userAgent;
}

async function saveAccountSettings() {
    if (!currentAccount) return alert('No account selected.');

    const phone = currentAccount.phone;
    
    const selectedProxyId = document.getElementById('account-proxy-select').value;
    const selectedTags = Array.from(document.querySelectorAll('#account-tags-selector input:checked')).map(i => i.value);

    // Fetch the full proxy object from the server
    const proxiesResponse = await fetch('/api/proxies');
    const proxies = await proxiesResponse.json();
    const selectedProxy = proxies.find(p => p.id === selectedProxyId) || null;

    const settings = {
        profile: {
            first_name: document.getElementById('account-first-name').value,
            last_name: document.getElementById('account-last-name').value,
            bio: document.getElementById('account-bio').value,
            avatar_path: document.getElementById('account-avatar-path').value,
        },
        user_agent: document.getElementById('account-user-agent-input').value,
        proxy: selectedProxy,
        tags: selectedTags
    };

    apiPost('/api/accounts/settings', { phone, settings }, (data) => {
        if (data.status === 'ok') {
            // Update the currentAccount object to reflect the changes immediately in the UI
            currentAccount.settings = settings;
        }
    });
}

function applyProfileChanges() {
     if (!currentAccount) return alert('No account selected.');
     const phone = currentAccount.phone;
     const profile = {
        first_name: document.getElementById('account-first-name').value,
        last_name: document.getElementById('account-last-name').value,
        bio: document.getElementById('account-bio').value,
        avatar_path: document.getElementById('account-avatar-path').value,
    };
    apiPost('/api/accounts/profile', { phone, profile });
}

async function populateProxyDropdown(selectedProxyId) {
    const select = document.getElementById('account-proxy-select');
    select.innerHTML = '<option value="">No Proxy</option>';
    try {
        const response = await fetch('/api/proxies');
        const proxies = await response.json();
        proxies.forEach(p => {
            const isSelected = p.id === selectedProxyId ? ' selected' : '';
            select.innerHTML += `<option value="${p.id}"${isSelected}>${p.host}:${p.port}</option>`;
        });
    } catch (error) { console.error("Couldn't load proxies for dropdown:", error); }
}

async function populateTagSelector(selectedTags) {
    const container = document.getElementById('account-tags-selector');
    container.innerHTML = '';
    try {
        const response = await fetch('/api/tags');
        const allTags = await response.json();
        allTags.forEach(tag => {
            const isChecked = selectedTags.includes(tag) ? ' checked' : '';
            container.innerHTML += `<label class="checkbox-label"><input type="checkbox" value="${tag}"${isChecked}> ${tag}</label>`;
        });
    } catch(error) { console.error("Couldn't load tags for selector:", error); }
}

// --- Audience CRM ---
function loadAccountsForScraper() {
    const select = document.getElementById('scraper-account');
    select.innerHTML = '<option disabled selected>Select account for scraping</option>';
    fetch('/api/accounts').then(r => r.json()).then(accounts => {
        accounts.forEach(acc => {
            select.innerHTML += `<option value="${acc.phone}">${acc.phone} (${acc.username || 'N/A'})</option>`;
        });
    });
}

function scrapeAudience() { /* Stub */ alert('Scraping not implemented in this version.'); }
function saveAudience() { /* Stub */ alert('Saving not implemented in this version.'); }
function loadAndDisplayAudiences() { /* Stub */ }

// --- Ad Cabinet ---
function loadCampaigns() { /* Stub */ document.getElementById('campaigns-table-body').innerHTML = ''; }
function toggleCampaignForm(show) { /* Stub */ alert('Campaign form not implemented in this version.'); }
function loadAccountsForCampaign() { /* Stub */ document.getElementById('campaign-accounts-select').innerHTML = ''; }
function saveCampaign() { /* Stub */ alert('Saving campaign not implemented in this version.'); }

// --- Resource Management (Proxies & Tags) ---

function loadProxies() {
    fetch('/api/proxies').then(r => r.json()).then(proxies => {
        const tableBody = document.getElementById('proxies-table-body');
        tableBody.innerHTML = '';
        if (!proxies) return;
        proxies.forEach(p => {
            const row = document.createElement('tr');
            row.id = `proxy-${p.id}`;
            row.innerHTML = `
                <td>${p.host}</td>
                <td>${p.port}</td>
                <td>${p.user || 'N/A'}</td>
                <td class="proxy-status">Not Checked</td>
                <td>
                    <button class="check-btn" onclick="checkProxy('${p.id}')">Check</button>
                    <button class="delete-btn" onclick="deleteProxy('${p.id}')">Delete</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }).catch(e => console.error('Failed to load proxies:', e));
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

    apiPost('/api/proxies/add', proxyData, (data) => {
        if (data.status === 'ok') {
            loadProxies();
            // Clear form
            document.getElementById('proxy-add-host').value = '';
            document.getElementById('proxy-add-port').value = '';
            document.getElementById('proxy-add-user').value = '';
            document.getElementById('proxy-add-pass').value = '';
        }
    });
}

function deleteProxy(proxyId) {
    if (!confirm('Are you sure you want to delete this proxy?')) return;
    apiPost('/api/proxies/delete', { id: proxyId }, (data) => {
        if (data.status === 'ok') loadProxies();
    });
}

async function checkProxy(proxyId) {
    const row = document.getElementById(`proxy-${proxyId}`);
    if (!row) return;
    const statusCell = row.querySelector('.proxy-status');
    statusCell.innerText = 'Checking...';

    // We need the full proxy object to check it.
    const proxiesResponse = await fetch('/api/proxies');
    const proxies = await proxiesResponse.json();
    const proxyToCheck = proxies.find(p => p.id === proxyId);

    if (!proxyToCheck) return statusCell.innerText = 'Error: Not Found';

    apiPost('/api/proxies/check', proxyToCheck, (data) => {
        statusCell.innerText = data.proxy_status || 'Error';
        if(data.proxy_status === 'working') {
            statusCell.style.color = 'green';
        } else {
            statusCell.style.color = 'red';
        }
    });
}

function loadTags() {
    fetch('/api/tags').then(r => r.json()).then(tags => {
        const container = document.getElementById('tags-list');
        container.innerHTML = '';
        if (!tags) return;
        tags.forEach(tag => {
            const tagEl = document.createElement('div');
            tagEl.className = 'tag-item';
            tagEl.innerHTML = `<span>${tag}</span><button onclick="deleteTag('${tag}')">&times;</button>`;
            container.appendChild(tagEl);
        });
    }).catch(e => console.error('Failed to load tags:', e));
}

function addTag() {
    const nameInput = document.getElementById('tag-add-name');
    const name = nameInput.value.trim();
    if (!name) return;
    apiPost('/api/tags/add', { name }, (data) => {
        if (data.status === 'ok') {
            loadTags();
            nameInput.value = '';
        }
    });
}

function deleteTag(tagName) {
    if (!confirm(`Are you sure you want to delete the tag "${tagName}"?`)) return;
    apiPost('/api/tags/delete', { name: tagName }, (data) => {
        if (data.status === 'ok') {
            loadTags();
            // Also refresh account settings if we are viewing an account that has this tag
            if(currentAccount) {
               populateTagSelector(currentAccount.settings.tags.filter(t => t !== tagName));
            }
        }
    });
}
