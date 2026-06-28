/* ==========================================================================
   OUTREACH NODE - FRONTEND JAVASCRIPT INTERACTIONS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    initDragAndDrop();
    initCampaignForm();
    initResultsFilter();
    initPromptDocUpload();
    initStatCountUp();
    initKeyboardNav();
    initInteractiveStats();
    initThemeToggle();
});

/* ==========================================================================
   DARK MODE SYSTEM (#20)
   Initializes and handles dark mode toggling with localStorage persistence
   ========================================================================== */

function initThemeToggle() {
    const btn = document.getElementById('theme-toggle-btn');
    if (!btn) return;

    const icon = btn.querySelector('i');

    function setTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            icon.className = 'fa-solid fa-sun';
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
            icon.className = 'fa-solid fa-moon';
            localStorage.setItem('theme', 'light');
        }
    }

    const savedTheme = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (savedTheme === 'dark' || (!savedTheme && systemDark)) {
        setTheme('dark');
    } else {
        setTheme('light');
    }

    btn.addEventListener('click', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        setTheme(isDark ? 'light' : 'dark');
    });
}

/* ==========================================================================
   KEYBOARD NAVIGATION ON RESULTS TABLE ROWS (#18)
   Allows users to navigate results table rows with ArrowUp/ArrowDown and open with Enter
   ========================================================================== */

function initKeyboardNav() {
    const table = document.getElementById('results-table');
    if (!table) return;

    const getRows = () => Array.from(table.querySelectorAll('tbody tr.prospect-row'));
    const rows = getRows();
    if (!rows.length) return;

    rows.forEach(row => {
        row.setAttribute('tabindex', '0');
    });

    // Re-evaluate tabindex when filter changes
    document.addEventListener('filterChanged', () => {
        getRows().forEach(row => {
            if (row.style.display === 'none') {
                row.removeAttribute('tabindex');
            } else {
                row.setAttribute('tabindex', '0');
            }
        });
    });

    table.addEventListener('keydown', (e) => {
        const activeEl = document.activeElement;
        if (!activeEl || !activeEl.classList.contains('prospect-row')) return;

        const visibleRows = getRows().filter(row => row.style.display !== 'none');
        const currentIndex = visibleRows.indexOf(activeEl);
        if (currentIndex === -1) return;

        if (e.key === 'ArrowDown' || e.key === 'j') {
            e.preventDefault();
            const nextRow = visibleRows[currentIndex + 1];
            if (nextRow) nextRow.focus();
        } else if (e.key === 'ArrowUp' || e.key === 'k') {
            e.preventDefault();
            const prevRow = visibleRows[currentIndex - 1];
            if (prevRow) prevRow.focus();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            const btn = activeEl.querySelector('.btn');
            if (btn) btn.click();
        }
    });
}

/* ==========================================================================
   INTERACTIVE STAT CARDS (#19)
   Filters the results table based on the clicked stat card (approved, rejected, total)
   ========================================================================== */

let currentFilterType = 'all';
let currentSearchQuery = '';

