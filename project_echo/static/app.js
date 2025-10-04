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
    if (sectionId === 'audiences') { loadAccounts(); loadAndDisplayAudiences(); }
    if (sectionId === 'campaigns') { loadCampaigns(); loadAccountsForCampaign(); loadAndDisplayAudiences(); }
    
    // If we are switching to any main section, ensure the specific account settings page is hidden
    if (['dashboard', 'accounts', 'audiences', 'campaigns', 'tasks', 'settings'].includes(sectionId)) {
         document.getElementById('account-settings').style.display = 'none';
         document.getElementById('accounts').style.display = (sectionId === 'accounts') ? 'block' : 'none';
    }
}

function showAccountSettingsPage(account) {
    // Hide the main accounts list and show the settings page
    document.getElementById('accounts').style.display = 'none';
    document.getElementById('account-settings').style.display = 'block';
    document.getElementById('account-settings').classList.add('active'); // Make it the active section

    // Populate data
    openAccountSettings(account);
}

function showMainAccountsPage() {
    // Hide settings, show main accounts list
    document.getElementById('account-settings').style.display = 'none';
    document.getElementById('account-settings').classList.remove('active');
    document.getElementById('accounts').style.display = 'block';
    switchSection('accounts'); // Re-run switchSection to fix nav and load accounts
}

function openSettingsTab(evt, tabName) {
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    document.querySelectorAll('.tab-link').forEach(tl => tl.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    evt.currentTarget.classList.add('active');
}


// --- Accounts Management ---
function loadAccounts() {
    fetch('/api/accounts').then(r => r.json()).then(data => {
        const tableBody = document.getElementById('accounts-table-body');
        if (!tableBody) return;
        tableBody.innerHTML = '';
        data.forEach(acc => {
            const tagsHtml = (acc.settings?.tags || []).map(tag => `<span class="tag">${tag}</span>`).join(' ');
            tableBody.innerHTML += `
                <tr>
                    <td>${acc.phone}</td>
                    <td>${acc.username || 'N/A'}</td>
                    <td>${tagsHtml}</td>
                    <td>
                        <button onclick='showAccountSettingsPage(${JSON.stringify(acc)})'>Settings</button>
                        <button class="delete-btn" onclick="deleteAccount('${acc.phone}')">Delete</button>
                    </td>
                </tr>`;
        });
    }).catch(e => console.error('Error loading accounts:', e));
}

function addAccount() {
    const phone = prompt("Enter phone number (e.g., +1234567890):");
    if (!phone) return;
    fetch('/api/accounts/add', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone})})
    .then(r => r.json()).then(data => {
        if (data.message.includes('Verification code sent')) {
            const code = prompt("Enter verification code:");
            if (code) finalizeLogin(phone, code);
        } else if (data.message.includes('password required')) {
            const password = prompt("Enter 2FA password:");
            if (password) finalizeLogin(phone, null, password);
        }
        alert(data.message);
        loadAccounts();
    });
}

function finalizeLogin(phone, code, password = null) {
    fetch('/api/accounts/finalize', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone,code,password})})
    .then(r => r.json()).then(data => {
        if (data.message.includes('password required')) {
            const new_password = prompt("2FA password required:");
            if (new_password) finalizeLogin(phone, null, new_password);
        } else {
            alert(data.message); loadAccounts();
        }
    });
}

function deleteAccount(phone) {
    if (!confirm(`Are you sure you want to delete account ${phone}? This action is irreversible.`)) return;
    fetch('/api/accounts/delete', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone})})
    .then(r=>r.json()).then(data=>{alert(data.message); loadAccounts();});
}

// --- Account Settings Page ---
function openAccountSettings(account) {
    document.getElementById('settings-account-phone').value = account.phone;
    document.getElementById('settings-account-display-phone').innerText = account.phone;
    
    const settings = account.settings || {};
    const profile = settings.profile || {};
    const proxy = settings.proxy || {};

    // Main Tab
    document.getElementById('account-first-name').value = profile.first_name || '';
    document.getElementById('account-last-name').value = profile.last_name || '';
    document.getElementById('account-bio').value = profile.bio || '';
    document.getElementById('account-avatar-path').value = profile.avatar_path || '';
    document.getElementById('account-user-agent-input').value = settings.system_version || '';
    
    const preview = document.getElementById('avatar-preview');
    preview.src = profile.avatar_path ? `/` + profile.avatar_path : '/static/placeholder.png';

    // Proxy Tab
    document.getElementById('account-proxy-type').value = proxy.type || 'socks5';
    document.getElementById('account-proxy-host').value = proxy.host || '';
    document.getElementById('account-proxy-port').value = proxy.port || '';
    document.getElementById('account-proxy-user').value = proxy.user || '';
    document.getElementById('account-proxy-pass').value = proxy.pass || '';

    // Tags Tab
    document.getElementById('account-tags-input').value = (settings.tags || []).join(', ');
    
    // Set first tab as active
    openSettingsTab({currentTarget: document.querySelector('.tab-link')}, 'main-settings');
}

