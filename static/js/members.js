// Members page JavaScript

let allMembers = [];

async function loadMembers(search = '') {
    const loading = document.getElementById('loading');
    const container = document.getElementById('members-container');
    const noResults = document.getElementById('no-results');
    
    loading.style.display = 'block';
    container.innerHTML = '';
    noResults.style.display = 'none';
    
    try {
        const url = search ? `/api/founders?search=${encodeURIComponent(search)}` : '/api/founders';
        const response = await fetch(url);
        const members = await response.json();
        
        allMembers = members;
        loading.style.display = 'none';
        
        if (members.length === 0) {
            noResults.style.display = 'block';
            return;
        }
        
        members.forEach(member => {
            const card = document.createElement('div');
            card.className = 'member-card';
            
            const links = [];
            if (member.yc_profile_url) {
                links.push(`<a href="${member.yc_profile_url}" target="_blank" class="member-link">YC Profile</a>`);
            }
            if (member.linkedin_url) {
                links.push(`<a href="${member.linkedin_url}" target="_blank" class="member-link">LinkedIn</a>`);
            }
            if (member.twitter_url) {
                links.push(`<a href="${member.twitter_url}" target="_blank" class="member-link">Twitter</a>`);
            }
            if (member.email) {
                links.push(`<a href="mailto:${member.email}" class="member-link">Email</a>`);
            }
            
            card.innerHTML = `
                <div class="member-name">${member.name}</div>
                <div class="member-company">${member.company_name || member.company_display_name || 'Unknown Company'}</div>
                ${member.role ? `<div class="member-role">${member.role}</div>` : ''}
                ${member.previous_company ? `<div class="member-role" style="color: #888; font-size: 0.85rem;">Previous: ${member.previous_company}</div>` : ''}
                ${member.bio ? `<div class="member-bio" style="color: #666; font-size: 0.85rem; margin-top: 0.5rem;">${member.bio.substring(0, 100)}...</div>` : ''}
                ${links.length > 0 ? `<div class="member-links">${links.join('')}</div>` : ''}
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading members:', error);
        loading.textContent = 'Error loading team members. Please try again.';
    }
}

function searchMembers() {
    const searchInput = document.getElementById('search-input');
    const searchTerm = searchInput.value.trim();
    loadMembers(searchTerm);
}

// Allow Enter key to trigger search
document.getElementById('search-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchMembers();
    }
});

// Load members on page load
loadMembers();