function applyCombinedFilters() {
    const rows = document.querySelectorAll('.prospect-row');
    rows.forEach(row => {
        const status = row.getAttribute('data-status');
        const text = row.innerText.toLowerCase();
        
        let matchesStatus = false;
        if (currentFilterType === 'all') {
            matchesStatus = true;
        } else if (currentFilterType === 'approved') {
            matchesStatus = (status === 'approved' || status === 'sent');
        } else if (currentFilterType === 'rejected') {
            matchesStatus = (status === 'rejected' || status === 'failed');
        }
        
        const matchesSearch = text.includes(currentSearchQuery);
        
        if (matchesStatus && matchesSearch) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    
    // Trigger filterChanged event so keyboard nav updates row tabindex
    document.dispatchEvent(new CustomEvent('filterChanged'));
}

function initInteractiveStats() {
    const cardTotal = document.getElementById('card-total');
    const cardApproved = document.getElementById('card-approved');
    const cardRejected = document.getElementById('card-rejected');
    if (!cardTotal || !cardApproved || !cardRejected) return;

    const cards = [cardTotal, cardApproved, cardRejected];

    function filterTable(filterType) {
        cards.forEach(c => c.classList.remove('active'));
        if (filterType === 'all') cardTotal.classList.add('active');
        if (filterType === 'approved') cardApproved.classList.add('active');
        if (filterType === 'rejected') cardRejected.classList.add('active');

        currentFilterType = filterType;
        applyCombinedFilters();
    }

    cardTotal.addEventListener('click', () => filterTable('all'));
    cardApproved.addEventListener('click', () => filterTable('approved'));
    cardRejected.addEventListener('click', () => filterTable('rejected'));

    // Set total as active by default
    cardTotal.classList.add('active');
}

/* ==========================================================================
   STAT COUNT-UP ANIMATION (#02)
   Animates all .stat-value elements from 0 to their target value
   ========================================================================== */

function initStatCountUp() {
    const statValues = document.querySelectorAll('.stat-value');
    if (!statValues.length) return;

    const easeOutQuart = (t) => 1 - Math.pow(1 - t, 4);

    statValues.forEach(el => {
        const rawText = el.innerText.trim();
        // Parse: "42", "9.2/10", "$0.0023", "8.5/10", "—"
        const match = rawText.match(/^([^\d-]*)([\d\.,]+)(.*)$/);
        if (!match) return;

        const prefix = match[1] || '';
        const numStr = match[2];
        const suffix = match[3] || '';

        const num = parseFloat(numStr.replace(/,/g, ''));
        if (isNaN(num)) return;

        const target = num;
        const isDecimal = numStr.includes('.');
        const decimals = isDecimal ? numStr.split('.')[1].length : 0;

        el.innerText = prefix + '0' + suffix;

        const duration = 800;
        const startTime = performance.now();

        function tick(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easedProgress = easeOutQuart(progress);
            const current = easedProgress * target;
            const formatted = decimals > 0
                ? current.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
                : Math.round(current).toLocaleString('en-US');
            el.innerText = prefix + formatted + suffix;

            if (progress < 1) requestAnimationFrame(tick);
        }

        requestAnimationFrame(tick);
    });
}

// Global state for preview modal
let currentProspectData = null;
let currentCampaignId = null;

/* ==========================================================================
   TOAST NOTIFICATION SYSTEM
   ========================================================================== */

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let iconClass = 'fa-circle-info';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'error') iconClass = 'fa-triangle-exclamation';

    toast.innerHTML = `
        <i class="fa-solid ${iconClass} toast-icon"></i>
        <span>${message}</span>
        <button class="toast-close" onclick="dismissToast(this.parentElement)">&times;</button>
        <div class="toast-progress"></div>
    `;

    container.appendChild(toast);

    // Auto remove after 5 seconds with slide-out animation
    setTimeout(() => dismissToast(toast), 5000);
}

function dismissToast(toast) {
    if (!toast || !toast.parentElement) return;
    toast.style.animation = 'slideOutRight 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
}

/* ==========================================================================
   DASHBOARD: DRAG AND DROP CSV UPLOAD
   ========================================================================== */

