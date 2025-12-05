// Script2WAVE v2.2 - 통합 미리보기
const API_BASE = '/api';

const state = {
    selectedFiles: [],
    selectedJobs: new Set(),
    jobs: { data: [], total: 0, page: 1, pageSize: 20, search: '', status: '', sortBy: 'created_at', sortOrder: 'desc' },
    autoRefresh: null,
    currentJobId: null,
    utterances: []
};

// === 초기화 ===
document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initToolbar();
    initTable();
    initPreviewModal();
    initSettingsModal();
    loadStats();
    loadJobs();
    startAutoRefresh();
});

function startAutoRefresh() {
    if (state.autoRefresh) clearInterval(state.autoRefresh);
    
    async function refresh() {
        await loadStats();
        await loadJobs();
        
        // 처리 중인 작업이 있으면 2초, 없으면 10초 간격
        const hasProcessing = state.jobs.data.some(j => 
            ['pending', 'parsing', 'generating_tts', 'mixing'].includes(j.status)
        );
        const interval = hasProcessing ? 2000 : 10000;
        
        state.autoRefresh = setTimeout(refresh, interval);
    }
    
    refresh();
}

// === 통계 ===
async function loadStats() {
    try {
        const stats = await fetchAPI('/jobs/stats/summary');
        document.getElementById('statTotal').textContent = stats.total;
        document.getElementById('statProcessing').textContent = stats.processing;
        document.getElementById('statCompleted').textContent = stats.by_status.completed || 0;
        document.getElementById('statFailed').textContent = stats.by_status.failed || 0;
    } catch (e) {}
}

// === 업로드 ===
function initUpload() {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('fileInput');
    
    zone.onclick = (e) => {
        if (e.target === zone || e.target.closest('.upload-text')) {
            input.click();
        }
    };
    
    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add('dragover'); };
    zone.ondragleave = () => zone.classList.remove('dragover');
    zone.ondrop = (e) => { 
        e.preventDefault(); 
        zone.classList.remove('dragover');
        
        // dataTransfer.items 또는 dataTransfer.files 사용
        let files = [];
        if (e.dataTransfer.items) {
            console.log('Using dataTransfer.items, count:', e.dataTransfer.items.length);
            for (let i = 0; i < e.dataTransfer.items.length; i++) {
                if (e.dataTransfer.items[i].kind === 'file') {
                    const file = e.dataTransfer.items[i].getAsFile();
                    if (file) {
                        files.push(file);
                        console.log('  Item ' + i + ':', file.name);
                    }
                }
            }
        } else {
            console.log('Using dataTransfer.files, count:', e.dataTransfer.files.length);
            for (let i = 0; i < e.dataTransfer.files.length; i++) {
                files.push(e.dataTransfer.files[i]);
            }
        }
        
        console.log('Total dropped files:', files.length);
        if (files.length > 0) {
            addFiles(files);
        }
    };
    
    input.addEventListener('change', function(e) {
        console.log('File input changed');
        console.log('Files object:', e.target.files);
        console.log('Files length:', e.target.files.length);
        
        if (e.target.files && e.target.files.length > 0) {
            // FileList를 명시적으로 순회
            const files = [];
            for (let i = 0; i < e.target.files.length; i++) {
                files.push(e.target.files[i]);
                console.log('File ' + i + ':', e.target.files[i].name);
            }
            addFiles(files);
        }
        // 같은 파일 재선택 가능하도록 초기화
        this.value = '';
    });
    
    document.getElementById('clearQueueBtn').onclick = clearQueue;
    document.getElementById('startUploadBtn').onclick = startUpload;
}

function addFiles(files) {
    // FileList 또는 Array 모두 처리
    let fileArray;
    if (Array.isArray(files)) {
        fileArray = files;
    } else {
        fileArray = [];
        for (let i = 0; i < files.length; i++) {
            fileArray.push(files[i]);
        }
    }
    
    console.log('=== addFiles called ===');
    console.log('Input type:', files.constructor.name);
    console.log('Files to add:', fileArray.length);
    fileArray.forEach((f, i) => console.log('  [' + i + '] ' + f.name));
    
    state.selectedFiles.push(...fileArray);
    console.log('Total in queue:', state.selectedFiles.length);
    renderQueue();
}

