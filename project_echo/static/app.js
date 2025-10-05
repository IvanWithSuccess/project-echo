let currentAccount = null; // Holds the account object being edited
let scrapedAudience = []; // Holds the result of a scrape before saving

document.addEventListener('DOMContentLoaded', () => {
    // Set up initial state
    switchSection('dashboard');
    setupTabListeners();
});

function setupTabListeners() {
    const accountTabs = document.querySelector('#account-settings md-tabs');
    accountTabs.addEventListener('change', (event) => {
        const activeTabId = accountTabs.activeTab.id;
        document.querySelectorAll('#account-settings .tab-panel').forEach(p => p.classList.remove('active'));
        
        if (activeTabId === 'tab-main-settings') {
            document.getElementById('main-settings-panel').classList.add('active');
        } else if (activeTabId === 'tab-proxy-settings') {
            document.getElementById('proxy-settings-panel').classList.add('active');
        }
    });
}

// --- Page & Section Navigation ---

function switchSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(s => s.style.display = 'none');
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));

    const section = document.getElementById(sectionId);
    if(section) section.style.display = 'block';

    const navItem = document.getElementById(`nav-${sectionId}`) || document.getElementById(`nav-${sectionId.split('-')[0]}`);
    if(navItem) navItem.classList.add('active');

    // Load data for the activated section
    if (sectionId === 'accounts') loadAccounts();
    if (sectionId === 'proxies') loadProxies();
    if (sectionId === 'audiences') { 
        loadAccountsForScraper(); 
        loadAndDisplayAudiences();
    }
    if (sectionId === 'campaigns') {}
}

function showAccountSettingsPage(account) {
    currentAccount = account; 
    switchSection('account-settings'); 
    document.getElementById('settings-account-display-phone').innerText = account.phone;
    
    const settings = account.settings || {};
    const profile = settings.profile || {};

    // Populate Main Settings
    document.getElementById('account-first-name').value = profile.first_name || '';
    document.getElementById('account-last-name').value = profile.last_name || '';
    document.getElementById('account-bio').value = profile.bio || '';
    document.getElementById('account-user-agent-input').value = settings.user_agent || '';

    const avatarPreview = document.getElementById('avatar-preview');
    const avatarPathInput = document.getElementById('account-avatar-path');
    avatarPathInput.value = profile.avatar_path || '';
    if (profile.avatar_path && profile.avatar_path !== 'None') {
        avatarPreview.src = `/uploads/${profile.avatar_path.split('/').pop()}`;
        avatarPreview.style.display = 'block';
    } else {
        avatarPreview.style.display = 'none';
    }

    const accountTabs = document.querySelector('#account-settings md-tabs');
    accountTabs.activeTabIndex = 0;
    document.querySelectorAll('#account-settings .tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('main-settings-panel').classList.add('active');

    populateProxyDropdown(settings.proxy ? settings.proxy.id : null);
}

function showMainAccountsPage() {
    currentAccount = null;
    switchSection('accounts');
}

// --- Generic API Helper ---
function apiPost(endpoint, body, callback) {
    fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) {
             // Use the message from the server-side error
            throw new Error(data.message || `HTTP error! status: ${response.status}`);
        }
        return data;
    })
    .then(data => {
        if(data.message) alert(data.message);
        if (callback) callback(data);
    })
    .catch(error => {
        console.error(`API Error at ${endpoint}:`, error);
        alert(error.message);
    });
}


// --- Accounts Center ---

