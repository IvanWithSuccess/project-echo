
// =================================================================================
// App State & Initialization
// =================================================================================

let currentAccount = null; 
let scrapedAudience = []; 
let campaignIntervalId = null;

document.addEventListener('DOMContentLoaded', () => {
    // Set initial section and setup event listeners
    switchSection('dashboard');
    setupTabListeners();
});

function setupTabListeners() {
    const accountTabs = document.querySelector('#account-settings md-tabs');
    if (accountTabs) {
        // This is the critical fix. The event is `change`, not anything else.
        accountTabs.addEventListener('change', () => {
            const activeTab = accountTabs.querySelector('md-primary-tab[active]');
            if (activeTab) {
                const panelId = activeTab.id.replace('tab-', '') + '-panel';
                document.querySelectorAll('#account-settings .tab-panel').forEach(p => p.classList.remove('active'));
                const panel = document.getElementById(panelId);
                if (panel) {
                    panel.classList.add('active');
                }
            }
        });
    }
}


// =================================================================================
// Core UI & API Functions
// =================================================================================

function switchSection(sectionId) {
    // Hide all sections, show the target one
    document.querySelectorAll('.content-section').forEach(s => s.style.display = 'none');
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));

    // Stop polling campaigns if we navigate away
    if (campaignIntervalId) {
        clearInterval(campaignIntervalId);
        campaignIntervalId = null;
    }

    const section = document.getElementById(sectionId);
    if (section) section.style.display = 'block';

    const navItem = document.getElementById(`nav-${sectionId.split('-')[0]}`);
    if (navItem) navItem.classList.add('active');

    // Load data for the activated section
    switch (sectionId) {
        case 'accounts': loadAccounts(); break;
        case 'account-settings': /* Loaded by showAccountSettingsPage */ break;
        case 'proxies': loadProxies(); break;
        case 'audiences': loadAccountsForScraper(); loadAndDisplayAudiences(); break;
        case 'campaigns': loadCampaignFormData(); loadCampaigns(); campaignIntervalId = setInterval(loadCampaigns, 5000); break;
    }
}

async function apiPost(endpoint, body, showAlerts = true) {
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.message || `HTTP error! Status: ${response.status}`);
        }
        if (showAlerts && data.message) {
            alert(data.message);
        }
        return data; // Return data for further processing
    } catch (error) {
        console.error(`API Error at ${endpoint}:`, error);
        if (showAlerts) {
            alert(error.message);
        }
        throw error; // Re-throw to be caught by calling function if needed
    }
}


// =================================================================================
// Accounts Center
// =================================================================================

function loadAccounts() {
    fetch('/api/accounts').then(r => r.json()).then(accounts => {
        const tableBody = document.getElementById('accounts-table-body');
        tableBody.innerHTML = ''; // Clear existing rows
        accounts.forEach(acc => {
            const row = tableBody.insertRow();
            
            row.insertCell().textContent = acc.phone;
            row.insertCell().textContent = acc.username || 'N/A';
            
            const tagsCell = row.insertCell();
            const tagsContainer = document.createElement('div');
            tagsContainer.className = 'tag-chip-container';
            (acc.settings?.tags || []).forEach(t => {
                const tagChip = document.createElement('div');
                tagChip.className = 'tag-chip';
                tagChip.textContent = t;
                tagsContainer.appendChild(tagChip);
            });
            tagsCell.appendChild(tagsContainer);

            const actionsCell = row.insertCell();
            const settingsButton = document.createElement('md-text-button');
            settingsButton.textContent = 'Settings';
            settingsButton.onclick = () => showAccountSettingsPage(acc);
            actionsCell.appendChild(settingsButton);

            const deleteButton = document.createElement('md-text-button');
            deleteButton.textContent = 'Delete';
            deleteButton.onclick = () => deleteAccount(acc.phone);
            actionsCell.appendChild(deleteButton);
        });
    });
}

function addAccount() {
    const phone = prompt('Enter phone number (e.g., +1234567890):');
    if (!phone) return;

    apiPost('/api/accounts/add', { phone }, false)
        .then(data => {
            if (data.message.includes('Verification code sent')) {
                const code = prompt('Enter the code from Telegram:');
                if (code) finalizeAccount(phone, code);
            }
            else {
                 alert(data.message);
                 loadAccounts();
            }
        })
        .catch(error => {
            if (error.message.includes('PASSWORD_NEEDED')) {
                const password = prompt('2FA password required:');
                if (password) finalizeAccount(phone, null, password);
            }
        });
}

