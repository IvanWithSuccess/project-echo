
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
    // No longer need to add a listener for a button that doesn't exist yet
    // The `addAccount` function is now directly called from the button's onclick
});

function setupTabListeners() {
    const accountTabs = document.querySelector('#account-settings md-tabs');
    if (accountTabs) {
        accountTabs.addEventListener('change', () => {
            const activeTabId = accountTabs.activeTab.id;
            document.querySelectorAll('#account-settings .tab-panel').forEach(p => p.classList.remove('active'));
            const panelId = activeTabId.replace('tab-', '') + '-panel';
            const panel = document.getElementById(panelId);
            if (panel) {
                panel.classList.add('active');
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
            
            // Tags cell
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

            // Actions cell - CORRECTLY created buttons
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
    const phone = prompt('Enter phone number (in international format, e.g., +1234567890):');
    if (!phone) return;

    apiPost('/api/accounts/add', { phone })
        .then(data => {
            if (data.message.includes('Verification code sent')) {
                const code = prompt('Enter the code you received in Telegram:');
                if (code) {
                    finalizeAccount(phone, code);
                }
            } else {
                loadAccounts(); // Reload if already authorized or other message
            }
        })
        .catch(error => {
            // Handle specific errors, e.g. if 2FA is needed
            if (error.message.includes('2FA password required')) {
                const password = prompt('This account has Two-Factor Authentication enabled. Please enter your password:');
                if (password) {
                    finalizeAccount(phone, null, password);
                }
            }
        });
}

function finalizeAccount(phone, code, password = null) {
    const body = { phone, code, password };
    apiPost('/api/accounts/finalize', body).then(() => {
        loadAccounts(); // Refresh the accounts list on success
    });
}

function deleteAccount(phone) {
    if (confirm(`Are you sure you want to delete the account ${phone}? This action cannot be undone.`)) {
        apiPost('/api/accounts/delete', { phone }, () => {
            loadAccounts(); // Refresh list after deletion
        });
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

    // Populate header and hidden input
    document.getElementById('settings-account-display-phone').textContent = account.phone;
    
    // Ensure panels are correctly shown/hidden
    document.getElementById('main-settings-panel').classList.add('active');
    document.getElementById('proxy-settings-panel').classList.remove('active');
    document.querySelector('#account-settings md-tabs').activeTabIndex = 0;


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

    // Populate User Agent
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
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    const formData = new FormData();
    formData.append('avatar', file);

    fetch('/api/accounts/upload_avatar', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'ok') {
                document.getElementById('account-avatar-path').value = data.path;
                const avatarPreview = document.getElementById('avatar-preview');
                avatarPreview.src = `/uploads/${data.path.split('/').pop()}`;
                avatarPreview.style.display = 'block';
                alert('Avatar uploaded. Click "Save Settings" to associate it with the account.');
            } else {
                alert(`Upload failed: ${data.message}`);
            }
        });
}

function generateUserAgent() {
    // Basic generator, can be expanded
    const os = document.getElementById('ua-os').value;
    const chromeVersion = document.getElementById('ua-chrome-version').value;
    // This is a simplified example. Real Telethon strings are more complex.
    const uaString = `Mozilla/5.0 (${os === 'macOS' ? 'Macintosh; Intel Mac OS X 10_15_7' : 'Windows NT 10.0; Win64; x64'}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion} Safari/537.36`;
    document.getElementById('account-user-agent-input').value = uaString;
}


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
            chip.innerHTML = `
                ${tag}
                <span class="material-symbols-outlined" onclick="deleteTag('${tag}')">cancel</span>
            `;
            list.appendChild(chip);
        });
    });
}

function addTag() {
    const name = document.getElementById('tag-add-name').value;
    if (!name.trim()) return;
    apiPost('/api/tags/add', { name }, () => {
        loadTags();
        document.getElementById('tag-add-name').value = '';
    });
}