function renderQueue() {
    const queue = document.getElementById('uploadQueue');
    const list = document.getElementById('queueList');
    const count = document.getElementById('queueCount');
    
    if (state.selectedFiles.length === 0) {
        queue.style.display = 'none';
        return;
    }
    
    // 총 용량 계산
    const totalSize = state.selectedFiles.reduce((sum, f) => sum + f.size, 0);
    
    queue.style.display = 'block';
    count.textContent = state.selectedFiles.length + '개 파일 (' + formatFileSize(totalSize) + ')';
    list.innerHTML = state.selectedFiles.map((f, i) => 
        '<div class="queue-item"><span>' + escapeHtml(f.name) + ' <span style="color:#999">(' + formatFileSize(f.size) + ')</span></span><button class="btn btn-small" onclick="removeFile(' + i + ')">제거</button></div>'
    ).join('');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function removeFile(i) {
    state.selectedFiles.splice(i, 1);
    renderQueue();
}

function clearQueue() {
    state.selectedFiles = [];
    document.getElementById('fileInput').value = '';
    renderQueue();
}

async function startUpload() {
    if (state.selectedFiles.length === 0) return;
    
    const total = state.selectedFiles.length;
    showLoading(total + '개 파일 업로드 중...');
    let ok = 0, fail = 0;
    
    // 파일 배열 복사 (순회 중 변경 방지)
    const filesToUpload = [...state.selectedFiles];
    
    for (let i = 0; i < filesToUpload.length; i++) {
        const file = filesToUpload[i];
        try {
            const fd = new FormData();
            fd.append('file', file);
            const res = await fetch(API_BASE + '/upload/', { method: 'POST', body: fd });
            if (res.ok) {
                ok++;
            } else {
                fail++;
                console.error('Upload failed:', file.name, res.status);
            }
        } catch (e) {
            fail++;
            console.error('Upload error:', file.name, e);
        }
        // 진행률 업데이트
        document.getElementById('loadingText').textContent = 
            '업로드 중... (' + (i + 1) + '/' + total + ')';
    }
    
    hideLoading();
    clearQueue();
    if (ok > 0) showToast(ok + '개 업로드 완료', 'success');
    if (fail > 0) showToast(fail + '개 실패', 'error');
    loadStats();
    loadJobs();
}

// === 툴바 ===
function initToolbar() {
    document.getElementById('refreshBtn').onclick = () => { loadStats(); loadJobs(); };
    document.getElementById('searchBtn').onclick = doSearch;
    document.getElementById('searchInput').onkeypress = (e) => { if (e.key === 'Enter') doSearch(); };
    document.getElementById('statusFilter').onchange = (e) => { state.jobs.status = e.target.value; state.jobs.page = 1; loadJobs(); };
    document.getElementById('pageSizeSelect').onchange = (e) => { state.jobs.pageSize = parseInt(e.target.value); state.jobs.page = 1; loadJobs(); };
    
    document.getElementById('batchDownloadBtn').onclick = batchDownload;
    document.getElementById('batchRetryBtn').onclick = batchRetry;
    document.getElementById('batchDeleteBtn').onclick = batchDelete;
}

function doSearch() {
    state.jobs.search = document.getElementById('searchInput').value;
    state.jobs.page = 1;
    loadJobs();
}

// === 테이블 ===
function initTable() {
    document.getElementById('selectAllJobs').onchange = (e) => {
        document.querySelectorAll('#jobsTableBody input[type="checkbox"]').forEach(cb => {
            cb.checked = e.target.checked;
            if (e.target.checked) state.selectedJobs.add(cb.dataset.id);
            else state.selectedJobs.delete(cb.dataset.id);
        });
        updateBatchBar();
    };
    
    document.querySelectorAll('#jobsTable th.sortable').forEach(th => {
        th.onclick = () => {
            const col = th.dataset.sort;
            if (state.jobs.sortBy === col) state.jobs.sortOrder = state.jobs.sortOrder === 'asc' ? 'desc' : 'asc';
            else { state.jobs.sortBy = col; state.jobs.sortOrder = 'desc'; }
            loadJobs();
        };
    });
}

async function loadJobs() {
    try {
        const p = new URLSearchParams({
            page: state.jobs.page,
            page_size: state.jobs.pageSize,
            sort_by: state.jobs.sortBy,
            sort_order: state.jobs.sortOrder
        });
        if (state.jobs.search) p.append('search', state.jobs.search);
        if (state.jobs.status) p.append('status', state.jobs.status);
        
        const data = await fetchAPI('/jobs/?' + p);
        state.jobs.data = data.jobs;
        state.jobs.total = data.total;
        
        renderTable(data.jobs);
        renderPagination(data.total, data.page, data.page_size);
        
        state.selectedJobs.clear();
        document.getElementById('selectAllJobs').checked = false;
        updateBatchBar();
    } catch (e) {
        showToast('로드 실패: ' + e.message, 'error');
    }
}

function renderTable(jobs) {
    const tbody = document.getElementById('jobsTableBody');
    
    if (!jobs.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">작업이 없습니다</td></tr>';
        return;
    }
    
    tbody.innerHTML = jobs.map(j => {
        const sel = state.selectedJobs.has(j.id);
        return '<tr class="' + (sel ? 'selected' : '') + '">' +
            '<td class="th-checkbox"><input type="checkbox" data-id="' + j.id + '" ' + (sel ? 'checked' : '') + ' onchange="toggleSelect(\'' + j.id + '\', this.checked)"></td>' +
            '<td title="' + escapeHtml(j.original_filename) + '">' + escapeHtml(truncate(j.original_filename, 40)) + '</td>' +
            '<td>' + renderStatus(j.status) + '</td>' +
            '<td>' + renderProgress(j.progress, j.status) + '</td>' +
            '<td>' + (j.duration_seconds ? formatDuration(j.duration_seconds) : '-') + '</td>' +
            '<td>' + formatDate(j.created_at) + '</td>' +
            '<td><div class="table-actions">' + renderActions(j) + '</div></td>' +
            '</tr>';
    }).join('');
}

function renderActions(j) {
    let a = [];
    if (j.status === 'completed') {
        a.push('<button class="action-btn primary" onclick="openPreview(\'' + j.id + '\',\'' + escapeHtml(j.original_filename) + '\')">미리보기</button>');
        a.push('<button class="action-btn" onclick="downloadAll(\'' + j.id + '\')">다운로드</button>');
    }
    if (j.status === 'failed') {
        a.push('<button class="action-btn" onclick="retryJob(\'' + j.id + '\')">재시도</button>');
    }
    a.push('<button class="action-btn delete" onclick="deleteJob(\'' + j.id + '\')">삭제</button>');
    return a.join('');
}

function toggleSelect(id, checked) {
    if (checked) state.selectedJobs.add(id);
    else state.selectedJobs.delete(id);
    updateBatchBar();
    const row = document.querySelector('input[data-id="' + id + '"]').closest('tr');
    row.classList.toggle('selected', checked);
}

function updateBatchBar() {
    const bar = document.getElementById('batchBar');
    const n = state.selectedJobs.size;
    bar.style.display = n > 0 ? 'flex' : 'none';
    document.getElementById('selectedCount').textContent = n;
}

function renderPagination(total, page, size) {
    document.getElementById('paginationInfo').textContent = total + '개';
    
    const pages = Math.ceil(total / size);
    const pag = document.getElementById('pagination');
    let btns = [];
    
    btns.push('<button ' + (page === 1 ? 'disabled' : '') + ' onclick="goPage(' + (page - 1) + ')">이전</button>');
    
    let start = Math.max(1, page - 2);
    let end = Math.min(pages, start + 4);
    start = Math.max(1, end - 4);
    
    for (let i = start; i <= end; i++) {
        btns.push('<button class="' + (i === page ? 'active' : '') + '" onclick="goPage(' + i + ')">' + i + '</button>');
    }
    
    btns.push('<button ' + (page === pages || pages === 0 ? 'disabled' : '') + ' onclick="goPage(' + (page + 1) + ')">다음</button>');
    
    pag.innerHTML = btns.join('');
}

function goPage(p) {
    state.jobs.page = p;
    loadJobs();
}

// === 일괄 작업 ===
async function batchDelete() {
    if (state.selectedJobs.size === 0) return;
    if (!confirm(state.selectedJobs.size + '개를 삭제하시겠습니까?')) return;
    
    showLoading('삭제 중...');
    try {
        await fetchAPI('/jobs/batch/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Array.from(state.selectedJobs))
        });
        showToast('삭제 완료', 'success');
        loadStats();
        loadJobs();
    } catch (e) {
        showToast('삭제 실패', 'error');
    }
    hideLoading();
}

