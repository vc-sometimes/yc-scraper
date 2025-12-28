// Dashboard JavaScript

async function loadStats() {
    try {
        console.log('Loading stats...');
        const response = await fetch('/api/stats');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const stats = await response.json();
        console.log('Stats loaded:', stats);
        
        document.getElementById('total-companies').textContent = stats.total_companies.toLocaleString();
        document.getElementById('total-members').textContent = (stats.total_founders || stats.total_members || 0).toLocaleString();
        document.getElementById('companies-with-members').textContent = (stats.companies_with_founders || stats.companies_with_members || 0).toLocaleString();
        
        // Top Companies Chart
        if (stats.top_companies.length > 0) {
            const topCompaniesCtx = document.getElementById('topCompaniesChart').getContext('2d');
            new Chart(topCompaniesCtx, {
                type: 'bar',
                data: {
                    labels: stats.top_companies.map(c => c.company_name.split('\n')[0].substring(0, 20)),
                    datasets: [{
                        label: 'Founders',
                        data: stats.top_companies.map(c => c.founder_count || c.member_count),
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // Batch Chart
        if (stats.batch_stats.length > 0) {
            const batchCtx = document.getElementById('batchChart').getContext('2d');
            new Chart(batchCtx, {
                type: 'doughnut',
                data: {
                    labels: stats.batch_stats.map(b => b.batch || 'Unknown'),
                    datasets: [{
                        data: stats.batch_stats.map(b => b.count),
                        backgroundColor: [
                            'rgba(102, 126, 234, 0.8)',
                            'rgba(118, 75, 162, 0.8)',
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(255, 206, 86, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                        ]
                    }]
                },
                options: {
                    responsive: true
                }
            });
        }
        
        // Load recent companies
        loadRecentCompanies();
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('total-companies').textContent = 'Error';
        document.getElementById('total-members').textContent = 'Error';
        document.getElementById('companies-with-members').textContent = 'Error';
    }
}

async function loadRecentCompanies() {
    try {
        console.log('Loading recent companies...');
        const response = await fetch('/api/companies?limit=6');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const companies = await response.json();
        console.log('Companies loaded:', companies.length);
        
        const container = document.getElementById('recent-companies');
        container.innerHTML = '';
        
        companies.forEach(company => {
            const card = document.createElement('div');
            card.className = 'company-card';
            card.innerHTML = `
                <div class="company-name">${company.name}</div>
                ${company.batch ? `<div class="company-info">Batch: ${company.batch}</div>` : ''}
                ${company.location ? `<div class="company-info">📍 ${company.location}</div>` : ''}
                ${company.industry ? `<div class="company-info">🏷️ ${company.industry}</div>` : ''}
                <a href="${company.yc_url}" target="_blank" class="company-url">View on YC →</a>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading recent companies:', error);
    }
}

// Load stats on page load
loadStats();

