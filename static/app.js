/**
 * 发票识别系统 - 前端交互逻辑
 */
(function () {
    'use strict';

    // ===== DOM Elements =====
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const btnRecognize = document.getElementById('btn-recognize');
    const btnDownload = document.getElementById('btn-download');
    const btnClear = document.getElementById('btn-clear');
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressCount = document.getElementById('progress-count');
    const progressText = document.getElementById('progress-text');
    const resultsSection = document.getElementById('results-section');
    const resultsBody = document.getElementById('results-body');
    const resultCount = document.getElementById('result-count');
    const toastContainer = document.getElementById('toast-container');
    const modelSelect = document.getElementById('model-select');

    // ===== State =====
    let selectedFiles = [];
    let recognitionResults = [];

    // 支持的文件格式
    const SUPPORTED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.tif'];

    // ===== Load Models =====
    async function loadModels() {
        try {
            const res = await fetch('/api/models');
            const data = await res.json();
            modelSelect.innerHTML = '';
            (data.models || []).forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = m.name;
                modelSelect.appendChild(opt);
            });
        } catch (e) {
            console.error('加载模型列表失败:', e);
            modelSelect.innerHTML = '<option value="">加载失败</option>';
        }
    }
    loadModels();

    // ===== Toast =====
    function showToast(message, type = 'info', duration = 3500) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '✓',
            error: '✕',
            info: 'ℹ'
        };

        toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toast-out 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    // ===== File Management =====
    function addFiles(files) {
        for (const file of files) {
            const ext = '.' + file.name.split('.').pop().toLowerCase();
            if (!SUPPORTED_EXTENSIONS.includes(ext)) {
                showToast(`${file.name} 格式不支持，已跳过`, 'error');
                continue;
            }
            // 去重
            if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                continue;
            }
            selectedFiles.push(file);
        }
        renderFileList();
        updateButtonStates();
    }

    function removeFile(index) {
        selectedFiles.splice(index, 1);
        renderFileList();
        updateButtonStates();
    }

    function renderFileList() {
        fileList.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const chip = document.createElement('div');
            chip.className = 'file-chip';
            const sizeMB = (file.size / 1024 / 1024).toFixed(1);
            const ext = '.' + file.name.split('.').pop().toLowerCase();
            const icon = ext === '.pdf' ? '📄' : '🖼️';
            chip.innerHTML = `
                <span class="file-icon">${icon}</span>
                <span>${file.name}</span>
                <span style="color: var(--text-muted); font-size: 0.78rem;">(${sizeMB}MB)</span>
                <button class="remove-btn" data-index="${index}" title="移除">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            `;
            fileList.appendChild(chip);
        });
    }

    function updateButtonStates() {
        btnRecognize.disabled = selectedFiles.length === 0;
        btnClear.disabled = selectedFiles.length === 0 && recognitionResults.length === 0;
        btnDownload.disabled = recognitionResults.length === 0;
    }

    // ===== Upload Zone Events =====
    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        addFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        addFiles(e.target.files);
        fileInput.value = '';
    });

    // File remove delegation
    fileList.addEventListener('click', (e) => {
        const removeBtn = e.target.closest('.remove-btn');
        if (removeBtn) {
            const index = parseInt(removeBtn.dataset.index);
            removeFile(index);
        }
    });

    // ===== Recognition =====
    btnRecognize.addEventListener('click', startRecognition);

    async function startRecognition() {
        if (selectedFiles.length === 0) return;

        const totalFiles = selectedFiles.length;

        // Show progress
        progressSection.classList.add('visible');
        resultsSection.classList.remove('visible');
        btnRecognize.disabled = true;
        btnDownload.disabled = true;
        recognitionResults = [];

        progressBar.style.width = '0%';
        progressCount.textContent = `0 / ${totalFiles}`;
        progressText.textContent = '正在上传文件并识别...';

        try {
            // 将所有文件一次性上传
            const formData = new FormData();
            selectedFiles.forEach(file => formData.append('files', file));

            // 添加选择的模型
            const selectedModel = modelSelect.value;
            if (selectedModel) {
                formData.append('model', selectedModel);
            }

            progressBar.style.width = '30%';
            progressText.textContent = `正在识别 ${totalFiles} 个发票...`;

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`服务器错误: ${response.status}`);
            }

            const data = await response.json();

            progressBar.style.width = '100%';
            progressCount.textContent = `${totalFiles} / ${totalFiles}`;
            progressText.textContent = '识别完成！';

            recognitionResults = data.results || [];
            renderResults();

            setTimeout(() => {
                progressSection.classList.remove('visible');
            }, 1200);

            const successCount = recognitionResults.filter(r => !r.error).length;
            showToast(`识别完成：${successCount} 个成功，${recognitionResults.length - successCount} 个失败`, 'success');

        } catch (err) {
            progressSection.classList.remove('visible');
            showToast(`识别失败: ${err.message}`, 'error');
            console.error('Recognition error:', err);
        }

        updateButtonStates();
    }

    // ===== Results Rendering =====
    function renderResults() {
        resultsBody.innerHTML = '';

        if (recognitionResults.length === 0) {
            resultsSection.classList.remove('visible');
            return;
        }

        resultsSection.classList.add('visible');
        resultCount.textContent = recognitionResults.length;

        const fields = ['发票日期', '发票类型', '发票号码', '数电发票号码',
                        '供应商名称', '金额', '税额', '有效抵扣税额', '价税合计'];
        const amountFields = ['金额', '税额', '有效抵扣税额', '价税合计'];

        recognitionResults.forEach((result, idx) => {
            const tr = document.createElement('tr');

            // Row index
            const tdIndex = document.createElement('td');
            tdIndex.className = 'row-index';
            tdIndex.textContent = idx + 1;
            tr.appendChild(tdIndex);

            if (result.error) {
                const tdError = document.createElement('td');
                tdError.colSpan = fields.length;
                tdError.className = 'error-cell';
                tdError.textContent = `${result['文件名'] || ''} — ${result.error}`;
                tr.appendChild(tdError);
            } else {
                fields.forEach(field => {
                    const td = document.createElement('td');
                    const value = result[field] || '';
                    td.textContent = value;

                    if (amountFields.includes(field) && value) {
                        td.className = 'amount';
                        // 格式化数字
                        const num = parseFloat(value);
                        if (!isNaN(num)) {
                            td.textContent = num.toLocaleString('zh-CN', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }
                    }

                    tr.appendChild(td);
                });
            }

            resultsBody.appendChild(tr);
        });
    }

    // ===== Download Excel =====
    btnDownload.addEventListener('click', downloadExcel);

    async function downloadExcel() {
        if (recognitionResults.length === 0) return;

        btnDownload.disabled = true;
        showToast('正在生成 Excel...', 'info', 2000);

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ results: recognitionResults })
            });

            if (!response.ok) {
                throw new Error(`下载失败: ${response.status}`);
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '发票识别结果.xlsx';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showToast('Excel 下载成功！', 'success');
        } catch (err) {
            showToast(`下载失败: ${err.message}`, 'error');
            console.error('Download error:', err);
        }

        btnDownload.disabled = false;
    }

    // ===== Clear =====
    btnClear.addEventListener('click', () => {
        selectedFiles = [];
        recognitionResults = [];
        renderFileList();
        resultsBody.innerHTML = '';
        resultsSection.classList.remove('visible');
        progressSection.classList.remove('visible');
        updateButtonStates();
        showToast('已清空所有数据', 'info', 2000);
    });

})();