function finalizeAccount(phone, code, password = null) {
    apiPost('/api/accounts/finalize', { phone, code, password }).then(() => loadAccounts());
}

function deleteAccount(phone) {
    if (confirm(`Delete ${phone}?`)) {
        apiPost('/api/accounts/delete', { phone }, () => loadAccounts());
    }
}

function showMainAccountsPage() {
    switchSection('accounts');
}


// =================================================================================
// Account Settings Page
// =================================================================================

function showAccountSettingsPage(account) {
    currentAccount = account;
    switchSection('account-settings');

    document.getElementById('settings-account-display-phone').textContent = account.phone;
    
    // Reset tabs and panels to a known state
    document.getElementById('main-settings-panel').classList.add('active');
    document.getElementById('proxy-settings-panel').classList.remove('active');
    const tabs = document.querySelector('#account-settings md-tabs');
    if (tabs) tabs.activeTabIndex = 0;

    // Populate Main Settings
    const settings = account.settings || {};
    const profile = settings.profile || {};
    document.getElementById('account-first-name').value = profile.first_name || '';
    document.getElementById('account-last-name').value = profile.last_name || '';
    document.getElementById('account-bio').value = profile.bio || '';
    
    const avatarPath = settings.avatar_path || '';
    const avatarPreview = document.getElementById('avatar-preview');
    document.getElementById('account-avatar-path').value = avatarPath;
    if (avatarPath) {
        avatarPreview.src = `/uploads/${avatarPath.split('/').pop()}`;
        avatarPreview.style.display = 'block';
    } else {
        avatarPreview.style.display = 'none';
    }

    const ua = settings.user_agent || {};
    document.getElementById('ua-os').value = ua.os || 'Windows';
    document.getElementById('ua-chrome-version').value = ua.chrome || '108.0.5359.215';
    document.getElementById('account-user-agent-input').value = ua.full_string || '';

    // Populate Proxy Settings
    loadProxiesForAccount(settings.proxy_id);
}

function saveAccountSettings() {
    if (!currentAccount) return;

    const settings = {
        profile: {
            first_name: document.getElementById('account-first-name').value,
            last_name: document.getElementById('account-last-name').value,
            bio: document.getElementById('account-bio').value
        },
        user_agent: {
            os: document.getElementById('ua-os').value,
            chrome: document.getElementById('ua-chrome-version').value,
            full_string: document.getElementById('account-user-agent-input').value
        },
        avatar_path: document.getElementById('account-avatar-path').value,
        proxy_id: document.getElementById('account-proxy-select').value
    };

    apiPost('/api/accounts/settings', { phone: currentAccount.phone, settings });
}

function applyProfileChanges() {
    if (!currentAccount) return;
    const profileData = {
        first_name: document.getElementById('account-first-name').value,
        last_name: document.getElementById('account-last-name').value,
        bio: document.getElementById('account-bio').value,
        avatar_path: document.getElementById('account-avatar-path').value
    };
    apiPost('/api/accounts/profile', { phone: currentAccount.phone, profile: profileData });
}

function handleAvatarUpload() {
    const input = document.getElementById('avatar-upload-input');
    if (!input.files.length) return;
    const formData = new FormData();
    formData.append('avatar', input.files[0]);

    fetch('/api/accounts/upload_avatar', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'ok') {
                document.getElementById('account-avatar-path').value = data.path;
                const preview = document.getElementById('avatar-preview');
                preview.src = `/uploads/${data.path.split('/').pop()}`;
                preview.style.display = 'block';
                alert('Avatar uploaded. Click "Save Settings" to confirm.');
            } else {
                alert(`Upload failed: ${data.message}`);
            }
        });
}

function generateUserAgent() {
    const os = document.getElementById('ua-os').value;
    const chrome = document.getElementById('ua-chrome-version').value;
    document.getElementById('account-user-agent-input').value = `Mozilla/5.0 (${os === 'macOS' ? 'Macintosh; Intel Mac OS X 10_15_7' : 'Windows NT 10.0; Win64; x64'}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chrome} Safari/537.36`;
}

// ... (Keep Tag, Proxy, Audience, and Campaign functions as they are, they are correct) ...

// =================================================================================
// Tags Management (Dialog)
// =================================================================================

function openTagsDialog() {
    loadTags();
    document.getElementById('tags-dialog').show();
}

function loadTags() {
    fetch('/api/tags').then(r => r.json()).then(tags => {
        const list = document.getElementById('tags-list');
        list.innerHTML = '';
        tags.forEach(tag => {
            const chip = document.createElement('div');
            chip.className = 'tag-chip-interactive';
            chip.innerHTML = `${tag} <span class="material-symbols-outlined" onclick="deleteTag('${tag}')">cancel</span>`;
            list.appendChild(chip);
        });
    });
}

