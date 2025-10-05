/**
 * Handles the tab switching event from the <md-tabs> component.
 */
function handleTabChange(event) {
    // The detail object contains the index of the selected tab
    const selectedIndex = event.detail.selectedTabIndex;
    const tabs = document.querySelectorAll('md-primary-tab');
    
    if (tabs[selectedIndex]) {
        // Get the ID of the panel this tab controls
        const panelId = tabs[selectedIndex].getAttribute('aria-controls');
        switchPanel(panelId);
    }
}

/**
 * Switches the visible content panel.
 * @param {string} panelId The ID of the panel to show.
 */
function switchPanel(panelId) {
    // Hide all content panels
    document.querySelectorAll('.content-panel').forEach(panel => {
        panel.style.display = 'none';
    });

    // Show the selected panel
    const activePanel = document.getElementById(panelId);
    if (activePanel) {
        activePanel.style.display = 'block';
    }
}

// Initialize the view on first load
document.addEventListener('DOMContentLoaded', () => {
    // We are setting the "Accounts" tab as active by default in the HTML
    // so no initial switch is needed here.
});