function initDragAndDrop() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('csv-file-input');
    const submitBtn = document.getElementById('submit-btn');
    const filepathInput = document.getElementById('uploaded-filepath');
    const previewContainer = document.getElementById('csv-preview-container');
    const previewTbody = document.getElementById('preview-tbody');
    const prospectCount = document.getElementById('prospect-count');

    if (!uploadZone) return;

    // Click to browse
    uploadZone.addEventListener('click', () => fileInput.click());

    // File selection
    fileInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0]));

    // Drag events
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
        }, false);
    });

    uploadZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        handleFileSelect(file);
    });

    function handleFileSelect(file) {
        const allowedExts = ['.csv', '.xlsx', '.xls'];
        const fileExt = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
        if (!file || !allowedExts.includes(fileExt)) {
            showToast('Please upload a valid CSV or Excel file.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        showToast('Uploading file and parsing fields...', 'info');

        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            // Save filepath
            filepathInput.value = data.filepath;
            prospectCount.innerText = data.count;

            // Render Preview Table dynamically based on columns
            console.log("CSV parse data received:", data);
            const table = document.getElementById('preview-table');
            if (table) {
                const thead = table.querySelector('thead');
                const tbody = document.getElementById('preview-tbody');
                
                // Get headers (either from data.headers or fallback to keys of the first row)
                let headers = data.headers;
                if (!headers && data.preview && data.preview.length > 0) {
                    headers = Object.keys(data.preview[0]);
                }
                
                console.log("Rendering preview with headers:", headers);

                if (thead && headers) {
                    thead.innerHTML = '';
                    const trHead = document.createElement('tr');
                    headers.forEach(header => {
                        const th = document.createElement('th');
                        th.innerText = header;
                        trHead.appendChild(th);
                    });
                    thead.appendChild(trHead);
                }

                if (tbody && data.preview && headers) {
                    tbody.innerHTML = '';
                    data.preview.forEach((row, idx) => {
                        console.log(`Rendering row ${idx}:`, row);
                        const tr = document.createElement('tr');
                        headers.forEach(header => {
                            const td = document.createElement('td');
                            const val = row[header];
                            td.innerText = (val !== undefined && val !== null && val !== '') ? val : '—';
                            tr.appendChild(td);
                        });
                        tbody.appendChild(tr);
                    });
                }
            } else {
                console.error("Preview table element not found!");
            }

            if (previewContainer) {
                previewContainer.classList.remove('hidden');
            } else {
                console.error("previewContainer element not found!");
            }
            submitBtn.disabled = false;
            submitBtn.classList.remove('disabled-btn');
            showToast('File loaded and preview rendered successfully!', 'success');
        })
        .catch(err => {
            console.error(err);
            showToast('Failed to parse file.', 'error');
        });
    }
}

/* ==========================================================================
   DASHBOARD: LAUNCH CAMPAIGN FORM
   ========================================================================== */

function initCampaignForm() {
    const form = document.getElementById('campaign-form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const payload = {
            filepath: formData.get('filepath'),
            sender_name: formData.get('sender_name'),
            sender_role: formData.get('sender_role'),
            sender_company: formData.get('sender_company'),
            tone: formData.get('tone'),
            goal: formData.get('goal'),
            custom_prompt: formData.get('custom_prompt'),
            auto_generate_audio: form.querySelector('#auto_generate_audio').checked,
            prompt_doc_content: document.getElementById('prompt-doc-content')?.value || '',
            prompt_doc_filename: document.getElementById('prompt-doc-filename-hidden')?.value || '',
            tags: document.getElementById('tags')?.value || '',
            ab_test: document.getElementById('ab_test')?.checked || false
        };

        showToast('Initializing multi-agent pipeline...', 'info');

        fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }
            showToast('Campaign launched successfully!', 'success');
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 1000);
        })
        .catch(err => {
            console.error(err);
            showToast('Failed to launch campaign.', 'error');
        });
    });
}

/* ==========================================================================
   DASHBOARD: PROMPT DOCUMENT UPLOAD
   ========================================================================== */

