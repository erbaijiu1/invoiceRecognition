// ===== Tabs & Ledger Logic =====
document.addEventListener('DOMContentLoaded', () => {
    const tabUpload = document.getElementById('tab-upload');
    const tabLedger = document.getElementById('tab-ledger');
    const viewUpload = document.getElementById('view-upload');
    const viewLedger = document.getElementById('view-ledger');
    
    if(!tabUpload || !tabLedger) return;

    tabUpload.addEventListener('click', () => {
        tabUpload.classList.add('active');
        tabLedger.classList.remove('active');
        viewUpload.style.display = 'block';
        viewLedger.style.display = 'none';
    });

    tabLedger.addEventListener('click', () => {
        tabLedger.classList.add('active');
        tabUpload.classList.remove('active');
        viewUpload.style.display = 'none';
        viewLedger.style.display = 'block';
        loadLedger();
    });

    const btnSearchLedger = document.getElementById('btn-search-ledger');
    const searchInput = document.getElementById('ledger-search');
    const btnExportLedger = document.getElementById('btn-export-ledger');

    let currentPage = 1;
    let pageSize = 100;

    btnSearchLedger.addEventListener('click', () => {
        currentPage = 1;
        loadLedger(searchInput.value);
    });
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentPage = 1;
            loadLedger(searchInput.value);
        }
    });

    const btnPrevPage = document.getElementById('btn-prev-page');
    const btnNextPage = document.getElementById('btn-next-page');
    const pageSizeSelect = document.getElementById('page-size-select');
    const paginationContainer = document.getElementById('ledger-pagination');

    btnPrevPage.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadLedger(searchInput.value);
        }
    });

    btnNextPage.addEventListener('click', () => {
        const totalPages = parseInt(document.getElementById('page-count').textContent) || 1;
        if (currentPage < totalPages) {
            currentPage++;
            loadLedger(searchInput.value);
        }
    });

    pageSizeSelect.addEventListener('change', (e) => {
        pageSize = parseInt(e.target.value);
        currentPage = 1;
        loadLedger(searchInput.value);
    });

    async function loadLedger(query = '') {
        const tbody = document.getElementById('ledger-body');
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">加载中...</td></tr>';
        
        try {
            const res = await fetch(`/invoice/api/ledger?query=${encodeURIComponent(query)}&page=${currentPage}&page_size=${pageSize}`);
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error || 'Server error');
            
            document.getElementById('ledger-count').textContent = data.total || data.results.length;
            
            // Update pagination info
            if (data.total !== undefined) {
                const totalPages = Math.ceil(data.total / pageSize) || 1;
                document.getElementById('page-total').textContent = data.total;
                document.getElementById('page-current').textContent = data.page;
                document.getElementById('page-count').textContent = totalPages;
                
                btnPrevPage.disabled = data.page <= 1;
                btnNextPage.disabled = data.page >= totalPages;
                
                paginationContainer.style.display = 'flex';
            } else {
                paginationContainer.style.display = 'none';
            }
            tbody.innerHTML = '';
            
            if (data.results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #888;">暂无记录</td></tr>';
                return;
            }

            data.results.forEach((r, idx) => {
                const tr = document.createElement('tr');
                const rowNum = (currentPage - 1) * pageSize + idx + 1;
                tr.innerHTML = `
                    <td class="row-index">${rowNum}</td>
                    <td>${r.recognition_time}</td>
                    <td>${r.filename || ''}</td>
                    <td>${r.invoice_type || ''}</td>
                    <td>${r.digital_invoice_number || r.invoice_number || ''}</td>
                    <td>${r.buyer_name || ''}</td>
                    <td>${r.seller_name || ''}</td>
                    <td class="amount">${parseFloat(r.amount||0).toLocaleString('zh-CN', {minimumFractionDigits: 2})}</td>
                    <td class="amount">${parseFloat(r.total_amount||0).toLocaleString('zh-CN', {minimumFractionDigits: 2})}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="9" class="error-cell">加载失败: ${err.message}</td></tr>`;
        }
    }

    btnExportLedger.addEventListener('click', () => {
        const rows = document.querySelectorAll('#ledger-table tr');
        let csvContent = "data:text/csv;charset=utf-8,\uFEFF";
        
        for (let i = 0; i < rows.length; i++) {
            let row = [], cols = rows[i].querySelectorAll('td, th');
            for (let j = 0; j < cols.length; j++) 
                row.push('"' + cols[j].innerText.replace(/"/g, '""') + '"');
            csvContent += row.join(",") + "\r\n";
        }
        
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "发票台账.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
});