async function batchRetry() {
    if (state.selectedJobs.size === 0) return;
    showLoading('재시도 중...');
    try {
        await fetchAPI('/jobs/batch/retry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Array.from(state.selectedJobs))
        });
        showToast('재시도 시작', 'success');
        loadJobs();
    } catch (e) {
        showToast('재시도 실패', 'error');
    }
    hideLoading();
}

async function batchDownload() {
    if (state.selectedJobs.size === 0) return;
    for (const id of state.selectedJobs) {
        window.open(API_BASE + '/files/' + id + '/download-all', '_blank');
        await sleep(300);
    }
    showToast('다운로드 시작', 'info');
}

// === 개별 작업 ===
async function deleteJob(id) {
    if (!confirm('삭제하시겠습니까?')) return;
    try {
        await fetchAPI('/jobs/' + id, { method: 'DELETE' });
        showToast('삭제됨', 'success');
        loadStats();
        loadJobs();
    } catch (e) {
        showToast('삭제 실패: ' + e.message, 'error');
    }
}

async function retryJob(id) {
    try {
        await fetchAPI('/jobs/' + id + '/retry', { method: 'POST' });
        showToast('재시도 시작', 'success');
        loadJobs();
    } catch (e) {
        showToast('재시도 실패', 'error');
    }
}