function deleteTag(name) {
    if (confirm(`Delete tag "${name}"? It will be removed from all accounts.`)) {
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
            
            // Actions
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
    if (!proxy.host || !proxy.port) {
        return alert('Host and Port are required.');
    }
    apiPost('/api/proxies/add', proxy, () => {
        loadProxies();
        // Clear form
        document.getElementById('proxy-add-host').value = '';
        document.getElementById('proxy-add-port').value = '';
        document.getElementById('proxy-add-user').value = '';
        document.getElementById('proxy-add-pass').value = '';
    });
}

function deleteProxy(proxyId) {
    if (confirm('Are you sure you want to delete this proxy?')) {
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
    select.innerHTML = '<md-select-option value=""></md-select-option>'; // "No Proxy" option
    fetch('/api/proxies').then(r => r.json()).then(proxies => {
        proxies.forEach(p => {
            const option = document.createElement('md-select-option');
            option.value = p.id;
            option.textContent = `${p.host}:${p.port} (${p.type.toUpperCase()})`;
            if (p.id === selectedProxyId) {
                option.selected = true;
            }
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
    statusEl.textContent = 'Scraping... this may take a while.';
    
    apiPost('/api/audiences/scrape', { phone, chat_link }, (data) => {
        statusEl.textContent = `Scraping complete. Found ${data.users.length} users.`;
        scrapedAudience = data.users;
        
        const resultsContainer = document.getElementById('audience-results-container');
        resultsContainer.style.display = 'block';
        
        const tableBody = document.getElementById('audience-table-body');
        tableBody.innerHTML = '';
        scrapedAudience.forEach(u => {
            const row = tableBody.insertRow();
            row.insertCell().textContent = u.id;
            row.insertCell().textContent = u.username || 'N/A';
            row.insertCell().textContent = u.name || 'N/A';
            row.insertCell().textContent = u.phone || 'N/A';
        });
    }).catch(() => {
        statusEl.textContent = 'Scraping failed. Check server logs.';
    });
}

function saveAudience() {
    const name = document.getElementById('save-audience-name').value;
    if (!name.trim()) return alert('Please provide a name for the audience.');
    if (scrapedAudience.length === 0) return alert('No users to save.');

    apiPost('/api/audiences/save', { name, users: scrapedAudience }, () => {
        // Clear results
        document.getElementById('audience-results-container').style.display = 'none';
        document.getElementById('save-audience-name').value = '';
        scrapedAudience = [];
        loadAndDisplayAudiences(); // Refresh the list of saved audiences
    });
}

function loadAndDisplayAudiences() {
    fetch('/api/audiences').then(r => r.json()).then(files => {
        const list = document.getElementById('saved-audiences-list');
        list.innerHTML = '';
        files.forEach(filename => {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <span><span class="material-symbols-outlined">folder</span> ${filename.replace('.json', '')}</span>
                <md-icon-button onclick="deleteAudienceFromList('${filename}')">
                    <span class="material-symbols-outlined">delete</span>
                </md-icon-button>
            `;
            list.appendChild(item);
        });
    });
}

function deleteAudienceFromList(filename) {
    if (confirm(`Are you sure you want to delete the audience "${filename}"?`)) {
        apiPost('/api/audiences/delete', { filename }, () => {
            loadAndDisplayAudiences();
        });
    }
}


// =================================================================================
// Ad Cabinet
// =================================================================================

function loadCampaignFormData() {
    // Load audiences into select
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

    // Load accounts into checkbox list
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
    
    const selectedCheckboxes = document.querySelectorAll('#campaign-accounts-list md-checkbox[checked]');
    const account_phones = Array.from(selectedCheckboxes).map(cb => cb.value);

    if (!name || !audience_file || !message || account_phones.length === 0) {
        return alert('Please fill all fields and select at least one account.');
    }

    const campaignData = { name, audience_file, account_phones, message };
    
    apiPost('/api/campaigns/start', campaignData, (data) => {
        if (data.status === 'ok') {
            loadCampaigns(); // Refresh the list immediately
            // Clear form
            document.getElementById('campaign-name').value = '';
            document.getElementById('campaign-message').value = '';
        }
    });
}

function loadCampaigns() {
    fetch('/api/campaigns').then(r => r.json()).then(campaigns => {
        const tableBody = document.getElementById('campaigns-table-body');
        tableBody.innerHTML = '';
        if (!campaigns) return;

        campaigns.forEach(c => {
            const row = document.createElement('tr');
            const createdDate = new Date(c.created_at + 'Z').toLocaleString(); 
            
            row.innerHTML = `
                <td>${c.name}</td>
                <td>${c.audience_file.replace('.json', '')}</td>
                <td>${c.progress || `0/${c.total_users}`}</td>
                <td><span class="status status-${(c.status || '').toLowerCase()}">${c.status}</span></td>
                <td>${createdDate}</td>
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
    if (!confirm('Are you sure you want to delete this campaign? This will remove it from the list.')) return;
    apiPost('/api/campaigns/delete', { id: campaignId }, () => {
        loadCampaigns();
    }, false);
}