function initPromptDocUpload() {
    const zone = document.getElementById('prompt-doc-zone');
    const input = document.getElementById('prompt-doc-input');
    const emptyState = document.getElementById('prompt-doc-empty');
    const loadedState = document.getElementById('prompt-doc-loaded');
    const loadingState = document.getElementById('prompt-doc-loading');
    const filenameSpan = document.getElementById('prompt-doc-filename');
    const filesizeSpan = document.getElementById('prompt-doc-filesize');
    const removeBtn = document.getElementById('prompt-doc-remove');
    const contentHidden = document.getElementById('prompt-doc-content');
    const filenameHidden = document.getElementById('prompt-doc-filename-hidden');

    if (!zone) return;

    zone.addEventListener('click', (e) => {
        if (e.target.closest('#prompt-doc-remove')) return;
        if (loadedState.classList.contains('hidden')) {
            input.click();
        }
    });

    input.addEventListener('change', () => {
        const file = input.files[0];
        if (!file) return;
        uploadPromptDoc(file);
    });

    removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        input.value = '';
        contentHidden.value = '';
        filenameHidden.value = '';
        loadedState.classList.add('hidden');
        emptyState.classList.remove('hidden');
        loadingState.classList.add('hidden');
    });

    // Drag-and-drop for doc zone
    ['dragenter', 'dragover'].forEach(evt => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            zone.style.borderColor = 'var(--accent-purple)';
            zone.style.background = 'rgba(79, 70, 229, 0.02)';
        });
    });
    ['dragleave', 'drop'].forEach(evt => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            zone.style.borderColor = '';
            zone.style.background = '';
        });
    });
    zone.addEventListener('drop', (e) => {
        const file = e.dataTransfer.files[0];
        if (!file) return;
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!['.pdf', '.docx', '.txt'].includes(ext)) {
            showToast('Please attach a PDF, DOCX, or TXT file.', 'error');
            return;
        }
        uploadPromptDoc(file);
    });

    function uploadPromptDoc(file) {
        emptyState.classList.add('hidden');
        loadedState.classList.add('hidden');
        loadingState.classList.remove('hidden');

        filenameSpan.innerText = file.name;
        filesizeSpan.innerText = (file.size / 1024).toFixed(1) + ' KB';

        const formData = new FormData();
        formData.append('file', file);

        fetch('/api/upload-prompt-doc', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            loadingState.classList.add('hidden');
            if (data.error) {
                showToast(data.error, 'error');
                emptyState.classList.remove('hidden');
                return;
            }
            contentHidden.value = data.content;
            filenameHidden.value = data.filename;
            loadedState.classList.remove('hidden');
            showToast('Document content extracted and ready for AI agents.', 'success');
        })
        .catch(err => {
            console.error(err);
            loadingState.classList.add('hidden');
            emptyState.classList.remove('hidden');
            showToast('Failed to process document.', 'error');
        });
    }
}

/* ==========================================================================
   PIPELINE: REAL-TIME ORCHESTRATION POLLING
   ========================================================================== */

let activeTimelineTimer = null;
let activeStageStartTime = 0;