function downloadAll(id) {
    window.open(API_BASE + '/files/' + id + '/download-all', '_blank');
}

// === 통합 미리보기 모달 ===
function initPreviewModal() {
    const modal = document.getElementById('previewModal');
    const player = document.getElementById('audioPlayer');
    
    document.getElementById('closePreviewModal').onclick = closePreview;
    modal.onclick = (e) => { if (e.target === modal) closePreview(); };
    
    // 오디오 이벤트
    player.ontimeupdate = () => {
        document.getElementById('currentTime').textContent = formatTime(player.currentTime);
        updateActiveUtterance(player.currentTime);
    };
    
    player.onloadedmetadata = () => {
        document.getElementById('totalTime').textContent = formatTime(player.duration);
    };
    
    // 다운로드 버튼
    document.getElementById('downloadWavBtn').onclick = () => {
        if (state.currentJobId) window.open(API_BASE + '/files/' + state.currentJobId + '/download', '_blank');
    };
    document.getElementById('downloadJsonBtn').onclick = () => {
        if (state.currentJobId) window.open(API_BASE + '/files/' + state.currentJobId + '/download-json', '_blank');
    };
    document.getElementById('downloadAllBtn').onclick = () => {
        if (state.currentJobId) window.open(API_BASE + '/files/' + state.currentJobId + '/download-all', '_blank');
    };
}

async function openPreview(jobId, filename) {
    state.currentJobId = jobId;
    
    const modal = document.getElementById('previewModal');
    const player = document.getElementById('audioPlayer');
    
    document.getElementById('previewTitle').textContent = filename;
    player.src = API_BASE + '/files/' + jobId + '/stream';
    
    // JSON 로드
    try {
        const data = await fetchAPI('/files/' + jobId + '/json-preview');
        state.utterances = data.utterances || [];
        
        // 파일 크기 표시
        let sizeInfo = state.utterances.length + '개 발화';
        if (data.file_sizes) {
            sizeInfo += ' | WAV ' + formatFileSize(data.file_sizes.wav);
            sizeInfo += ' | JSON ' + formatFileSize(data.file_sizes.json);
        }
        document.getElementById('utteranceCount').textContent = sizeInfo;
        
        renderUtterances();
    } catch (e) {
        state.utterances = [];
        document.getElementById('utteranceCount').textContent = '0개';
        document.getElementById('utterancesList').innerHTML = '<div class="empty-state">발화 정보 없음</div>';
    }
    
    modal.classList.add('active');
}

function closePreview() {
    const modal = document.getElementById('previewModal');
    const player = document.getElementById('audioPlayer');
    player.pause();
    modal.classList.remove('active');
    state.currentJobId = null;
    state.utterances = [];
}

function renderUtterances() {
    const list = document.getElementById('utterancesList');
    
    if (!state.utterances.length) {
        list.innerHTML = '<div class="empty-state">발화 정보 없음</div>';
        return;
    }
    
    list.innerHTML = state.utterances.map((u, idx) => {
        const role = u.role === 'agent' ? '상담사' : '고객';
        return '<div class="utterance-item ' + u.role + '" data-idx="' + idx + '" onclick="seekToUtterance(' + idx + ')">' +
            '<div class="utterance-header">' +
            '<span class="utterance-role">#' + u.turn_idx + ' ' + role + '</span>' +
            '<span class="utterance-time">' + formatTime(u.started_at) + ' - ' + formatTime(u.ended_at) + '</span>' +
            '</div>' +
            '<div class="utterance-text">' + escapeHtml(u.utterance) + '</div>' +
            '</div>';
    }).join('');
}

function seekToUtterance(idx) {
    const u = state.utterances[idx];
    if (!u) return;
    
    const player = document.getElementById('audioPlayer');
    player.currentTime = u.started_at;
    player.play();
}

