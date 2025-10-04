
document.addEventListener('DOMContentLoaded', function() {
    loadAccounts();
});

function loadAccounts() {
    fetch('/api/accounts')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('accounts-table-body');
            tableBody.innerHTML = ''; // Clear existing data
            data.forEach(account => {
                let row = `<tr>
                            <td>${account.phone}</td>
                            <td>${account.username || 'N/A'}</td>
                           </tr>`;
                tableBody.innerHTML += row;
            });
        })
        .catch(error => console.error('Error loading accounts:', error));
}

function addAccount() {
    // Only prompt for the phone number
    const phone = prompt("Enter phone number (e.g., +1234567890):");
    if (!phone) return;

    // Send initial request with just the phone number
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
        } else if (data.status === 'ok' && data.message === '2FA password required.') {
            const password = prompt("Enter your 2FA password:");
            if (password) {
                finalizeConnection(phone, null, password);
            }
        } else if (data.status === 'ok') {
            alert('Account added successfully!');
            loadAccounts(); // Refresh the list
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
        if (data.status === 'ok') {
            alert('Account connected successfully!');
            loadAccounts(); // Refresh the list
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error finalizing connection:', error);
        alert('An unexpected error occurred. Check the console for details.');
    });
}
