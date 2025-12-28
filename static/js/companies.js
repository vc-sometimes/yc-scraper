// Companies page JavaScript

let allCompanies = [];

async function loadCompanies(search = '') {
    const loading = document.getElementById('loading');
    const container = document.getElementById('companies-container');
    const noResults = document.getElementById('no-results');
    
    loading.style.display = 'block';
    container.innerHTML = '';
    noResults.style.display = 'none';
    
    try {
        const url = search ? `/api/companies?search=${encodeURIComponent(search)}` : '/api/companies';
        const response = await fetch(url);
        const companies = await response.json();
        
        allCompanies = companies;
        loading.style.display = 'none';
        
        if (companies.length === 0) {
            noResults.style.display = 'block';
            return;
        }
        
        companies.forEach(company => {
            const card = document.createElement('div');
            card.className = 'company-card';
            card.innerHTML = `
                <div class="company-name">${company.name}</div>
                ${company.batch ? `<div class="company-info">📅 Batch: ${company.batch}</div>` : ''}
                ${company.location ? `<div class="company-info">📍 ${company.location}</div>` : ''}
                ${company.industry ? `<div class="company-info">🏷️ ${company.industry}</div>` : ''}
                ${company.is_hiring ? `<div class="company-info">✅ Hiring</div>` : ''}
                <a href="${company.yc_url}" target="_blank" class="company-url">View on YC →</a>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading companies:', error);
        loading.textContent = 'Error loading companies. Please try again.';
    }
}

function searchCompanies() {
    const searchInput = document.getElementById('search-input');
    const searchTerm = searchInput.value.trim();
    loadCompanies(searchTerm);
}

// Allow Enter key to trigger search
document.getElementById('search-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchCompanies();
    }
});

// Load companies on page load
loadCompanies();

