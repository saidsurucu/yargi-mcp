document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const searchQuery = document.getElementById('searchQuery');
    const courtType = document.getElementById('courtType');
    const results = document.getElementById('results');
    const resultsContent = document.getElementById('resultsContent');
    const loading = document.getElementById('loading');

    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const query = searchQuery.value.trim();
        if (!query) {
            alert('Lütfen arama terimi girin!');
            return;
        }

        // Show loading
        loading.style.display = 'block';
        results.style.display = 'none';
        
        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    court_type: courtType.value
                })
            });

            const data = await response.json();
            
            if (data.success) {
                displayResults(data.results);
            } else {
                displayError(data.error || 'Arama başarısız!');
            }
        } catch (error) {
            console.error('Arama hatası:', error);
            displayError('Bağlantı hatası! Lütfen tekrar deneyin.');
        } finally {
            loading.style.display = 'none';
        }
    });

    function displayResults(results) {
        if (!results || results.length === 0) {
            resultsContent.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i>
                    Sonuç bulunamadı. Farklı arama terimleri deneyebilirsiniz.
                </div>
            `;
        } else {
            resultsContent.innerHTML = results.map(result => `
                <div class="result-card">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="court-badge">${result.court || 'Bilinmeyen Mahkeme'}</span>
                        <span class="date-badge">${result.date || 'Tarih Yok'}</span>
                    </div>
                    <h5 class="mb-2">${result.title || 'Başlık Yok'}</h5>
                    <p class="text-muted mb-2">${result.summary || 'Özet mevcut değil'}</p>
                    <div class="mt-3">
                        <button class="btn btn-outline-primary btn-sm" onclick="viewDocument('${result.id}')">
                            📖 Detayı Gör
                        </button>
                        <button class="btn btn-outline-secondary btn-sm ms-2" onclick="copyLink('${result.id}')">
                            🔗 Linki Kopyala
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        results.style.display = 'block';
        results.scrollIntoView({ behavior: 'smooth' });
    }

    function displayError(message) {
        resultsContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i>
                ${message}
            </div>
        `;
        results.style.display = 'block';
    }

    // Global functions
    window.viewDocument = function(documentId) {
        window.open(`/document/${documentId}`, '_blank');
    };

    window.copyLink = function(documentId) {
        const url = `${window.location.origin}/document/${documentId}`;
        navigator.clipboard.writeText(url).then(() => {
            // Simple toast notification
            const toast = document.createElement('div');
            toast.className = 'position-fixed top-0 end-0 p-3';
            toast.style.zIndex = '9999';
            toast.innerHTML = `
                <div class="toast show" role="alert">
                    <div class="toast-body">
                        📋 Link kopyalandı!
                    </div>
                </div>
            `;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        });
    };

    // Enter key support
    searchQuery.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchForm.dispatchEvent(new Event('submit'));
        }
    });
});
