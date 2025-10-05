let currentAccount = null; // Holds the account object being edited
let scrapedAudience = []; // Holds the result of a scrape before saving
let campaignIntervalId = null; // To hold the interval for campaign polling

document.addEventListener('DOMContentLoaded', () => {
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

function switchSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(s => s.style.display = 'none');
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));

    if (campaignIntervalId) {
        clearInterval(campaignIntervalId);
        campaignIntervalId = null;
    }

    const section = document.getElementById(sectionId);
    if(section) section.style.display = 'block';

    const navItem = document.getElementById(`nav-${sectionId}`) || document.getElementById(`nav-${sectionId.split('-')[0]}`);
    if(navItem) navItem.classList.add('active');

    if (sectionId === 'accounts') loadAccounts();
    if (sectionId === 'proxies') loadProxies();
    if (sectionId === 'audiences') { 
        loadAccountsForScraper(); 
        loadAndDisplayAudiences();
    }
    if (sectionId === 'campaigns') {
        loadCampaignFormData();
        loadCampaigns();
        campaignIntervalId = setInterval(loadCampaigns, 5000); // Refresh every 5 seconds
    }
}

function apiPost(endpoint, body, callback, showAlerts = true) {
    fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.message || `HTTP error! status: ${response.status}`);
        }
        return data;
    })
    .then(data => {
        if(showAlerts && data.message) alert(data.message);
        if (callback) callback(data);
    })
    .catch(error => {
        console.error(`API Error at ${endpoint}:`, error);
        if (showAlerts) alert(error.message);
    });
}

// ... (Keep existing account, settings, proxy, tags, and audience functions as they are)
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

// ... other account functions

// --- Ad Cabinet ---
function loadCampaignFormData() {
    // Load audiences into select
    const audienceSelect = document.getElementById('campaign-audience-select');
    audienceSelect.innerHTML = '';
    fetch('/api/audiences').then(r => r.json()).then(files => {
        files.forEach(filename => {
            const option = document.createElement('md-select-option');
            option.value = filename;
            option.innerText = filename.replace('.json', '');
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
            label.innerHTML = `
                <md-checkbox value="${acc.phone}"></md-checkbox>
                <span>${acc.phone}${acc.username ? ` (${acc.username})` : ''}</span>
            `;
            accountsList.appendChild(label);
        });
    });
}

function startCampaign() {
    const name = document.getElementById('campaign-name').value;
    const audience_file = document.getElementById('campaign-audience-select').value;
    const message = document.getElementById('campaign-message').value;
    
    const selectedCheckboxes = document.querySelectorAll('#campaign-accounts-list md-checkbox:checked');
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
            const createdDate = new Date(c.created_at + 'Z').toLocaleString(); // Assuming UTC
            row.innerHTML = `
                <td>${c.name}</td>
                <td>${c.audience_file.replace('.json', '')}</td>
                <td>${c.progress || `0/${c.total_users}`}</td>
                <td><span class="status status-${c.status.toLowerCase()}">${c.status}</span></td>
                <td>${createdDate}</td>
                <td>
                    <md-icon-button onclick="deleteCampaign('${c.id}')">
                        <span class="material-symbols-outlined">delete</span>
                    </md-icon-button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    });
}

function deleteCampaign(campaignId) {
    if (!confirm('Are you sure you want to delete this campaign? This won\'t stop a running campaign, but will remove it from the list.')) return;
    apiPost('/api/campaigns/delete', { id: campaignId }, () => {
        loadCampaigns();
    }, false);
}

