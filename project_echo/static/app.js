let scrapedAudience = [];

document.addEventListener('DOMContentLoaded', () => {
    switchSection('dashboard');
});

function switchSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar nav li').forEach(i => i.classList.remove('active'));

    document.getElementById(sectionId)?.classList.add('active');
    document.getElementById(`nav-${sectionId}`)?.classList.add('active');

    if (sectionId === 'accounts') loadAccounts();
    if (sectionId === 'audiences') { loadAccounts(); loadAndDisplayAudiences(); }
    if (sectionId === 'campaigns') { loadCampaigns(); loadAccountsForCampaign(); loadAndDisplayAudiences(); }
}

// ... (Account and Audience functions) ...
function loadAccounts() {
    fetch('/api/accounts').then(r => r.json()).then(data => {
        const tableBody = document.getElementById('accounts-table-body');
        const scraperSelect = document.getElementById('scraper-account');
        tableBody.innerHTML = '';
        scraperSelect.innerHTML = '<option disabled selected>Select an account</option>';
        data.forEach(acc => {
            tableBody.innerHTML += `<tr><td>${acc.phone}</td><td>${acc.username || 'N/A'}</td><td><button class="delete-btn" onclick="deleteAccount('${acc.phone}')">Delete</button></td></tr>`;
            scraperSelect.innerHTML += `<option value="${acc.phone}">${acc.phone} (${acc.username || 'N/A'})</option>`;
        });
    }).catch(e => console.error('Error loading accounts:', e));
}

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
        if(data.status === 'ok') loadCampaigns(); // Refresh to show 'In Progress' status
    });
}

function editCampaign(campaignId) {
    // This would fetch the specific campaign details and populate the form
    // For now, it's just a placeholder.
    alert("Editing functionality to be fully implemented. For now, create a new campaign.");
}

function toggleCampaignForm(show) {
    document.getElementById('campaign-form-container').style.display = show ? 'block' : 'none';
    document.getElementById('campaign-list-view').style.display = show ? 'none' : 'block';
    if (!show) { // Clear form
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

    if (!campaign.name || !campaign.message || !campaign.audience) {
        return alert('Please fill all fields.');
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

// ... Add other placeholder functions if needed, like addAccount, etc.
// Make sure all required functions are present or stubbed.