function handleAvatarUpload() {
    const input = document.getElementById('avatar-upload-input');
    const preview = document.getElementById('avatar-preview');
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('avatar', file);

    fetch('/api/accounts/upload_avatar', { method: 'POST', body: formData })
    .then(r => r.json()).then(data => {
        if(data.status === 'ok') {
            document.getElementById('account-avatar-path').value = data.path;
            preview.src = `/` + data.path; // Update preview
        } else {
            alert('Upload failed: ' + data.message);
        }
    }).catch(e => {
        alert('An error occurred during upload.');
        console.error(e);
    });
}

function saveAccountSettings() {
    const phone = document.getElementById('settings-account-phone').value;
    
    const proxyHost = document.getElementById('account-proxy-host').value;
    const proxyPort = document.getElementById('account-proxy-port').value;

    const settings = {
        profile: {
            first_name: document.getElementById('account-first-name').value,
            last_name: document.getElementById('account-last-name').value,
            bio: document.getElementById('account-bio').value,
            avatar_path: document.getElementById('account-avatar-path').value
        },
        tags: document.getElementById('account-tags-input').value.split(',').map(t => t.trim()).filter(t => t),
        system_version: document.getElementById('account-user-agent-input').value,
        proxy: (proxyHost && proxyPort) ? {
            type: document.getElementById('account-proxy-type').value,
            host: proxyHost,
            port: parseInt(proxyPort, 10),
            user: document.getElementById('account-proxy-user').value,
            pass: document.getElementById('account-proxy-pass').value
        } : null
    };

    fetch('/api/accounts/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, settings })
    })
    .then(r => r.json()).then(data => {
        if (data.status === 'ok') {
            alert("Settings saved successfully!");
        } else {
            alert(`Error: ${data.message}`);
        }
    });
}

function applyProfileChanges() {
    const phone = document.getElementById('settings-account-phone').value;
    if (!confirm(`This will connect to Telegram and apply profile changes for ${phone}. Continue?`)) return;

    const profileData = {
        first_name: document.getElementById('account-first-name').value,
        last_name: document.getElementById('account-last-name').value,
        bio: document.getElementById('account-bio').value,
        avatar_path: document.getElementById('account-avatar-path').value
    };

    fetch('/api/accounts/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, profile: profileData })
    })
    .then(r => r.json()).then(data => {
        alert(data.message);
    });
}

// --- Audience Management ---
function loadAndDisplayAudiences() {
    fetch('/api/audiences').then(r => r.json()).then(data => {
        if (data.status !== 'ok') return;
        const list = document.getElementById('saved-audiences-list');
        const select = document.getElementById('campaign-audience-select');
        list.innerHTML = data.audiences.length ? '' : '<li>No saved audiences.</li>';
        select.innerHTML = '<option disabled selected value="">Select an audience</option>';
        data.audiences.forEach(name => {
            list.innerHTML += `<li>${name}</li>`;
            select.innerHTML += `<option value="${name}">${name}</option>`;
        });
    }).catch(e => console.error('Error loading audiences:', e));
}