function addTag() {
    const name = document.getElementById('tag-add-name').value;
    if (name.trim()) apiPost('/api/tags/add', { name }, () => {
        loadTags();
        document.getElementById('tag-add-name').value = '';
    });
}

function deleteTag(name) {
    if (confirm(`Delete tag "${name}"?`)) {
        apiPost('/api/tags/delete', { name }, () => loadTags());
    }
}


// =================================================================================
// Proxies Section
// =================================================================================

function loadProxies() {
    fetch('/api/proxies').then(r => r.json()).then(proxies => {
        const tableBody = document.getElementById('proxies-table-body');
        tableBody.innerHTML = '';
        proxies.forEach(p => {
            const row = tableBody.insertRow();
            row.insertCell().textContent = `${p.host}:${p.port}`;
            row.insertCell().textContent = p.type.toUpperCase();
            row.insertCell().textContent = p.user || 'N/A';
            row.insertCell().id = `proxy-status-${p.id}`;
            
            const actionsCell = row.insertCell();
            const checkButton = document.createElement('md-text-button');
            checkButton.textContent = 'Check';
            checkButton.onclick = () => checkProxy(p);
            actionsCell.appendChild(checkButton);
            
            const deleteButton = document.createElement('md-text-button');
            deleteButton.textContent = 'Delete';
            deleteButton.onclick = () => deleteProxy(p.id);
            actionsCell.appendChild(deleteButton);
        });
    });
}

function addProxy() {
    const proxy = {
        type: document.getElementById('proxy-add-type').value,
        host: document.getElementById('proxy-add-host').value,
        port: document.getElementById('proxy-add-port').value,
        user: document.getElementById('proxy-add-user').value,
        pass: document.getElementById('proxy-add-pass').value
    };
    if (!proxy.host || !proxy.port) return alert('Host and Port are required.');
    apiPost('/api/proxies/add', proxy, () => {
        loadProxies();
        ['proxy-add-host', 'proxy-add-port', 'proxy-add-user', 'proxy-add-pass'].forEach(id => document.getElementById(id).value = '');
    });
}

function deleteProxy(proxyId) {
    if (confirm('Delete this proxy?')) {
        apiPost('/api/proxies/delete', { id: proxyId }, () => loadProxies());
    }
}

function checkProxy(proxy) {
    const statusCell = document.getElementById(`proxy-status-${proxy.id}`);
    statusCell.textContent = 'Checking...';
    apiPost('/api/proxies/check', proxy, (data) => {
        statusCell.textContent = data.proxy_status;
        statusCell.style.color = data.proxy_status === 'working' ? 'green' : 'red';
    }, false);
}

function loadProxiesForAccount(selectedProxyId) {
    const select = document.getElementById('account-proxy-select');
    select.innerHTML = '<md-select-option value=""></md-select-option>';
    fetch('/api/proxies').then(r => r.json()).then(proxies => {
        proxies.forEach(p => {
            const option = document.createElement('md-select-option');
            option.value = p.id;
            option.textContent = `${p.host}:${p.port}`;
            if (p.id === selectedProxyId) option.selected = true;
            select.appendChild(option);
        });
        select.value = selectedProxyId || '';
    });
}


// =================================================================================
// Audience CRM
// =================================================================================

function loadAccountsForScraper() {
    const select = document.getElementById('scraper-account-select');
    select.innerHTML = '<md-select-option></md-select-option>';
    fetch('/api/accounts').then(r => r.json()).then(accounts => {
        accounts.forEach(acc => {
            const option = document.createElement('md-select-option');
            option.value = acc.phone;
            option.textContent = `${acc.phone} (${acc.username || 'N/A'})`;
            select.appendChild(option);
        });
    });
}

function scrapeAudience() {
    const phone = document.getElementById('scraper-account-select').value;
    const chat_link = document.getElementById('scraper-chat-link').value;
    if (!phone || !chat_link) return alert('Please select an account and provide a chat link.');

    const statusEl = document.getElementById('scraper-status');
    statusEl.textContent = 'Scraping...';
    
    apiPost('/api/audiences/scrape', { phone, chat_link }, (data) => {
        statusEl.textContent = `Found ${data.users.length} users.`;
        scrapedAudience = data.users;
        document.getElementById('audience-results-container').style.display = 'block';
        const tableBody = document.getElementById('audience-table-body');
        tableBody.innerHTML = '';
        scrapedAudience.forEach(u => {
            const row = tableBody.insertRow();
            row.insertCell().textContent = u.id;
            row.insertCell().textContent = u.username || 'N/A';
            row.insertCell().textContent = u.name || 'N/A';
            row.insertCell().textContent = u.phone || 'N/A';
        });
    }).catch(() => statusEl.textContent = 'Scraping failed.');
}

