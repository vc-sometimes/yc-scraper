let allCompanies = [];
let filteredCompanies = [];
let currentSort = { column: null, direction: null };

// Load companies on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCompanies();
    document.getElementById('searchInput').addEventListener('input', filterTable);
    
    // Setup sortable headers
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.getAttribute('data-sort');
            sortTable(column);
        });
    });
});

async function loadCompanies() {
    try {
        const response = await fetch('/api/companies');
        allCompanies = await response.json();
        
        // Load founder counts
        await loadFounderCounts();
        
        filteredCompanies = allCompanies;
        renderTable();
    } catch (error) {
        console.error('Error loading companies:', error);
        document.getElementById('tableBody').innerHTML = 
            '<tr><td colspan="3" class="loading">Error loading companies</td></tr>';
    }
}

async function loadFounderCounts() {
    try {
        const response = await fetch('/api/founders');
        const founders = await response.json();
        
        // Group founders by company
        const foundersByCompany = {};
        founders.forEach(founder => {
            const companyName = founder.company_name || founder.company_display_name;
            if (companyName) {
                const cleanName = companyName.split('\n')[0];
                if (!foundersByCompany[cleanName]) {
                    foundersByCompany[cleanName] = [];
                }
                foundersByCompany[cleanName].push(founder);
            }
        });
        
        // Add founders to companies
        allCompanies.forEach(company => {
            const cleanName = company.name.split('\n')[0];
            company.founders = foundersByCompany[cleanName] || [];
        });
    } catch (error) {
        console.error('Error loading founder counts:', error);
    }
}

function filterTable() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    filteredCompanies = allCompanies.filter(company => {
        const name = (company.name || '').toLowerCase();
        return !searchTerm || name.includes(searchTerm);
    });
    
    // Reapply current sort
    if (currentSort.column) {
        sortTable(currentSort.column, currentSort.direction, false);
    } else {
        renderTable();
    }
}

function sortTable(column, direction = null, updateFiltered = true) {
    // Determine sort direction
    if (direction === null) {
        if (currentSort.column === column) {
            // Toggle direction
            direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            direction = 'asc';
        }
    }
    
    currentSort = { column, direction };
    
    // Update UI indicators
    document.querySelectorAll('.sortable').forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc');
        if (header.getAttribute('data-sort') === column) {
            header.classList.add(`sort-${direction}`);
        }
    });
    
    // Sort the data
    const companiesToSort = updateFiltered ? filteredCompanies : allCompanies;
    
    companiesToSort.sort((a, b) => {
        let aValue, bValue;
        
        if (column === 'name') {
            aValue = (a.name || '').toLowerCase();
            bValue = (b.name || '').toLowerCase();
        } else if (column === 'founders') {
            aValue = (a.founders || []).length;
            bValue = (b.founders || []).length;
        } else if (column === 'batch') {
            aValue = (a.batch || '').toLowerCase();
            bValue = (b.batch || '').toLowerCase();
        }
        
        if (aValue < bValue) return direction === 'asc' ? -1 : 1;
        if (aValue > bValue) return direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    if (updateFiltered) {
        renderTable();
    }
}

async function updateCounter() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        const total = stats.total_companies || 0;
        const withFounders = stats.companies_with_founders || 0;
        const totalFounders = stats.total_founders || 0;
        
        const counterText = document.getElementById('counterText');
        if (counterText) {
            counterText.textContent = `${withFounders}/${total} companies with founders • ${totalFounders} founders total`;
        }
    } catch (error) {
        console.error('Error updating counter:', error);
    }
}

