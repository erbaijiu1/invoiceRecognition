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

    btnSearchLedger.addEventListener('click', () => loadLedger(searchInput.value));
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') loadLedger(searchInput.value);
    });

    async function loadLedger(query = '') {
        const tbody = document.getElementById('ledger-body');
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">加载中...</td></tr>';
        
        try {
            const res = await fetch('/invoice/api/ledger?query=' + encodeURIComponent(query));
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error || 'Server error');
            
            document.getElementById('ledger-count').textContent = data.results.length;
            tbody.innerHTML = '';
            
            if (data.results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #888;">暂无记录</td></tr>';
                return;
            }

            data.results.forEach((r, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="row-index">${idx + 1}</td>
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