function loadAccounts() {
    fetch('/api/accounts').then(r => r.json()).then(accounts => {
        const tableBody = document.getElementById('accounts-table-body');
        tableBody.innerHTML = '';
        accounts.forEach(acc => {
            const tagsHtml = (acc.settings?.tags || []).map(t => `<div class="tag-chip">${t}</div>`).join('');
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${acc.phone}</td>
                <td>${acc.username || 'N/A'}</td>
                <td><div class="tag-chip-container">${tagsHtml}</div></td>
                <td>
                    <md-text-button onclick='showAccountSettingsPage(${JSON.stringify(acc).replace(/"/g, "&quot;")})'>Settings</md-text-button>
                    <md-text-button onclick="deleteAccount('${acc.phone}')">Delete</md-text-button>
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
        if (data.message.includes('code sent')) {
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
    if (confirm(`Delete account ${phone}? This also deletes the session file.`)) {
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
            alert('Avatar uploaded. Save settings to confirm.');
        } else {
            alert(`Upload failed: ${data.message}`);
        }
    });
}

function generateUserAgent() {
    const os = document.getElementById('ua-os').value;
    const chromeVersion = document.getElementById('ua-chrome-version').value;
    document.getElementById('account-user-agent-input').value = 
        `Mozilla/5.0 (${os}; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion} Safari/537.36`;
}

async function saveAccountSettings() {
    if (!currentAccount) return alert('No account selected.');

    const phone = currentAccount.phone;
    const proxySelect = document.getElementById('account-proxy-select');
    const selectedProxyId = proxySelect.value;
    
    const proxiesResponse = await fetch('/api/proxies');
    const proxies = await proxiesResponse.json();
    const selectedProxy = proxies.find(p => p.id === selectedProxyId) || null;

    const settings = {
        ...currentAccount.settings,
        profile: {
            first_name: document.getElementById('account-first-name').value,
            last_name: document.getElementById('account-last-name').value,
            bio: document.getElementById('account-bio').value,
            avatar_path: document.getElementById('account-avatar-path').value,
        },
        user_agent: document.getElementById('account-user-agent-input').value,
        proxy: selectedProxy,
    };

    apiPost('/api/accounts/settings', { phone, settings }, (data) => {
        if (data.status === 'ok') {
            currentAccount.settings = settings;
        }
    });
}

function applyProfileChanges() {
     if (!currentAccount) return alert('No account selected.');
     apiPost('/api/accounts/profile', {
         phone: currentAccount.phone,
         profile: {
            first_name: document.getElementById('account-first-name').value,
            last_name: document.getElementById('account-last-name').value,
            bio: document.getElementById('account-bio').value,
            avatar_path: document.getElementById('account-avatar-path').value,
        }
    });
}

async function populateProxyDropdown(selectedProxyId) {
    const select = document.getElementById('account-proxy-select');
    select.innerHTML = '<md-select-option value=""></md-select-option>'; 
    try {
        const response = await fetch('/api/proxies');
        const proxies = await response.json();
        proxies.forEach(p => {
            const option = document.createElement('md-select-option');
            option.value = p.id;
            option.innerText = `${p.host}:${p.port}`;
            if (p.id === selectedProxyId) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    } catch (error) { console.error("Couldn't load proxies for dropdown:", error); }
}

// --- Audience CRM ---
function loadAccountsForScraper() {
    const select = document.getElementById('scraper-account-select');
    select.innerHTML = '<md-select-option></md-select-option>';
    fetch('/api/accounts').then(r => r.json()).then(accounts => {
        accounts.forEach(acc => {
            const option = document.createElement('md-select-option');
            option.value = acc.phone;
            option.innerText = acc.phone + (acc.username ? ` (${acc.username})` : '');
            select.appendChild(option);
        });
    });
}

function scrapeAudience() {
    const phone = document.getElementById('scraper-account-select').value;
    const chatLink = document.getElementById('scraper-chat-link').value;
    const statusEl = document.getElementById('scraper-status');

    if (!phone || !chatLink) {
        return alert('Please select an account and provide a chat link.');
    }

    statusEl.textContent = 'Scraping in progress... This may take a while.';
    document.getElementById('audience-results-container').style.display = 'none';
    scrapedAudience = [];

    apiPost('/api/audiences/scrape', { phone, chat_link: chatLink }, (data) => {
        if (data.status === 'ok') {
            statusEl.textContent = `Scraping complete. Found ${data.users.length} users.`;
            scrapedAudience = data.users;
            displayAudienceResults(data.users);
        } else {
             // The generic apiPost handler will show the error alert
            statusEl.textContent = 'An error occurred during scraping.';
        }
    });
}

function displayAudienceResults(users) {
    const tableBody = document.getElementById('audience-table-body');
    tableBody.innerHTML = '';
    users.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username || 'N/A'}</td>
            <td>${[user.first_name, user.last_name].filter(Boolean).join(' ') || 'N/A'}</td>
            <td>${user.phone || 'N/A'}</td>
        `;
        tableBody.appendChild(row);
    });
    document.getElementById('audience-results-container').style.display = 'block';
}

function saveAudience() {
    const name = document.getElementById('save-audience-name').value.trim();
    if (!name) {
        return alert('Please provide a name for the audience.');
    }
    if (scrapedAudience.length === 0) {
        return alert('No audience data to save. Please scrape first.');
    }

    apiPost('/api/audiences/save', { name, users: scrapedAudience }, (data) => {
        if (data.status === 'ok') {
            document.getElementById('save-audience-name').value = '';
            document.getElementById('audience-results-container').style.display = 'none';
            scrapedAudience = [];
            loadAndDisplayAudiences();
        }
    });
}

function loadAndDisplayAudiences() {
    const listContainer = document.getElementById('saved-audiences-list');
    listContainer.innerHTML = '';
    fetch('/api/audiences').then(r => r.json()).then(files => {
        if (files.length === 0) {
            listContainer.innerHTML = '<p>No saved audiences yet.</p>';
            return;
        }
        files.forEach(filename => {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <span>${filename.replace('.json', '')}</span>
                <div class="item-actions">
                    <md-icon-button onclick="deleteAudience('${filename}')">
                        <span class="material-symbols-outlined">delete</span>
                    </md-icon-button>
                </div>
            `;
            listContainer.appendChild(item);
        });
    });
}