function renderTable() {
    const tbody = document.getElementById('tableBody');
    
    if (filteredCompanies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="loading">No companies found</td></tr>';
        return;
    }
    
    tbody.innerHTML = filteredCompanies.map(company => {
        // Clean company name - take first line only, remove location if concatenated
        let cleanName = company.name ? company.name.split('\n')[0] : '';
        // Remove location patterns that are concatenated (e.g., "CompanyNameSan Francisco, CA, USA")
        // Match: city name followed by ", XX, USA" or ", Country" at the end
        cleanName = cleanName.replace(/, [A-Z]{2}, USA$/, '') // Remove ", CA, USA" etc
            .replace(/, (United States|USA|United Kingdom|UK|Canada|Germany|France|Spain|Italy|Netherlands|Belgium|Switzerland|Austria|Sweden|Norway|Denmark|Finland|Poland|Czech Republic|Hungary|Romania|Bulgaria|Greece|Portugal|Ireland|Croatia|Slovenia|Slovakia|Lithuania|Latvia|Estonia|Luxembourg|Malta|Cyprus|Iceland|Liechtenstein|Monaco|San Marino|Vatican City|Andorra|Gibraltar|Australia|New Zealand|Japan|South Korea|China|India|Singapore|Hong Kong|Taiwan|Thailand|Malaysia|Indonesia|Philippines|Vietnam|Cambodia|Laos|Myanmar|Bangladesh|Sri Lanka|Pakistan|Nepal|Bhutan|Maldives|Afghanistan|Iran|Iraq|Saudi Arabia|UAE|Qatar|Kuwait|Bahrain|Oman|Yemen|Jordan|Lebanon|Syria|Israel|Palestine|Turkey|Cyprus|Georgia|Armenia|Azerbaijan|Kazakhstan|Uzbekistan|Turkmenistan|Tajikistan|Kyrgyzstan|Mongolia|North Korea|Russia|Belarus|Ukraine|Moldova|Serbia|Montenegro|Bosnia and Herzegovina|North Macedonia|Albania|Kosovo)$/i, '')
            .replace(/(San Francisco|New York|Los Angeles|Boston|Seattle|Austin|Chicago|Denver|Miami|Portland|Remote|Berlin|London|Toronto|Vancouver|Tel Aviv|Bangalore|Singapore|Tokyo|Sydney|Melbourne|Paris|Amsterdam|Stockholm|Copenhagen|Zurich|Dublin|Madrid|Barcelona|Milan|Rome|Vienna|Prague|Warsaw|Helsinki|Oslo|Brussels|Lisbon|Athens|Dubai|Hong Kong|Shanghai|Beijing|Mumbai|Delhi|Hyderabad|Chennai|Pune|Kolkata|Jakarta|Manila|Bangkok|Hanoi|Seoul|Taipei|Kuala Lumpur|Mexico City|São Paulo|Rio de Janeiro|Buenos Aires|Santiago|Lima|Bogotá|Caracas|Montevideo|Lagos|Nairobi|Cairo|Johannesburg|Cape Town|Casablanca|Tunis|Algiers|Accra|Addis Ababa|Dakar|Kampala|Dar es Salaam|Kigali|Khartoum|Kinshasa|Luanda|Maputo|Harare|Lusaka|Windhoek|Gaborone|Mbabane|Maseru|Libreville|Yaoundé|Douala|Abidjan|Ouagadougou|Bamako|Niamey|Nouakchott|Banjul|Bissau|Conakry|Freetown|Monrovia|Brazzaville|Bujumbura|Djibouti|Asmara|Malabo|Moroni|Victoria|Port Louis|Saint-Denis|Saint-Pierre|Kingston|Port-au-Prince|Santo Domingo|Havana|San Juan|Nassau|Bridgetown|Castries|Kingstown|Roseau|St\. John's|Basseterre|St\. George's|Hamilton|Road Town|The Valley|Cockburn Town|George Town|Oranjestad|Willemstad|Philipsburg|Marigot|Gustavia|Basse-Terre|Fort-de-France|Pointe-à-Pitre|Saint-Pierre|Miquelon|Saint-Barthélemy|Saint-Martin|Bonaire|Saba|Sint Eustatius|Sint Maarten|Anguilla|Montserrat|Turks and Caicos|British Virgin Islands|Cayman Islands|Bermuda|Falkland Islands|South Georgia|Saint Helena|Ascension|Tristan da Cunha|Pitcairn|Tokelau|Niue|Cook Islands|American Samoa|Guam|Northern Mariana Islands|Puerto Rico|US Virgin Islands|Wake Island|Midway Atoll|Johnston Atoll|Palmyra Atoll|Baker Island|Howland Island|Jarvis Island|Kingman Reef|Navassa Island|Serranilla Bank|Bajo Nuevo Bank|Clipperton Island|Revillagigedo Islands|Socorro Island|Clarion Island|San Benedicto Island|Roca Partida|Guadalupe Island|Cedros Island|Natividad Island|San Roque Island|Asunción Island|San Martín Island|San Jerónimo Island|San Esteban Island|Tiburón Island|Ángel de la Guarda Island|Partida Norte Island|Partida Sur Island|Espíritu Santo Island|San José Island|San Francisco Island|San Diego Island|Coronados Islands|Todos Santos Islands)$/i, '')
            .trim();
        
        const founders = company.founders || [];
        
        let foundersDisplay = '';
        if (founders.length > 0) {
            foundersDisplay = founders.map((f, idx) => {
                const roleText = f.role ? ` (${f.role})` : '';
                return `<a href="#" class="founder-link" onclick="event.stopPropagation(); showFounderPopup(${company.id}, ${idx}); return false;">${f.name}${roleText}</a>`;
            }).join(', ');
        } else {
            foundersDisplay = '<span style="color: #9b9a97; font-style: italic;">No founders</span>';
        }
        
        const ycLink = company.yc_url ? `<a href="${company.yc_url}" target="_blank" class="company-link" onclick="event.stopPropagation();">${cleanName}</a>` : cleanName;
        const batchDisplay = company.batch ? `<span class="batch-badge">${company.batch}</span>` : '<span style="color: #9b9a97; font-style: italic;">—</span>';
        
        return `
            <tr onclick="showCompanyDetails(${company.id})">
                <td class="company-name">${ycLink}</td>
                <td class="batch-cell">${batchDisplay}</td>
                <td class="founders-cell">${foundersDisplay}</td>
            </tr>
        `;
    }).join('');
}