function scrapeAudience() {
    const phone = document.getElementById('scraper-account').value;
    const chat_link = document.getElementById('chat-link').value;
    const statusEl = document.getElementById('scraper-status');

    if (!phone || !chat_link) { return alert('Please select an account and provide a chat link.'); }

    statusEl.innerText = 'Scraping in progress...';
    document.getElementById('save-audience-btn').style.display = 'none';

    fetch('/api/audience/scrape', { method: 'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({phone, chat_link}) })
    .then(r => r.json()).then(data => {
        if (data.status === 'ok') {
            statusEl.innerText = `Scraping complete! Found ${data.users.length} users.`;
            scrapedAudience = data.users;
            populateAudienceTable(scrapedAudience);
            document.getElementById('save-audience-btn').style.display = 'inline-block';
        } else {
            statusEl.innerText = `Error: ${data.message}`;
        }
    }).catch(e => statusEl.innerText = `Fetch Error: ${e}`);
}

function saveAudience() {
    const filename = prompt("Enter a name for this audience (e.g., 'crypto_investors'):");
    if (!filename || !scrapedAudience.length) return;

    fetch('/api/audiences/save', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({filename, users: scrapedAudience}) })
    .then(r => r.json()).then(data => {
        alert(data.message);
        if (data.status === 'ok') {
            loadAndDisplayAudiences(); 
            scrapedAudience = [];
            document.getElementById('audience-table-body').innerHTML = '';
            document.getElementById('save-audience-btn').style.display = 'none';
            document.getElementById('scraper-status').innerText = '';
        }
    });
}

function populateAudienceTable(users) {
    const tableBody = document.getElementById('audience-table-body');
    tableBody.innerHTML = '';
    users.forEach(user => {
        tableBody.innerHTML += `<tr><td>${user.id}</td><td>${user.username || 'N/A'}</td><td>${user.first_name || ''} ${user.last_name || ''}</td></tr>`;
    });
}

// --- Campaign Management ---
function loadCampaigns() {
    fetch('/api/campaigns').then(r => r.json()).then(campaigns => {
        const tableBody = document.getElementById('campaigns-table-body');
        tableBody.innerHTML = '';
        campaigns.forEach(c => {
            const actions = c.status === 'Draft' 
                ? `<button onclick="startCampaign('${c.id}')">Start</button><button onclick="editCampaign('${c.id}')">Edit</button>`
                : (c.status === 'In Progress' ? '<i>Running...</i>' : '<i>Finished</i>');
            
            tableBody.innerHTML += `<tr>
                <td>${c.name}</td>
                <td>${c.audience}</td>
                <td>${c.status}</td>
                <td>${actions} <button class="delete-btn">Delete</button></td>
            </tr>`;
        });
    });
}

function startCampaign(campaignId) {
    if (!confirm("Are you sure you want to start this campaign? It will begin sending messages.")) return;

    fetch('/api/campaigns/start', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id: campaignId}) })
    .then(r => r.json())
    .then(data => {
        alert(data.message);
        if(data.status === 'ok') loadCampaigns();
    });
}

function editCampaign(campaignId) {
    alert("Editing functionality to be fully implemented. For now, create a new campaign.");
}

function toggleCampaignForm(show) {
    document.getElementById('campaign-form-container').style.display = show ? 'block' : 'none';
    document.getElementById('campaign-list-view').style.display = show ? 'none' : 'block';
    if (!show) { 
        document.getElementById('campaign-id').value = '';
        document.getElementById('campaign-name').value = '';
        document.getElementById('campaign-message').value = '';
        document.getElementById('campaign-audience-select').value = '';
        document.querySelectorAll('#campaign-accounts-select input:checked').forEach(i => i.checked = false);
    }
}

function loadAccountsForCampaign(){
     fetch('/api/accounts').then(r => r.json()).then(data => {
        const container = document.getElementById('campaign-accounts-select');
        container.innerHTML = '';
        data.forEach(acc => {
            container.innerHTML += `<label><input type="checkbox" name="campaign-account" value="${acc.phone}"> ${acc.phone} (${acc.username || 'N/A'})</label>`;
        });
    });
}

function saveCampaign() {
    const campaign = {
        id: document.getElementById('campaign-id').value,
        name: document.getElementById('campaign-name').value,
        message: document.getElementById('campaign-message').value,
        audience: document.getElementById('campaign-audience-select').value,
        accounts: Array.from(document.querySelectorAll('#campaign-accounts-select input:checked')).map(i => i.value)
    };

    if (!campaign.name || !campaign.message || !campaign.audience || campaign.accounts.length === 0) {
        return alert('Please fill all fields: Name, Message, Audience, and select at least one account.');
    }

    fetch('/api/campaigns/save', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(campaign) })
    .then(r => r.json()).then(data => {
        if (data.status === 'ok') {
            alert(data.message);
            toggleCampaignForm(false);
            loadCampaigns();
        } else {
            alert(`Error: ${data.message}`);
        }
    });
}