function initPipelinePolling(campaignId) {
    const terminalBody = document.getElementById('terminal-body');
    const runningList = document.getElementById('prospects-running-list');
    const globalStatusText = document.getElementById('campaign-global-status');
    const completionActions = document.getElementById('pipeline-completion-actions');
    
    // Timeline DOM elements
    const timelineCard = document.getElementById('timeline-visualizer-card');
    const timelineProspectName = document.getElementById('timeline-prospect-name');

    if (!terminalBody) return;

    let processedProspectIds = new Set();
    let currentLogs = [];
    let orchestratorLogged = false;

    const pollInterval = setInterval(() => {
        fetch(`/api/status/${campaignId}`)
        .then(res => res.json())
        .then(state => {
            if (state.error) {
                clearInterval(pollInterval);
                showToast(state.error, 'error');
                return;
            }

            // Log orchestrator agent activity
            if (state.current_stage === 'analyzing_prompt' && !orchestratorLogged) {
                orchestratorLogged = true;
                appendLogLine(`[Orchestrator Agent] Analyzing outreach prompt and building research plan...`, 'agent-log');
            }
            if (state.research_plan && state.research_plan.email_angle && !currentLogs.includes('orchestrator_done')) {
                currentLogs.push('orchestrator_done');
                appendLogLine(`[Orchestrator Agent] Research plan ready. LinkedIn priority: ${state.research_plan.linkedin_priority}, Web priority: ${state.research_plan.web_priority}`, 'success-log');
            }

            // Update running list of prospects
            runningList.innerHTML = '';
            let activeStage = null;
            let activeProspect = null;

            state.prospects.forEach(p => {
                const row = document.createElement('div');
                row.className = `prospect-run-card ${p.status === 'processing' ? 'processing' : ''}`;
                
                let stageText = p.stage.replace(/_/g, ' ');
                stageText = stageText.charAt(0).toUpperCase() + stageText.slice(1);

                let badgeClass = p.status;
                if (p.status === 'processing') {
                    badgeClass = 'pending';
                    activeStage = p.stage; // Track what agent is currently working
                    activeProspect = p;
                }

                let abBadge = '';
                if (p.ab_variant) {
                    abBadge = `<span class="status-badge" style="background: var(--accent-light); color: var(--accent); font-size: 10px; padding: 2px 6px;">Variant ${p.ab_variant}</span>`;
                }

                row.innerHTML = `
                    <div class="prospect-run-info">
                        <h4>${p.name}</h4>
                        <span>${p.company} &bull; ${p.title}</span>
                    </div>
                    <div class="prospect-run-status">
                        ${p.status === 'processing' ? '<span class="pulse-circle"></span>' : ''}
                        <span>${stageText}</span>
                        ${abBadge}
                        <span class="status-badge ${badgeClass}">${p.status.toUpperCase()}</span>
                    </div>
                `;
                runningList.appendChild(row);

                // Log completions to terminal
                if (p.status !== 'pending' && p.status !== 'processing' && !processedProspectIds.has(p.id)) {
                    processedProspectIds.add(p.id);
                    appendLogLine(`[ORCHESTRATOR] Completed processing for prospect: ${p.name}. Quality Score: ${p.proofread_score}/10. Status: ${p.status.toUpperCase()}`, 'success-log');
                }
            });

            // Update Stepper Cards
            updateStepperCards(activeStage);
            
            // Update Duration Timeline Visualizer
            if (activeProspect) {
                timelineCard.classList.remove('hidden');
                timelineProspectName.innerText = `${activeProspect.name} (${activeProspect.company})`;
                
                const timeline = activeProspect.agent_timeline || {orchestrator: 0, prospecting: 0, linkedin: 0, context: 0, copywriting: 0, proofreading: 0};
                
                // Clear any running frontend ticker interval if we moved to a new stage
                const currentSubstage = activeStage.startsWith('proofreading') ? 'proofreading' : activeStage;
                
                // Render locked durations
                updateTimelineBar('orchestrator', timeline.orchestrator, currentSubstage);
                updateTimelineBar('prospecting', timeline.prospecting, currentSubstage);
                updateTimelineBar('linkedin', timeline.linkedin, currentSubstage);
                updateTimelineBar('context', timeline.context, currentSubstage);
                updateTimelineBar('copywriting', timeline.copywriting, currentSubstage);
                updateTimelineBar('proofreading', timeline.proofreading, currentSubstage);
                
                // Start a smooth local count-up timer for the active stage
                setupLiveTimelineTicker(currentSubstage, timeline);
            } else {
                timelineCard.classList.add('hidden');
                if (activeTimelineTimer) {
                    clearInterval(activeTimelineTimer);
                    activeTimelineTimer = null;
                }
            }

            // Log details based on active stage
            if (activeStage && !currentLogs.includes(`${activeStage}_${state.status}`)) {
                currentLogs.push(`${activeStage}_${state.status}`);
                if (activeStage === 'prospecting') {
                    appendLogLine(`[Prospecting Agent] Scraping web for professional profile details...`, 'agent-log');
                } else if (activeStage === 'linkedin') {
                    appendLogLine(`[LinkedIn Agent] Performing prompt-guided LinkedIn intelligence gathering...`, 'agent-log');
                } else if (activeStage === 'context') {
                    appendLogLine(`[Web/Context Agent] Executing prompt-guided deep search for company signals...`, 'agent-log');
                } else if (activeStage === 'copywriting') {
                    appendLogLine(`[Copywriter Agent] Generating personalized cold email using research plan...`, 'agent-log');
                } else if (activeStage.startsWith('proofreading')) {
                    appendLogLine(`[Proofreader Agent] Auditing email for tone match & prompt relevance (score > 7 required)...`, 'agent-log');
                } else if (activeStage === 'generating_audio') {
                    appendLogLine(`[TTS Voicemail Tool] Rendering Google Text-to-Speech audio voicemails...`, 'system-log');
                }
            }

            // Handle Completion
            if (state.status === 'completed') {
                clearInterval(pollInterval);
                if (activeTimelineTimer) {
                    clearInterval(activeTimelineTimer);
                    activeTimelineTimer = null;
                }
                globalStatusText.innerText = 'Completed';
                const spinnerEl = document.querySelector('.pipeline-loader .spinner');
                if (spinnerEl) spinnerEl.style.display = 'none';
                completionActions.classList.remove('hidden');
                appendLogLine(`[SYSTEM] Campaign completed! Generated Excel spreadsheet. Ready for review.`, 'success-log');
                showToast('Campaign successfully completed!', 'success');
            } else if (state.status === 'failed') {
                clearInterval(pollInterval);
                if (activeTimelineTimer) {
                    clearInterval(activeTimelineTimer);
                    activeTimelineTimer = null;
                }
                globalStatusText.innerText = 'Failed';
                const spinnerFail = document.querySelector('.pipeline-loader .spinner');
                if (spinnerFail) spinnerFail.style.display = 'none';
                appendLogLine(`[SYSTEM ERROR] Campaign execution encountered a critical error and terminated.`, 'error-log');
                showToast('Campaign execution failed.', 'error');
                
                if (state.error_type === 'api_key_limit_reached') {
                    showErrorModal(
                        'API Key / Limit Reached',
                        'The agent network has suspended operations. The API Key might be invalid, not set, or the request rate limit was reached.',
                        state.error_message || 'Quota exceeded (429) or invalid API Key.'
                    );
                } else {
                    showErrorModal(
                        'Agent Execution Failed',
                        'The pipeline stopped running due to a system error. The agent was unable to continue processing.',
                        state.error_message || 'General Agent failure.'
                    );
                }
            }
        })
        .catch(err => {
            console.error(err);
        });
    }, 1500);

    function appendLogLine(text, styleClass) {
        const line = document.createElement('div');
        line.className = `log-line ${styleClass}`;
        line.innerText = text;
        terminalBody.appendChild(line);
        terminalBody.scrollTop = terminalBody.scrollHeight;
    }
    
    function updateTimelineBar(stageName, lockedDuration, activeStage) {
        const bar = document.getElementById(`bar-${stageName}`);
        const text = document.getElementById(`dur-${stageName}`);
        
        if (!bar || !text) return;
        
        if (lockedDuration > 0 && stageName !== activeStage) {
            bar.style.width = '100%';
            bar.style.background = 'var(--accent-mint)'; // Completed stage
            text.innerText = `${lockedDuration.toFixed(1)}s`;
        } else if (stageName !== activeStage) {
            bar.style.width = '0%';
            bar.style.background = 'var(--accent-purple)';
            text.innerText = '0.0s';
        }
    }
    
    function setupLiveTimelineTicker(activeStage, timeline) {
        const activeBar = document.getElementById(`bar-${activeStage}`);
        const activeText = document.getElementById(`dur-${activeStage}`);
        
        if (!activeBar || !activeText) return;
        
        // Check if we need to start or restart the ticker
        if (activeTimelineTimer && activeTimelineTimer.stage === activeStage) {
            return; // Already running for this stage
        }
        
        if (activeTimelineTimer) {
            clearInterval(activeTimelineTimer);
        }
        
        // Start counter
        let startVal = timeline[activeStage] || 0.0;
        let elapsed = startVal;
        
        activeBar.style.background = 'var(--accent-purple)';
        
        const timer = setInterval(() => {
            elapsed += 0.1;
            activeText.innerText = `${elapsed.toFixed(1)}s`;
            // Grow bar up to 90% dynamically while waiting
            const widthPct = Math.min(10 + (elapsed * 8), 92);
            activeBar.style.width = `${widthPct}%`;
        }, 100);
        
        timer.stage = activeStage;
        activeTimelineTimer = timer;
    }

    function updateStepperCards(activeStage) {
        // Reset steps
        document.querySelectorAll('.step-card').forEach(card => {
            card.classList.remove('active', 'completed');
            card.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-clock"></i> Pending';
        });

        if (!activeStage) return;

        const stepOrchestrator = document.getElementById('step-orchestrator');
        const stepProspecting = document.getElementById('step-prospecting');
        const stepLinkedin = document.getElementById('step-linkedin');
        const stepContext = document.getElementById('step-context');
        const stepCopywriter = document.getElementById('step-copywriter');
        const stepProofreader = document.getElementById('step-proofreader');

        function markCompleted(el) {
            if (el) {
                el.classList.add('completed');
                el.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-circle-check"></i> Completed';
            }
        }
        function markActive(el) {
            if (el) {
                el.classList.add('active');
                el.querySelector('.step-status').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Active';
            }
        }

        // Orchestrator is always completed by the time per-prospect stages start
        markCompleted(stepOrchestrator);

        if (activeStage === 'prospecting') {
            markActive(stepProspecting);
        } else if (activeStage === 'linkedin') {
            markCompleted(stepProspecting);
            markActive(stepLinkedin);
        } else if (activeStage === 'context') {
            markCompleted(stepProspecting);
            markCompleted(stepLinkedin);
            markActive(stepContext);
        } else if (activeStage === 'copywriting') {
            markCompleted(stepProspecting);
            markCompleted(stepLinkedin);
            markCompleted(stepContext);
            markActive(stepCopywriter);
        } else if (activeStage.startsWith('proofreading') || activeStage === 'generating_audio') {
            markCompleted(stepProspecting);
            markCompleted(stepLinkedin);
            markCompleted(stepContext);
            markCompleted(stepCopywriter);
            markActive(stepProofreader);
        }
    }
}