async function showCompanyDetails(companyId) {
    try {
        const response = await fetch(`/api/companies/${companyId}`);
        const company = await response.json();
        
        const cleanName = company.name.split('\n')[0];
        document.getElementById('detailsCompanyName').textContent = cleanName;
        
        // Display founders
        const foundersList = document.getElementById('foundersList');
        if (company.founders && company.founders.length > 0) {
            foundersList.innerHTML = company.founders.map((founder, idx) => {
                let links = '';
                if (founder.linkedin_url) {
                    links += `<a href="${founder.linkedin_url}" target="_blank">LinkedIn</a>`;
                }
                if (founder.twitter_url) {
                    links += `<a href="${founder.twitter_url}" target="_blank">Twitter/X</a>`;
                }
                if (founder.yc_profile_url) {
                    links += `<a href="${founder.yc_profile_url}" target="_blank">YC Profile</a>`;
                }
                
                return `
                    <div class="founder-item">
                        <div class="founder-name">
                            <a href="#" class="founder-link" onclick="event.stopPropagation(); showFounderPopup(${companyId}, ${idx}); return false;">${founder.name}</a>
                        </div>
                        ${founder.role ? `<div class="founder-role">${founder.role}</div>` : ''}
                        ${links ? `<div class="founder-links">${links}</div>` : ''}
                    </div>
                `;
            }).join('');
        } else {
            foundersList.innerHTML = '<div class="no-founders">No founders found</div>';
        }
        
        document.getElementById('companyDetails').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading company details:', error);
        alert('Error loading company details');
    }
}

async function showFounderPopup(companyId, founderIndex) {
    try {
        const response = await fetch(`/api/companies/${companyId}`);
        const company = await response.json();
        
        if (!company.founders || !company.founders[founderIndex]) {
            return;
        }
        
        const founder = company.founders[founderIndex];
        
        // Create popup HTML
        let linksHTML = '';
        if (founder.linkedin_url) {
            linksHTML += `<a href="${founder.linkedin_url}" target="_blank" class="social-link linkedin">LinkedIn</a>`;
        }
        if (founder.twitter_url) {
            linksHTML += `<a href="${founder.twitter_url}" target="_blank" class="social-link twitter">Twitter/X</a>`;
        }
        if (founder.yc_profile_url) {
            linksHTML += `<a href="${founder.yc_profile_url}" target="_blank" class="social-link yc">YC Profile</a>`;
        }
        
        if (!linksHTML) {
            linksHTML = '<div class="no-socials">No social links available</div>';
        }
        
        const popupHTML = `
            <div class="founder-popup" id="founderPopup">
                <div class="popup-content">
                    <div class="popup-header">
                        <h3>${founder.name}</h3>
                        <button class="popup-close" onclick="closeFounderPopup()">×</button>
                    </div>
                    <div class="popup-body">
                        ${founder.role ? `<div class="popup-role">${founder.role}</div>` : ''}
                        <div class="popup-links">
                            ${linksHTML}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing popup if any
        const existingPopup = document.getElementById('founderPopup');
        if (existingPopup) {
            existingPopup.remove();
        }
        
        // Add popup to body
        document.body.insertAdjacentHTML('beforeend', popupHTML);
        
        // Close on outside click
        document.getElementById('founderPopup').addEventListener('click', (e) => {
            if (e.target.id === 'founderPopup') {
                closeFounderPopup();
            }
        });
        
    } catch (error) {
        console.error('Error loading founder details:', error);
    }
}

function closeFounderPopup() {
    const popup = document.getElementById('founderPopup');
    if (popup) {
        popup.remove();
    }
}

function closeDetails() {
    document.getElementById('companyDetails').classList.add('hidden');
}

// Close details when clicking outside
document.getElementById('companyDetails').addEventListener('click', (e) => {
    if (e.target.id === 'companyDetails') {
        closeDetails();
    }
});

// Close details with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeDetails();
        closeFounderPopup();
    }
});
