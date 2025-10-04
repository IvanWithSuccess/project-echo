let scrapedAudience = [];

document.addEventListener('DOMContentLoaded', () => {
    switchSection('dashboard');
});

window.onclick = function(event) {
    const modal = document.getElementById("account-settings-modal");
    if (event.target == modal) {
        closeAccountSettingsModal();
    }
}

function switchSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar nav li').forEach(i => i.classList.remove('active'));

    document.getElementById(sectionId)?.classList.add('active');
    document.getElementById(`nav-${sectionId}`)?.classList.add('active');

    if (sectionId === 'accounts') loadAccounts();
    if (sectionId === 'audiences') { loadAccounts(); loadAndDisplayAudiences(); }
    if (sectionId === 'campaigns') { loadCampaigns(); loadAccountsForCampaign(); loadAndDisplayAudiences(); }
}

// --- Accounts Management ---
function loadAccounts() {
    fetch('/api/accounts').then(r => r.json()).then(data => {
        const tableBody = document.getElementById('accounts-table-body');
        const scraperSelect = document.getElementById('scraper-account');
        tableBody.innerHTML = '';
        scraperSelect.innerHTML = '<option disabled selected>Select an account</option>';
        
        data.forEach(acc => {
            const tagsHtml = (acc.settings?.tags || []).map(tag => `<span class="tag">${tag}</span>`).join(' ');
            tableBody.innerHTML += `
                <tr>
                    <td>${acc.phone}</td>
                    <td>${acc.username || 'N/A'}</td>
                    <td>${tagsHtml}</td>
                    <td>
                        <button onclick='openAccountSettingsModal(${JSON.stringify(acc)})'>Settings</button>
                        <button class="delete-btn" onclick="deleteAccount('${acc.phone}')">Delete</button>
                    </td>
                </tr>`;

            scraperSelect.innerHTML += `<option value="${acc.phone}">${acc.phone} (${acc.username || 'N/A'})</option>`;
        });
    }).catch(e => console.error('Error loading accounts:', e));
}

function addAccount() {
    // ... (unchanged)
}

function finalizeLogin(phone, code, password = null) {
    // ... (unchanged)
}

function deleteAccount(phone) {
    // ... (unchanged)
}

// --- Account Settings Modal ---
function openAccountSettingsModal(account) {
    document.getElementById('settings-account-phone').value = account.phone;
    document.getElementById('settings-modal-title').innerText = `Settings for ${account.phone}`;
    
    const settings = account.settings || {};
    const profile = settings.profile || {};
    const proxy = settings.proxy || {};

    // Profile
    document.getElementById('account-first-name').value = profile.first_name || '';
    document.getElementById('account-last-name').value = profile.last_name || '';
    document.getElementById('account-bio').value = profile.bio || '';
    document.getElementById('account-avatar-path').value = profile.avatar_path || '';

    // Tags
    document.getElementById('account-tags-input').value = (settings.tags || []).join(', ');

    // User-Agent & Proxy
    document.getElementById('account-user-agent-input').value = settings.system_version || '';
    document.getElementById('account-proxy-type').value = proxy.type || 'socks5';
    document.getElementById('account-proxy-host').value = proxy.host || '';
    document.getElementById('account-proxy-port').value = proxy.port || '';
    document.getElementById('account-proxy-user').value = proxy.user || '';
    document.getElementById('account-proxy-pass').value = proxy.pass || '';

    document.getElementById('account-settings-modal').style.display = 'block';
}

function closeAccountSettingsModal() {
    document.getElementById('account-settings-modal').style.display = 'none';
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
            alert("Settings saved to accounts.json. Click 'Apply Profile Changes' to update them on Telegram.");
            loadAccounts(); // Refresh to reflect potential data structure changes
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
        if (data.status === 'ok') {
            closeAccountSettingsModal();
        }
    });
}

// ... (rest of the file is unchanged)



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