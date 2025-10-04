
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
    // We will implement this functionality in the next steps
    alert('Add account functionality will be implemented soon!');
}