/* ==========================================================================
   RESULTS: SEARCH / FILTER TABLE ROW INTERACTION
   ========================================================================== */

function initResultsFilter() {
    const filterInput = document.getElementById('table-filter');
    if (!filterInput) return;

    filterInput.addEventListener('input', (e) => {
        currentSearchQuery = e.target.value.toLowerCase();
        applyCombinedFilters();
    });
}

/* ==========================================================================
   RESULTS: EMAIL CUSTOMIZER PREVIEW MODAL
   ========================================================================== */

function openPreviewModal(campaignIdOrElement, prospect) {
    if (campaignIdOrElement instanceof HTMLElement) {
        currentCampaignId = campaignIdOrElement.getAttribute('data-campaign-id');
        currentProspectData = JSON.parse(campaignIdOrElement.getAttribute('data-prospect'));
    } else {
        currentCampaignId = campaignIdOrElement;
        currentProspectData = prospect;
    }
    const prospect = currentProspectData;

    const modal = document.getElementById('preview-modal');
    
    // Fill fields
    document.getElementById('modal-email-to').value = prospect.email;
    document.getElementById('modal-email-subject').value = prospect.email_subject || `Outreach to ${prospect.company}`;
    document.getElementById('modal-email-body').value = prospect.email_body || '';
    
    // Editor score / critique details
    document.getElementById('modal-rating-score').innerText = prospect.proofread_score ? `${prospect.proofread_score}/10` : '—';
    document.getElementById('modal-critique-box').innerText = prospect.proofread_critique || 'No critical review generated.';
    
    // Fill Personalization Hooks List
    const hooksContainer = document.getElementById('modal-hooks-list');
    hooksContainer.innerHTML = '';
    const hooks = prospect.prospect_data?.key_interests || ["Job Title / Company News Match"];
    hooks.forEach(h => {
        const li = document.createElement('li');
        li.innerText = h;
        hooksContainer.appendChild(li);
    });

    // Reset Send Status
    const sendStatus = document.getElementById('modal-send-status');
    sendStatus.innerText = '';
    sendStatus.className = 'send-status-text';

    // Show/hide audio components
    const audioWrapper = document.getElementById('modal-audio-player-wrapper');
    const audioPlayer = document.getElementById('modal-audio-player');
    const genAudioBtn = document.getElementById('modal-gen-audio-btn');

    if (prospect.audio_path) {
        audioPlayer.src = prospect.audio_path;
        audioWrapper.classList.remove('hidden');
        genAudioBtn.classList.add('hidden');
    } else {
        audioPlayer.src = '';
        audioWrapper.classList.add('hidden');
        genAudioBtn.classList.remove('hidden');
    }

    // Configure Action Buttons
    const sendBtn = document.getElementById('modal-send-btn');
    sendBtn.disabled = false;
    sendBtn.onclick = handleSendEmail;

    genAudioBtn.onclick = handleGenerateAudio;

    // Open modal
    modal.classList.remove('hidden');
}