function saveAudience() {
    const name = document.getElementById('save-audience-name').value;
    if (!name.trim() || !scrapedAudience.length) return alert('Audience name and scraped users are required.');
    apiPost('/api/audiences/save', { name, users: scrapedAudience }, () => {
        document.getElementById('audience-results-container').style.display = 'none';
        document.getElementById('save-audience-name').value = '';
        scrapedAudience = [];
        loadAndDisplayAudiences();
    });
}

function loadAndDisplayAudiences() {
    fetch('/api/audiences').then(r => r.json()).then(files => {
        const list = document.getElementById('saved-audiences-list');
        list.innerHTML = '';
        files.forEach(filename => {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `<span><span class="material-symbols-outlined">folder</span> ${filename.replace('.json', '')}</span>
                <md-icon-button onclick="deleteAudienceFromList('${filename}')"><span class="material-symbols-outlined">delete</span></md-icon-button>`;
            list.appendChild(item);
        });
    });
}

function deleteAudienceFromList(filename) {
    if (confirm(`Delete audience "${filename}"?`)) {
        apiPost('/api/audiences/delete', { filename }, () => loadAndDisplayAudiences());
    }
}


// =================================================================================
// Ad Cabinet
// =================================================================================

function loadCampaignFormData() {
    const audienceSelect = document.getElementById('campaign-audience-select');
    audienceSelect.innerHTML = '<md-select-option></md-select-option>';
    fetch('/api/audiences').then(r => r.json()).then(files => {
        files.forEach(filename => {
            const option = document.createElement('md-select-option');
            option.value = filename;
            option.textContent = filename.replace('.json', '');
            audienceSelect.appendChild(option);
        });
    });

    const accountsList = document.getElementById('campaign-accounts-list');
    accountsList.innerHTML = '';
    fetch('/api/accounts').then(r => r.json()).then(accounts => {
        accounts.forEach(acc => {
            const label = document.createElement('label');
            label.className = 'checkbox-label';
            const checkbox = document.createElement('md-checkbox');
            checkbox.value = acc.phone;
            const text = document.createElement('span');
            text.textContent = ` ${acc.phone}${acc.username ? ` (${acc.username})` : ''}`;
            label.appendChild(checkbox);
            label.appendChild(text);
            accountsList.appendChild(label);
        });
    });
}

function startCampaign() {
    const name = document.getElementById('campaign-name').value;
    const audience_file = document.getElementById('campaign-audience-select').value;
    const message = document.getElementById('campaign-message').value;
    const account_phones = Array.from(document.querySelectorAll('#campaign-accounts-list md-checkbox[checked]')).map(cb => cb.value);

    if (!name || !audience_file || !message || !account_phones.length) return alert('All fields and at least one account are required.');

    apiPost('/api/campaigns/start', { name, audience_file, account_phones, message }, () => {
        loadCampaigns();
        document.getElementById('campaign-name').value = '';
        document.getElementById('campaign-message').value = '';
    });
}

function loadCampaigns() {
    fetch('/api/campaigns').then(r => r.json()).then(campaigns => {
        const tableBody = document.getElementById('campaigns-table-body');
        tableBody.innerHTML = '';
        if (!campaigns) return;
        campaigns.forEach(c => {
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td>${c.name}</td>
                <td>${c.audience_file.replace('.json', '')}</td>
                <td>${c.progress || `0/${c.total_users}`}</td>
                <td><span class="status status-${(c.status || '').toLowerCase()}">${c.status}</span></td>
                <td>${new Date(c.created_at + 'Z').toLocaleString()}</td>
            `;
            const actionsCell = row.insertCell();
            const deleteButton = document.createElement('md-icon-button');
            deleteButton.innerHTML = `<span class="material-symbols-outlined">delete</span>`;
            deleteButton.onclick = () => deleteCampaign(c.id);
            actionsCell.appendChild(deleteButton);
        });
    });
}

function deleteCampaign(campaignId) {
    if (confirm('Delete this campaign?')) {
        apiPost('/api/campaigns/delete', { id: campaignId }, () => loadCampaigns(), false);
    }
}
