/**
 * Switches the visible content section based on the navigation item clicked.
 * @param {string} sectionId The ID of the section to show.
 */
function switchSection(sectionId) {
    // Hide all content sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
    });

    // Show the selected section
    const activeSection = document.getElementById(sectionId);
    if (activeSection) {
        activeSection.style.display = 'block';
    }

    // Update the active state in the navigation rail
    // Note: The Material 3 components might handle this automatically based on 
    // other interactions, but we'll be explicit for clarity.
    document.querySelectorAll('.nav-item').forEach(item => {
        item.active = (item.id === `nav-${sectionId}`);
    });
}

// Initialize the view on first load
document.addEventListener('DOMContentLoaded', () => {
    // No initial switch needed, handled by default HTML visibility
});