function updateActiveUtterance(currentTime) {
    // 현재 재생 위치에 해당하는 발화 찾기
    let activeIdx = -1;
    for (let i = 0; i < state.utterances.length; i++) {
        const u = state.utterances[i];
        if (currentTime >= u.started_at && currentTime <= u.ended_at) {
            activeIdx = i;
            break;
        }
    }
    
    // 활성화 표시
    document.querySelectorAll('.utterance-item').forEach((el, idx) => {
        el.classList.toggle('active', idx === activeIdx);
    });
    
    // 활성화된 항목으로 스크롤
    if (activeIdx >= 0) {
        const activeEl = document.querySelector('.utterance-item[data-idx="' + activeIdx + '"]');
        if (activeEl) {
            activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
}

// === 설정 모달 ===
function initSettingsModal() {
    const modal = document.getElementById('settingsModal');
    
    document.getElementById('settingsBtn').onclick = openSettings;
    document.getElementById('closeSettingsModal').onclick = () => modal.classList.remove('active');
    modal.onclick = (e) => { if (e.target === modal) modal.classList.remove('active'); };
    
    document.getElementById('saveApiKeyBtn').onclick = saveApiKey;
    document.getElementById('apiKeyInput').onkeypress = (e) => { if (e.key === 'Enter') saveApiKey(); };
}

async function openSettings() {
    const modal = document.getElementById('settingsModal');
    modal.classList.add('active');
    
    // 현재 상태 로드
    try {
        const config = await fetchAPI('/config');
        const status = document.getElementById('apiKeyStatus');
        
        if (config.has_api_key) {
            const source = config.api_key_source === 'runtime' ? '(세션)' : '(환경변수)';
            status.textContent = 'API 키 설정됨 ' + source;
            status.className = 'settings-status success';
        } else if (config.tts_mock_mode) {
            status.textContent = 'Mock 모드 (테스트용)';
            status.className = 'settings-status';
        } else {
            status.textContent = 'API 키 없음 - 키를 입력해주세요';
            status.className = 'settings-status error';
        }
    } catch (e) {
        document.getElementById('apiKeyStatus').textContent = '상태 확인 실패';
        document.getElementById('apiKeyStatus').className = 'settings-status error';
    }
}

async function saveApiKey() {
    const input = document.getElementById('apiKeyInput');
    const key = input.value.trim();
    
    if (!key) {
        showToast('API 키를 입력해주세요', 'error');
        return;
    }
    
    try {
        const res = await fetch(API_BASE + '/settings/api-key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast('API 키가 저장되었습니다: ' + data.masked_key, 'success');
            input.value = '';
            
            const status = document.getElementById('apiKeyStatus');
            status.textContent = 'API 키 설정됨 (세션) - ' + data.masked_key;
            status.className = 'settings-status success';
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('저장 실패: ' + e.message, 'error');
    }
}

// === 유틸 ===
async function fetchAPI(endpoint, options) {
    const res = await fetch(API_BASE + endpoint, options || {});
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Error' }));
        throw new Error(err.detail || 'API Error');
    }
    return res.json();
}

function renderStatus(s) {
    const labels = { pending: '대기중', parsing: '파싱중', generating_tts: 'TTS생성', mixing: '믹싱', completed: '완료', failed: '실패', cancelled: '취소' };
    let cls = s;
    if (['parsing', 'generating_tts', 'mixing'].includes(s)) cls = 'processing';
    return '<span class="status-badge ' + cls + '">' + (labels[s] || s) + '</span>';
}

function renderProgress(p, s) {
    const pct = s === 'completed' ? 100 : p;
    const cls = s === 'completed' ? 'progress-fill complete' : 'progress-fill';
    return '<div class="progress-container"><div class="progress-bar"><div class="' + cls + '" style="width:' + pct + '%"></div></div><span class="progress-text">' + pct + '%</span></div>';
}

function formatDate(d) {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function formatDuration(s) {
    if (!s) return '-';
    if (s < 60) return Math.round(s) + '초';
    return Math.floor(s / 60) + '분 ' + Math.round(s % 60) + '초';
}

function formatTime(s) {
    if (s == null || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return m + ':' + String(sec).padStart(2, '0');
}

function truncate(s, n) {
    return s && s.length > n ? s.slice(0, n - 3) + '...' : s || '';
}

function escapeHtml(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

function showToast(msg, type) {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = 'toast ' + (type || 'info');
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

function showLoading(text) {
    document.getElementById('loadingText').textContent = text || '처리 중...';
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}
