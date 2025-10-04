let scrapedAudience = []; // Global variable to hold scraped users

document.addEventListener('DOMContentLoaded', function() {
    loadAccounts();
    loadAndDisplayAudiences(); // Load audiences on page load
});

function switchSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    document.querySelectorAll('.sidebar nav li').forEach(navItem => {
        navItem.classList.remove('active');
    });

    document.getElementById(sectionId).classList.add('active');
    document.getElementById(`nav-${sectionId}`).classList.add('active');
    
    if (sectionId === 'audiences' || sectionId === 'campaigns') {
        loadAndDisplayAudiences();
    }
    if (sectionId === 'accounts') {
        loadAccounts();
    }
}

function loadAccounts() {
    fetch('/api/accounts')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('accounts-table-body');
            const scraperAccountSelect = document.getElementById('scraper-account');
            tableBody.innerHTML = ''; 
            scraperAccountSelect.innerHTML = '';

            if (data.length === 0) {
                scraperAccountSelect.innerHTML = '<option disabled selected>No accounts available</option>';
            } else {
                 scraperAccountSelect.innerHTML = '<option disabled selected>Select an account</option>';
            }

            data.forEach(account => {
                let row = `<tr><td>${account.phone}</td><td>${account.username || 'N/A'}</td><td><button class="delete-btn" onclick="deleteAccount('${account.phone}')">Delete</button></td></tr>`;
                tableBody.innerHTML += row;

                let option = `<option value="${account.phone}">${account.phone} (${account.username || 'N/A'})</option>`;
                scraperAccountSelect.innerHTML += option;
            });
        })
        .catch(error => console.error('Error loading accounts:', error));
}

function addAccount() {
    const phone = prompt("Enter phone number (e.g., +1234567890):");
    if (!phone) return;
    alert("Processing... This may take a moment.");

    fetch('/api/accounts/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone }) })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok' && data.message === 'Verification code sent.') {
            const code = prompt("Enter the verification code:");
            if (code) finalizeConnection(phone, code, null);
        } else if (data.status === 'ok') {
            alert('Account added successfully!');
            loadAccounts();
        } else {
            alert(`Error: ${data.message}`);
        }
    }).catch(error => console.error('Error:', error));
}

function finalizeConnection(phone, code, password) {
    fetch('/api/accounts/finalize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone, code, password }) })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok' && data.message === 'Account connected successfully!') {
            alert('Account connected successfully!');
            loadAccounts();
        } else if (data.status === 'ok' && data.message === '2FA password required.') {
            const pass = prompt("Enter your 2FA password:");
            if (pass) finalizeConnection(phone, null, pass);
        } else {
            alert(`Error: ${data.message}`);
        }
    }).catch(error => console.error('Error:', error));
}

function deleteAccount(phone) {
    if (!confirm(`Delete ${phone}?`)) return;

    fetch('/api/accounts/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone }) })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            alert('Account deleted!');
            loadAccounts();
        } else {
            alert(`Error: ${data.message}`);
        }
    }).catch(error => console.error('Error:', error));
}

function scrapeAudience() {
    const phone = document.getElementById('scraper-account').value;
    const chatLink = document.getElementById('chat-link').value;
    const statusEl = document.getElementById('scraper-status');
    if (!phone || !chatLink) { alert('Please select an account and enter a chat link.'); return; }

    statusEl.textContent = 'Scraping... This can take a while.';
    document.getElementById('audience-table-body').innerHTML = '';
    scrapedAudience = [];
    document.getElementById('save-audience-btn').style.display = 'none';

    fetch('/api/audience/scrape', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone, chat_link: chatLink }) })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            statusEl.textContent = `Found ${data.users.length} users.`;
            scrapedAudience = data.users;
            populateAudienceTable(scrapedAudience);
            if(scrapedAudience.length > 0) document.getElementById('save-audience-btn').style.display = 'block';
        } else {
            statusEl.textContent = `Error: ${data.message}`;
        }
    }).catch(error => statusEl.textContent = 'An unexpected error occurred.');
}

function populateAudienceTable(users) {
    const tableBody = document.getElementById('audience-table-body');
    tableBody.innerHTML = '';
    users.forEach(user => {
        const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
        tableBody.innerHTML += `<tr><td>${user.id}</td><td>${user.username || 'N/A'}</td><td>${fullName || 'N/A'}</td></tr>`;
    });
}

function saveAudience() {
    if (scrapedAudience.length === 0) { alert("No audience to save."); return; }
    
    const chatName = document.getElementById('chat-link').value.replace(/[^a-zA-Z0-9]/g, '_');
    const defaultFilename = `audience_${chatName || 'export'}_${new Date().toISOString().slice(0,10)}`;
    const filename = prompt("Enter a name for this audience:", defaultFilename);

    if (!filename) return;

    fetch('/api/audiences/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ filename, users: scrapedAudience }) })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        if(data.status === 'ok') loadAndDisplayAudiences();
    }).catch(error => console.error('Save error:', error));
}

function loadAndDisplayAudiences() {
    fetch('/api/audiences')
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'ok') { console.error('Failed to load audiences:', data.message); return; }
        
        const list = document.getElementById('saved-audiences-list');
        const select = document.getElementById('campaign-audience-select');
        
        if(list) {
            list.innerHTML = data.audiences.length ? '' : '<li>No saved audiences.</li>';
            data.audiences.forEach(name => { list.innerHTML += `<li>${name}</li>`; });
        }
        if(select) {
            select.innerHTML = '<option disabled selected>Select an audience</option>';
            data.audiences.forEach(name => { select.innerHTML += `<option value="${name}">${name}</option>`; });
        }
    }).catch(error => console.error('Load error:', error));
}