function closePreviewModal() {
    const modal = document.getElementById('preview-modal');
    const audioPlayer = document.getElementById('modal-audio-player');
    if (audioPlayer) {
        audioPlayer.pause();
    }
    modal.classList.add('hidden');
}

function showErrorModal(title, message, details = '') {
    const modal = document.getElementById('error-modal');
    if (!modal) return;
    
    document.getElementById('error-modal-title').innerText = title;
    document.getElementById('error-modal-message').innerText = message;
    
    const detailsBox = document.getElementById('error-modal-details');
    if (details) {
        detailsBox.innerText = details;
        detailsBox.style.display = 'block';
    } else {
        detailsBox.style.display = 'none';
    }
    
    modal.classList.remove('hidden');
}

function closeErrorModal() {
    const modal = document.getElementById('error-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function handleSendEmail() {
    const to = document.getElementById('modal-email-to').value;
    const subject = document.getElementById('modal-email-subject').value;
    const body = document.getElementById('modal-email-body').value;
    const sendStatus = document.getElementById('modal-send-status');
    const sendBtn = document.getElementById('modal-send-btn');

    sendStatus.innerText = 'Sending email...';
    sendStatus.className = 'send-status-text sending';
    sendBtn.disabled = true;

    fetch('/api/send-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: to,
            subject: subject,
            body: body,
            campaign_id: currentCampaignId,
            prospect_id: currentProspectData.id
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            sendStatus.innerText = `Error: ${data.error}`;
            sendStatus.className = 'send-status-text error';
            sendBtn.disabled = false;
            showToast(`Failed to send email: ${data.error}`, 'error');
            return;
        }

        sendStatus.innerText = 'Email Sent Successfully!';
        sendStatus.className = 'send-status-text success';
        showToast('Cold email successfully sent!', 'success');
        
        // Update table row dynamically
        setTimeout(() => {
            const row = document.querySelector(`.prospect-row[data-id="${currentProspectData.id}"]`);
            if (row) {
                row.setAttribute('data-status', 'sent');
                
                // Update status badge
                const statusBadge = row.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge sent';
                    statusBadge.innerText = 'Sent';
                }
                
                // Re-apply filters
                if (typeof applyCombinedFilters === 'function') {
                    applyCombinedFilters();
                }
                
                // Update interactive counters
                const statApproved = document.getElementById('stat-approved');
                if (statApproved) {
                    const approvedCount = document.querySelectorAll('.prospect-row[data-status="approved"], .prospect-row[data-status="sent"]').length;
                    statApproved.innerText = approvedCount;
                }
            }
            closePreviewModal();
        }, 1200);
    })
    .catch(err => {
        console.error(err);
        sendStatus.innerText = 'Network error sending email.';
        sendStatus.className = 'send-status-text error';
        sendBtn.disabled = false;
    });
}

function handleGenerateAudio() {
    const text = document.getElementById('modal-email-body').value;
    const genAudioBtn = document.getElementById('modal-gen-audio-btn');
    const audioWrapper = document.getElementById('modal-audio-player-wrapper');
    const audioPlayer = document.getElementById('modal-audio-player');

    genAudioBtn.disabled = true;
    genAudioBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Rendering...';
    showToast('Rendering gTTS voicemail audio...', 'info');

    fetch('/api/generate-audio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            campaign_id: currentCampaignId,
            prospect_id: currentProspectData.id
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            genAudioBtn.disabled = false;
            genAudioBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Audio';
            showToast('Voicemail rendering failed.', 'error');
            return;
        }

        audioPlayer.src = data.audio_url;
        audioWrapper.classList.remove('hidden');
        genAudioBtn.classList.add('hidden');
        showToast('Voicemail audio generated successfully!', 'success');
    })
    .catch(err => {
        console.error(err);
        genAudioBtn.disabled = false;
        genAudioBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Audio';
        showToast('Error sending audio requests.', 'error');
    });
}