function deleteAudience(filename) {
    if (!confirm(`Are you sure you want to delete the audience "${filename.replace('.json', '')}"?`)) return;

    apiPost('/api/audiences/delete', { filename }, (data) => {
        if (data.status === 'ok') {
            loadAndDisplayAudiences();
        }
    });
}


// --- Proxy Manager ---

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
                    <md-text-button onclick="checkProxy('${p.id}')">Check</md-text-button>
                    <md-text-button onclick="deleteProxy('${p.id}')">Delete</md-text-button>
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
            document.getElementById('proxy-add-host').value = '';
            document.getElementById('proxy-add-port').value = '';
            document.getElementById('proxy-add-user').value = '';
            document.getElementById('proxy-add-pass').value = '';
        }
    });
}

function deleteProxy(proxyId) {
    if (confirm('Are you sure you want to delete this proxy?')) {
        apiPost('/api/proxies/delete', { id: proxyId }, (data) => {
            if (data.status === 'ok') loadProxies();
        });
    }
}

async function checkProxy(proxyId) {
    const statusCell = document.querySelector(`#proxy-${proxyId} .proxy-status`);
    if (!statusCell) return;
    statusCell.textContent = 'Checking...';
    statusCell.className = 'proxy-status';

    try {
        const proxiesResponse = await fetch('/api/proxies');
        const proxies = await proxiesResponse.json();
        const proxyToCheck = proxies.find(p => p.id === proxyId);

        if (!proxyToCheck) return statusCell.textContent = 'Error: Not Found';

        apiPost('/api/proxies/check', proxyToCheck, (data) => {
            statusCell.textContent = data.proxy_status || 'Error';
            statusCell.classList.add(data.proxy_status === 'working' ? 'working' : 'not-working');
        });
    } catch (e) {
        statusCell.textContent = 'Error';
    }
}

// --- Tags Dialog ---
const tagsDialog = document.getElementById('tags-dialog');

function openTagsDialog() {
    loadTags();
    tagsDialog.show();
}

function loadTags() {
    const container = document.getElementById('tags-list');
    container.innerHTML = 'Loading...';
    fetch('/api/tags').then(r => r.json()).then(tags => {
        container.innerHTML = '';
        if (!tags) return;
        tags.forEach(tag => {
            const tagEl = document.createElement('div');
            tagEl.className = 'tag-item';
            tagEl.innerHTML = `
                <span>${tag}</span>
                <md-icon-button onclick="deleteTag('${tag}')">
                    <span class="material-symbols-outlined">delete</span>
                </md-icon-button>
            `;
            container.appendChild(tagEl);
        });
    }).catch(e => {
        container.innerHTML = 'Failed to load tags.';
        console.error('Failed to load tags:', e);
    });
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
    if (confirm(`Delete the tag "${tagName}"? This will remove it from all accounts.`)) {
        apiPost('/api/tags/delete', { name: tagName }, (data) => {
            if (data.status === 'ok') {
                loadTags();
                loadAccounts();
            }
        });
    }
}
