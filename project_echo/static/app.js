let scrapedAudience = []; // Global variable to hold scraped users

document.addEventListener('DOMContentLoaded', function() {
    // Load initial data for the default view
    loadAccounts();
});

function switchSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
        section.classList.remove('active');
    });

    // Remove active class from all nav items
    document.querySelectorAll('.sidebar nav li').forEach(navItem => {
        navItem.classList.remove('active');
    });

    // Show the target section and mark nav item as active
    document.getElementById(sectionId).style.display = 'block';
    document.getElementById(sectionId).classList.add('active');
    document.getElementById(`nav-${sectionId}`).classList.add('active');
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
                let row = `<tr>
                            <td>${account.phone}</td>
                            <td>${account.username || 'N/A'}</td>
                            <td><button class="delete-btn" onclick="deleteAccount('${account.phone}')">Delete</button></td>
                           </tr>`;
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

    // Simple status update
    alert("Processing... This may take a moment.");

    fetch('/api/accounts/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok' && data.message === 'Verification code sent.') {
            const code = prompt("Enter the verification code sent to your Telegram:");
            if (code) {
                finalizeConnection(phone, code, null);
            }
        } else if (data.status === 'ok' && data.message === 'Account already authorized and added.'){
            alert('Account added successfully!');
            loadAccounts();
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error adding account:', error);
        alert('An unexpected error occurred. Check the console for details.');
    });
}

function finalizeConnection(phone, code, password) {
    fetch('/api/accounts/finalize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, code, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok' && data.message === 'Account connected successfully!') {
            alert('Account connected successfully!');
            loadAccounts();
        } else if (data.status === 'ok' && data.message === '2FA password required.') {
            const password = prompt("Enter your 2FA password:");
            if (password) {
                finalizeConnection(phone, null, password);
            }
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error finalizing connection:', error);
        alert('An unexpected error occurred. Check the console for details.');
    });
}

function deleteAccount(phone) {
    if (!confirm(`Are you sure you want to delete the account ${phone}? This cannot be undone.`)) {
        return;
    }

    fetch('/api/accounts/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            alert('Account deleted successfully!');
            loadAccounts();
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error deleting account:', error);
        alert('An unexpected error occurred. Check the console for details.');
    });
}

function scrapeAudience() {
    const phone = document.getElementById('scraper-account').value;
    const chatLink = document.getElementById('chat-link').value;
    const statusEl = document.getElementById('scraper-status');
    const tableBody = document.getElementById('audience-table-body');

    if (!phone || phone === 'Select an account') {
        alert('Please select a valid account.');
        return;
    }
    if (!chatLink) {
        alert('Please enter a target chat link or username.');
        return;
    }

    statusEl.textContent = 'Scraping in progress... This may take a while depending on the chat size.';
    tableBody.innerHTML = '';
    scrapedAudience = [];
    document.getElementById('save-audience-btn').style.display = 'none';

    fetch('/api/audience/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, chat_link: chatLink })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            statusEl.textContent = `Scraping complete! Found ${data.users.length} users.`;
            scrapedAudience = data.users;
            populateAudienceTable(scrapedAudience);
            if(scrapedAudience.length > 0){
                 document.getElementById('save-audience-btn').style.display = 'block';
            }
        } else {
            statusEl.textContent = `Error: ${data.message}`;
        }
    })
    .catch(error => {
        console.error('Error scraping audience:', error);
        statusEl.textContent = 'An unexpected error occurred.';
    });
}

function populateAudienceTable(users) {
    const tableBody = document.getElementById('audience-table-body');
    tableBody.innerHTML = '';
    users.forEach(user => {
        const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
        let row = `<tr>
                    <td>${user.id}</td>
                    <td>${user.username || 'N/A'}</td>
                    <td>${fullName || 'N/A'}</td>
                   </tr>`;
        tableBody.innerHTML += row;
    });
}

function saveAudience() {
    if (scrapedAudience.length === 0) {
        alert("No audience to save.");
        return;
    }

    const chatLink = document.getElementById('chat-link').value.replace(/[^a-zA-Z0-9]/g, '_');
    const filename = `audience_${chatLink || 'export'}_${new Date().toISOString().slice(0,10)}.csv`;
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "UserID,Username,FirstName,LastName\r\n";

    scrapedAudience.forEach(user => {
        const row = `${user.id},${user.username || ''},${user.first_name || ''},${user.last_name || ''}`;
        csvContent += row + "\r\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
