/* ═══════════════════════════════════════════════════════════════════════════
   Novel Studio — Aurora Engine Controller v3.0
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── Application State ─────────────────────────────────────────────────────
  const state = {
    currentStep: 1,
    currentJobId: null,
    scenes: [],
    characters: {},
    isProcessing: false,
    inputMode: 'lib', // 'lib' or 'raw'
    currentNovelTitle: null,
    currentChapterPath: null,
    currentChapterId: null,
    terminalLines: []
  };

  // ── DOM Utilities ─────────────────────────────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ── Initialization ────────────────────────────────────────────────────────
  window.addEventListener('DOMContentLoaded', () => {
    loadLibrary();
    checkHealth();

    // Initialize with fade-in animation
    document.body.style.opacity = '0';
    setTimeout(() => {
      document.body.style.transition = 'opacity 0.5s ease';
      document.body.style.opacity = '1';
    }, 50);
  });

  // ── Navigation ────────────────────────────────────────────────────────────
  window.switchStep = function (stepNum) {
    // Validation: Block stepping forward if no job or cached chapter
    if (stepNum > 1 && !state.currentJobId && !state.currentChapterId) {
      showToast('Please ignite the engine first by selecting a chapter.', 'warning');
      return;
    }

    // Update State
    state.currentStep = stepNum;

    // Update Sidebar
    $$('.nav-step').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.step) === stepNum);
    });

    // Update Workspace with staggered animation
    $$('.step-container').forEach(el => {
      el.classList.remove('active');
    });

    const targetStep = $(`#step-${stepNum}`);
    if (targetStep) {
      setTimeout(() => targetStep.classList.add('active'), 50);
    }

    // Lifecycle hooks
    if (stepNum === 2) {
      loadScenes(state.currentChapterId);
    } else if (stepNum === 3) {
      loadCharacters();
    }
  };

  // Helper to reset for a new novel/chapter
  window.resetForNewChapter = function () {
    state.currentJobId = null;
    state.currentChapterId = null;
    state.currentChapterPath = null;
    state.scenes = [];
    state.characters = {};
  };

  // ── Step 1: Library & Ignition ────────────────────────────────────────────

  window.switchLibraryTab = function (mode) {
    state.inputMode = mode;

    // UI Toggles with smooth transition
    $('#btn-tab-lib').classList.toggle('active', mode === 'lib');
    $('#btn-tab-raw').classList.toggle('active', mode === 'raw');

    const libTab = $('#tab-library');
    const rawTab = $('#tab-raw');

    if (mode === 'lib') {
      rawTab.style.opacity = '0';
      setTimeout(() => {
        rawTab.style.display = 'none';
        libTab.style.display = 'block';
        setTimeout(() => libTab.style.opacity = '1', 50);
      }, 200);
    } else {
      libTab.style.opacity = '0';
      setTimeout(() => {
        libTab.style.display = 'none';
        rawTab.style.display = 'block';
        setTimeout(() => rawTab.style.opacity = '1', 50);
      }, 200);
    }
  };

  // Library Logic
  async function loadLibrary() {
    const grid = $('#novel-grid');
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1/-1;">
        <i data-lucide="loader-2" class="animate-spin" style="width: 40px; height: 40px;"></i>
        <div class="empty-state-title">Loading Library...</div>
      </div>
    `;
    lucide.createIcons();

    try {
      const res = await fetch('/api/library');
      const novels = await res.json();
      renderNovelGrid(novels);
    } catch (e) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1/-1; border-color: var(--error);">
          <i data-lucide="alert-circle" style="width: 40px; height: 40px; color: var(--error);"></i>
          <div class="empty-state-title">Failed to Load Library</div>
          <p>${escapeHtml(e.message)}</p>
        </div>
      `;
      lucide.createIcons();
    }
  }

  function renderNovelGrid(novels) {
    const grid = $('#novel-grid');
    if (!novels.length) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1/-1;">
          <i data-lucide="book" style="width: 48px; height: 48px;"></i>
          <div class="empty-state-title">No Novels Found</div>
          <p>Upload an EPUB file to begin your creative journey</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    grid.innerHTML = novels.map(novel => `
      <div class="novel-card" onclick="selectNovel('${escapeJsString(novel.title)}')">
        <button class="novel-delete-btn" onclick="event.stopPropagation(); deleteNovel('${escapeJsString(novel.title)}')" title="Delete novel">
          <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
        </button>
        <button class="novel-edit-btn" onclick="event.stopPropagation(); openEditTitleModal('${escapeJsString(novel.title)}')" title="Edit title">
          <i data-lucide="pencil" style="width: 14px; height: 14px;"></i>
        </button>
        <div class="novel-cover">
          ${novel.title.charAt(0).toUpperCase()}
        </div>
        <div>
          <div class="novel-title" title="${escapeHtml(novel.title)}">${escapeHtml(novel.title)}</div>
          <div class="novel-meta">
            <span>${escapeHtml(novel.author || 'Unknown Author')}</span>
            <span>•</span>
            <span>${novel.chapter_count} chapters</span>
          </div>
        </div>
      </div>
    `).join('');
    lucide.createIcons();
  }

  window.handleEpubUpload = async function (input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];

    const formData = new FormData();
    formData.append('file', file);

    const btn = input.nextElementSibling;
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="animate-spin" style="width: 16px; height: 16px;"></i> Uploading...`;
    lucide.createIcons();

    try {
      const res = await fetch('/api/library/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      showToast('Novel uploaded successfully!', 'success');
      loadLibrary();

    } catch (e) {
      showToast(`Upload failed: ${e.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalHTML;
      input.value = '';
      lucide.createIcons();
    }
  };

  // ── Edit Novel Title ──────────────────────────────────────────────────────
  window.editingNovelTitle = null;

  window.openEditTitleModal = function (currentTitle) {
    window.editingNovelTitle = currentTitle;
    const modal = $('#edit-title-modal');
    const input = $('#edit-title-input');

    input.value = currentTitle;
    modal.style.display = 'flex';

    // Focus input after a short delay for the transition
    setTimeout(() => input.focus(), 100);
  };

  window.closeEditTitleModal = function () {
    const modal = $('#edit-title-modal');
    modal.style.display = 'none';
    window.editingNovelTitle = null;
  };

  window.saveNovelTitle = async function () {
    if (!window.editingNovelTitle) return;

    const newTitle = $('#edit-title-input').value.trim();

    if (!newTitle) {
      showToast('Title cannot be empty', 'warning');
      return;
    }

    try {
      showToast('Updating title...', 'info');

      const res = await fetch(`/api/library/${encodeURIComponent(window.editingNovelTitle)}/title`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Failed to update title');
      }

      showToast('Title updated successfully', 'success');
      closeEditTitleModal();

      // Reload the library to reflect changes
      loadLibrary();

    } catch (e) {
      showToast(`Update failed: ${e.message}`, 'error');
    }
  };

  // Close modal when clicking outside
  $('#edit-title-modal').addEventListener('click', function (e) {
    if (e.target === this) {
      closeEditTitleModal();
    }
  });

  // Save on Enter key
  $('#edit-title-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
      saveNovelTitle();
    }
  });

  window.deleteNovel = async function (novelTitle) {
    // Show confirmation dialog
    const confirmed = confirm(`Are you sure you want to delete "${novelTitle}"?\n\nThis will permanently remove the novel and all associated chapters, images, audio, and video files. This action cannot be undone.`);

    if (!confirmed) return;

    try {
      showToast(`Deleting "${novelTitle}"...`, 'info');

      const res = await fetch(`/api/library/${encodeURIComponent(novelTitle)}`, {
        method: 'DELETE'
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Failed to delete novel');
      }

      showToast(`"${novelTitle}" deleted successfully`, 'success');

      // Reload the library to reflect changes
      loadLibrary();

      // Reset state if the deleted novel was currently selected
      if (state.currentNovelTitle === novelTitle) {
        state.currentNovelTitle = null;
        state.currentChapterPath = null;
        state.currentChapterId = null;
        state.currentJobId = null;
        state.scenes = [];
      }

    } catch (e) {
      showToast(`Delete failed: ${e.message}`, 'error');
    }
  };

  window.selectNovel = async function (title) {
    state.currentNovelTitle = title;
    $('#selected-novel-title').textContent = title;

    // UI Transitions
    const grid = $('#novel-grid');
    const chapterContainer = $('#chapter-list-container');

    grid.style.opacity = '0';
    setTimeout(() => {
      grid.style.display = 'none';
      chapterContainer.style.display = 'block';
      setTimeout(() => chapterContainer.style.opacity = '1', 50);
    }, 200);

    $('.tabs-header').style.display = 'none';

    const list = $('#chapter-list');
    list.innerHTML = `
      <div class="chapter-item" style="justify-content: center; cursor: default;">
        <i data-lucide="loader-2" class="animate-spin" style="width: 18px; height: 18px;"></i>
        <span style="margin-left: 0.5rem;">Loading chapters...</span>
      </div>
    `;
    lucide.createIcons();

    try {
      const res = await fetch(`/api/library/${encodeURIComponent(title)}/chapters`);
      const chapters = await res.json();
      renderChapterList(chapters);
    } catch (e) {
      list.innerHTML = `
        <div class="chapter-item" style="border-color: var(--error); color: var(--error);">
          <span>Failed to load chapters: ${escapeHtml(e.message)}</span>
        </div>
      `;
    }
  };

  window.closeChapterList = function () {
    const grid = $('#novel-grid');
    const chapterContainer = $('#chapter-list-container');

    chapterContainer.style.opacity = '0';
    setTimeout(() => {
      chapterContainer.style.display = 'none';
      grid.style.display = 'grid';
      setTimeout(() => grid.style.opacity = '1', 50);
    }, 200);

    $('.tabs-header').style.display = 'flex';
    state.currentNovelTitle = null;
  };

  // Common terms to filter out as non-content chapters
  const TOC_TERMS = [
    'table of contents', 'contents', 'toc',
    'copyright', 'dedication', 'acknowledgements', 'acknowledgments',
    'about the author', 'about this book', 'preface', 'foreword',
    'introduction', 'prologue', 'epilogue', 'appendix', 'glossary',
    'index', 'bibliography', 'references', 'also by'
  ];

  function isChapterContent(chapter) {
    const title = (chapter.title || '').toLowerCase().trim();
    // Check if title matches any TOC/non-content terms
    return !TOC_TERMS.some(term => title === term || title.startsWith(term + ' '));
  }

  function escapeJsString(str) {
    // Escape backslashes and single quotes for JavaScript string literals
    if (!str) return '';
    return str
      .replace(/\\/g, '\\\\')  // Escape backslashes first
      .replace(/'/g, "\\'")     // Escape single quotes
      .replace(/"/g, '\\"')     // Escape double quotes
      .replace(/\n/g, '\\n')    // Escape newlines
      .replace(/\r/g, '\\r')    // Escape carriage returns
      .replace(/\t/g, '\\t');   // Escape tabs
  }

  function renderChapterList(chapters) {
    const list = $('#chapter-list');

    // Filter out non-content chapters
    const contentChapters = chapters.filter(isChapterContent);

    if (!contentChapters.length) {
      list.innerHTML = `
        <div class="empty-state" style="padding: 2rem;">
          <i data-lucide="file-x" style="width: 32px; height: 32px;"></i>
          <p>No valid chapters found in this novel.</p>
          <p style="font-size: var(--text-xs); margin-top: 0.5rem;">Table of Contents and metadata pages are filtered out.</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    list.innerHTML = contentChapters.map((ch, index) => {
      const p = ch.progress || {};
      const indicators = `
        <div style="display: flex; gap: 0.25rem; margin-right: 0.75rem;" title="Extraction > Images > Audio > Video">
          <div style="width: 8px; height: 8px; border-radius: 50%; background: ${p.scenes ? 'var(--primary)' : 'var(--border)'};" title="Scenes Extracted"></div>
          <div style="width: 8px; height: 8px; border-radius: 50%; background: ${p.images ? 'var(--primary)' : 'var(--border)'};" title="Images Generated"></div>
          <div style="width: 8px; height: 8px; border-radius: 50%; background: ${p.audio ? 'var(--primary)' : 'var(--border)'};" title="Audio Generated"></div>
          <div style="width: 8px; height: 8px; border-radius: 50%; background: ${p.video ? 'var(--success)' : 'var(--border)'};" title="Video Assembly"></div>
        </div>
      `;

      let statusBadge = '';
      if (ch.status === 'completed') {
        statusBadge = `<span style="font-size: var(--text-xs); background: rgba(16, 185, 129, 0.1); color: var(--success); padding: 0.125rem 0.5rem; border-radius: 999px; border: 1px solid rgba(16, 185, 129, 0.2);">Completed</span>`;
      } else if (ch.status === 'extracted') {
        statusBadge = `<span style="font-size: var(--text-xs); background: rgba(139, 92, 246, 0.1); color: var(--primary); padding: 0.125rem 0.5rem; border-radius: 999px; border: 1px solid rgba(139, 92, 246, 0.2);">Extracted</span>`;
      } else {
        statusBadge = `<span style="font-size: var(--text-xs); color: var(--text-dim);">Pending</span>`;
      }

      return `
      <div class="chapter-item" style="cursor: pointer;">
        <div style="display: flex; align-items: center; gap: 0.75rem; flex-grow: 1;" onclick="igniteChapter('${escapeJsString(ch.path)}', '${escapeJsString(ch.status || 'pending')}', '${escapeJsString(ch.id)}')">
          <span style="font-family: var(--font-mono); color: var(--text-dim); font-size: var(--text-xs);">${String(index + 1).padStart(4, '0')}</span>
          <span style="font-weight: 500;">${escapeHtml(ch.title || 'Untitled Chapter')}</span>
        </div>
        <div style="display: flex; align-items: center;">
          ${indicators}
          <div style="display: flex; align-items: center; gap: 0.5rem;" onclick="igniteChapter('${escapeJsString(ch.path)}', '${escapeJsString(ch.status || 'pending')}', '${escapeJsString(ch.id)}')">
            ${statusBadge}
          </div>
          <button class="btn-secondary" style="margin-left: 1rem; padding: 0.35rem 0.6rem; font-size: 0.75rem;" onclick="event.stopPropagation(); triggerFullPipeline('${escapeJsString(ch.id)}', '${escapeJsString(ch.path)}')" title="Run Full Pipeline">
            <i data-lucide="play" style="width: 14px; height: 14px;"></i>
          </button>
        </div>
      </div>
    `}).join('');
    lucide.createIcons();
  }

  // Ignition Logic
  window.triggerFullPipeline = async function (chapterId, chapterPath) {
    state.currentChapterId = chapterId;
    state.currentChapterPath = chapterPath;
    state.currentJobId = null;
    switchStep(4);
    setTimeout(() => {
      runFullPipeline();
    }, 500);
  };

  window.igniteChapter = async function (chapterPath, status = 'pending', chapterId = null) {
    // Reset state for new extraction
    state.currentChapterPath = chapterPath;
    state.currentChapterId = chapterId;
    state.currentJobId = null;
    state.scenes = [];
    state.characters = {};

    if (status === 'extracted' || status === 'completed') {
      // Skip extraction and go straight to Vision
      showToast('Loading existing extraction...', 'info');
      switchStep(2);
    } else {
      ignite({ chapter_path: chapterPath, force_extract: false, novel_title: state.currentNovelTitle });
    }
  };

  window.redoExtraction = async function () {
    if (!state.currentChapterPath && !state.currentNovelTitle) {
      showToast('No chapter selected.', 'warning');
      return;
    }

    const confirmRedo = confirm("Are you sure you want to redo extraction? This will overwrite your existing scenes and characters.");
    if (!confirmRedo) return;

    // Clear local state so the UI reflects the regeneration state
    state.scenes = [];
    state.characters = {};
    renderScenes(state.scenes);

    // Call ignite with force_extract = true
    ignite({
      chapter_path: state.currentChapterPath,
      force_extract: true,
      novel_title: state.currentNovelTitle
    });
  };

  window.startExtraction = async function () {
    const textInput = $('#raw-text-input');
    const text = textInput.value.trim();

    if (!text) {
      showToast('Please provide narrative text.', 'warning');
      textInput.focus();
      return;
    }

    ignite({ text: text, force_extract: true, novel_title: state.currentNovelTitle });
  };

  async function ignite(payload) {
    showToast('Igniting Aurora Engine...', 'info');
    state.isProcessing = true;

    try {
      const res = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      // Handle cached results - scenes already exist
      if (data.status === 'cached') {
        state.currentJobId = data.job_id;
        if (data.chapter_id) state.currentChapterId = data.chapter_id;

        showToast(`Using cached scenes (${data.scenes_count} scenes)`, 'info');
        setTimeout(() => switchStep(2), 500);
        state.isProcessing = false;
        return;
      }

      // For new extractions, wait for completion via SSE
      const jobId = data.job_id;

      showLoadingOverlay('Igniting Aurora Engine...');

      // Monitor progress via SSE
      await waitForExtraction(jobId);

      state.currentJobId = jobId;
      showToast('Extraction complete!', 'success');
      setTimeout(() => switchStep(2), 500);

    } catch (e) {
      hideLoadingOverlay();
      showToast(`Ignition Error: ${e.message}`, 'error');
    } finally {
      state.isProcessing = false;
    }
  }

  // Overlay Helpers
  function showLoadingOverlay(title = "Processing...") {
    const overlay = $('#global-loading-overlay');
    if (!overlay) return;
    $('#loading-title').innerText = title;
    $('#loading-detail').innerText = "Initializing systems";
    $('#loading-progress-bar').style.width = "0%";
    overlay.style.display = 'flex';
    overlay.style.opacity = '1';
  }

  function updateLoadingOverlay(percent, detail) {
    if (percent >= 0 && $('#loading-progress-bar')) {
      $('#loading-progress-bar').style.width = `${percent}%`;
    }
    if (detail && $('#loading-detail')) {
      $('#loading-detail').innerText = detail;
    }
  }

  function hideLoadingOverlay() {
    const overlay = $('#global-loading-overlay');
    if (!overlay) return;
    overlay.style.opacity = '0';
    setTimeout(() => overlay.style.display = 'none', 300);
  }

  function waitForExtraction(jobId) {
    return new Promise((resolve, reject) => {
      const evtSource = new EventSource(`/api/progress/${jobId}`);
      let completed = false;

      evtSource.onmessage = (e) => {
        const msg = JSON.parse(e.data);

        updateLoadingOverlay(msg.percent, msg.detail);

        if (msg.step === 'complete') {
          completed = true;
          evtSource.close();
          hideLoadingOverlay();
          if (msg.chapter_id) state.currentChapterId = msg.chapter_id;
          resolve(msg);
        }

        if (msg.step === 'error') {
          completed = true;
          evtSource.close();
          hideLoadingOverlay();
          reject(new Error(msg.detail || 'Extraction failed'));
        }
      };

      evtSource.onerror = (e) => {
        if (!completed) {
          evtSource.close();
          hideLoadingOverlay();
          reject(new Error('Connection lost during extraction'));
        }
      };

      // Timeout after 5 minutes
      setTimeout(() => {
        if (!completed) {
          evtSource.close();
          reject(new Error('Extraction timeout'));
        }
      }, 300000);
    });
  }

  // ── Step 2: The Vision (Scenes) ───────────────────────────────────────────
  async function loadScenes(chapterId) {
    if (!chapterId) {
      console.warn('loadScenes called without chapterId');
      return;
    }

    const container = $('#scenes-container');

    // Clear cached scenes if switching to a different chapter
    if (state.currentChapterId !== chapterId) {
      state.scenes = [];
    }

    // Use cached scenes if available for this job
    if (state.scenes.length > 0) {
      renderScenes(state.scenes);
      return;
    }

    container.innerHTML = `
      <div class="empty-state">
        <i data-lucide="loader-2" class="animate-spin" style="width: 40px; height: 40px;"></i>
        <div class="empty-state-title">Loading Scenes...</div>
        <p>Retrieving extracted scenes</p>
      </div>
    `;
    lucide.createIcons();

    try {
      const safeTitle = encodeURIComponent(state.currentNovelTitle);
      const res = await fetch(`/api/novels/${safeTitle}/scenes/${chapterId}`);

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${res.status}`);
      }

      const data = await res.json();

      // Handle array response (scenes list)
      if (Array.isArray(data)) {
        state.scenes = data;
      } else if (data.scenes && Array.isArray(data.scenes)) {
        state.scenes = data.scenes;
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        throw new Error('Invalid response format');
      }

      renderScenes(state.scenes);
    } catch (e) {
      console.error('Failed to load scenes:', e);
      container.innerHTML = `
        <div class="empty-state" style="border-color: var(--error);">
          <i data-lucide="alert-circle" style="width: 48px; height: 48px; color: var(--error);"></i>
          <div class="empty-state-title">Failed to Load Scenes</div>
          <p>${escapeHtml(e.message)}</p>
          <button class="btn-secondary mt-4" onclick="loadScenes('${chapterId}')">
            <i data-lucide="refresh-cw" style="width: 16px; height: 16px;"></i>
            Retry
          </button>
        </div>
      `;
      lucide.createIcons();
    }
  }

  window.generateAllImages = async function () {
    if (!state.currentChapterId) return;

    try {
      showToast('Initiating batch image generation...', 'info');

      // Show mini overlays for all scenes
      state.scenes.forEach((_, i) => {
        const overlay = document.getElementById(`img-progress-overlay-${i}`);
        if (overlay) overlay.style.display = 'flex';
        const btn = document.getElementById(`btn-gen-img-${i}`);
        if (btn) btn.disabled = true;
      });

      const res = await fetch('/api/generate/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chapter_id: state.currentChapterId,
          job_id: state.currentJobId,
          scene_indices: state.scenes.map((_, i) => i),
          novel_title: state.currentNovelTitle
        })
      });
      const data = await res.json();
      monitorGeneration(data.job_id);
    } catch (e) {
      document.querySelectorAll('.image-progress-overlay').forEach(el => el.style.display = 'none');
      showToast('Generation failed: ' + e.message, 'error');
    }
  };

  window.generateSceneImage = async function (idx) {
    if (!state.currentChapterId) return;
    const btn = document.getElementById(`btn-gen-img-${idx}`);
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<i data-lucide="loader-2" class="animate-spin" style="width: 14px; height: 14px;"></i> Generating...`;
      lucide.createIcons();
    }

    // Enable local progress overlay
    const overlay = document.getElementById(`img-progress-overlay-${idx}`);
    if (overlay) overlay.style.display = 'flex';

    try {
      const res = await fetch('/api/generate/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter_id: state.currentChapterId, job_id: state.currentJobId, scene_indices: [idx], novel_title: state.currentNovelTitle })
      });
      const data = await res.json();
      monitorGeneration(data.job_id, idx);
    } catch (e) {
      if (overlay) overlay.style.display = 'none';
      showToast('Generation failed: ' + e.message, 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="image" style="width: 14px; height: 14px;"></i> Generate`;
        lucide.createIcons();
      }
    }
  };

  function monitorGeneration(jobId, specificIdx = null) {
    const evtSource = new EventSource(`/api/progress/${jobId}`);

    evtSource.onmessage = (e) => {
      const msg = JSON.parse(e.data);

      // Parse the 'Scene X' out of the message if applicable
      let activeIdx = specificIdx;
      if (msg.detail) {
        const match = msg.detail.match(/Scene (\d+)/i);
        if (match) {
          activeIdx = parseInt(match[1], 10);
        }
      }

      if (activeIdx !== null) {
        const pb = document.getElementById(`img-progress-bar-${activeIdx}`);
        const pt = document.getElementById(`img-progress-text-${activeIdx}`);

        if (pb) pb.style.width = `${msg.percent}%`;
        if (pt) pt.innerText = msg.detail || 'Generating...';

        const overlay = document.getElementById(`img-progress-overlay-${activeIdx}`);
        if (overlay) overlay.style.display = 'flex';
      }

      if (msg.chapter_id) state.currentChapterId = msg.chapter_id;

      if (msg.step === 'complete') {
        evtSource.close();
        document.querySelectorAll('.image-progress-overlay').forEach(el => el.style.display = 'none');
        showToast('Images generated successfully!', 'success');

        if (specificIdx !== null) {
          refreshImage(specificIdx);
        } else {
          state.scenes.forEach((_, i) => refreshImage(i));
        }
      }

      if (msg.step === 'error') {
        evtSource.close();
        document.querySelectorAll('.image-progress-overlay').forEach(el => el.style.display = 'none');
        showToast('Generation error: ' + msg.detail, 'error');

        state.scenes.forEach((_, i) => {
          const btn = document.getElementById(`btn-gen-img-${i}`);
          if (btn) btn.disabled = false;
        });
      }
    };

    evtSource.onerror = () => {
      document.querySelectorAll('.image-progress-overlay').forEach(el => el.style.display = 'none');
      evtSource.close();
    };
  }

  function refreshImage(idx) {
    const img = $(`#img-scene-${idx}`);
    const btn = $(`#btn-gen-img-${idx}`);

    if (img) {
      const timestamp = new Date().getTime();
      const safeTitle = encodeURIComponent(state.currentNovelTitle);
      img.src = `/runs/${safeTitle}/${state.currentChapterId}/images/scene_${String(idx).padStart(3, '0')}.png?t=${timestamp}`;
      img.style.display = 'block';
    }

    if (btn) {
      btn.innerHTML = `<i data-lucide="refresh-cw" style="width: 14px; height: 14px;"></i> Regenerate`;
      btn.disabled = false;
    }
    lucide.createIcons();
  }

  // Helper to extract narration text from scene sequence
  function getSceneNarration(scene) {
    // If scene has narration field directly, use it
    if (scene.narration) return scene.narration;

    // Otherwise extract from sequence array
    const sequence = scene.sequence || [];
    const narrationParts = [];

    for (const item of sequence) {
      if (item.type === 'narration' && item.text) {
        narrationParts.push(item.text);
      } else if (item.type === 'dialogue' && item.text) {
        const speaker = item.speaker || 'Unknown';
        narrationParts.push(`${speaker}: "${item.text}"`);
      }
    }

    return narrationParts.join('\n\n');
  }

  function renderScenes(scenes) {
    const container = $('#scenes-container');

    if (!scenes || !scenes.length) {
      container.innerHTML = `
        <div class="empty-state">
          <i data-lucide="eye-off" style="width: 48px; height: 48px;"></i>
          <div class="empty-state-title">No Scenes Found</div>
          <p>No visual scenes were extracted from this chapter.</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    container.innerHTML = scenes.map((scene, i) => `
      <div class="scene-card">
        <div class="scene-header">
          <div>
            <span class="status-badge info" style="margin-bottom: 0.5rem; display: inline-flex;">
              Scene ${i + 1}
            </span>
            <h3 class="scene-title">${escapeHtml(scene.title || 'Untitled Scene')}</h3>
          </div>
        </div>
        
        <div class="scene-content">
          <div class="scene-form">
            <div class="form-group">
              <label>Visual Description</label>
              <textarea class="aurora-input" rows="3" id="scene-desc-${i}">${escapeHtml(scene.visual_description || '')}</textarea>
            </div>
            <div class="form-group">
              <label>Narration</label>
              <textarea class="aurora-input" rows="3" style="font-family: var(--font-body);" id="scene-narration-${i}">${escapeHtml(getSceneNarration(scene))}</textarea>
            </div>
          </div>
          
          <div class="scene-image" style="position: relative; overflow: hidden; border-radius: var(--radius-md);">
            <img id="img-scene-${i}" 
                 src="/runs/${encodeURIComponent(state.currentNovelTitle)}/${state.currentChapterId}/images/scene_${String(i).padStart(3, '0')}.png" 
                 onerror="this.style.display='none'"
                 alt="Scene ${i + 1}" />

            <!-- Local Generation Progress Overlay -->
            <div id="img-progress-overlay-${i}" class="image-progress-overlay" style="display: none; position: absolute; inset: 0; background: rgba(10, 10, 15, 0.85); flex-direction: column; align-items: center; justify-content: center; backdrop-filter: blur(4px); z-index: 10;">
              <i data-lucide="loader-2" class="animate-spin" style="width: 24px; height: 24px; color: var(--primary);"></i>
              <div id="img-progress-text-${i}" style="margin-top: 10px; font-size: var(--text-xs); color: var(--text-dim); text-align: center; padding: 0 10px;">Waiting...</div>
              <div style="width: 80%; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; margin-top: 8px; overflow: hidden;">
                <div id="img-progress-bar-${i}" style="height: 100%; width: 0%; background: var(--primary); transition: width 0.3s ease;"></div>
              </div>
            </div>
            
            <button id="btn-gen-img-${i}" class="btn-secondary" onclick="generateSceneImage(${i})" style="font-size: var(--text-xs); z-index: 11; position: relative;">
              <i data-lucide="image" style="width: 14px; height: 14px;"></i>
              Generate Image
            </button>
          </div>
        </div>
      </div>
    `).join('');
    lucide.createIcons();

    // Check for existing images and update button state
    scenes.forEach((_, i) => {
      const img = document.getElementById(`img-scene-${i}`);
      if (img) {
        img.onload = () => {
          img.style.display = 'block';
          const btn = document.getElementById(`btn-gen-img-${i}`);
          if (btn) {
            btn.innerHTML = `<i data-lucide="refresh-cw" style="width: 14px; height: 14px;"></i> Regenerate`;
          }
          lucide.createIcons();
        };
      }
    });
  }

  // ── Step 3: Characters & Voices ───────────────────────────────────────────
  async function loadCharacters() {
    const container = $('#characters-container');

    container.innerHTML = `
      <div class="empty-state" style="grid-column: 1/-1;">
        <i data-lucide="loader-2" class="animate-spin" style="width: 40px; height: 40px;"></i>
        <div class="empty-state-title">Loading Characters...</div>
      </div>
    `;
    lucide.createIcons();

    try {
      const safeTitle = encodeURIComponent(state.currentNovelTitle);
      const res = await fetch(`/api/novels/${safeTitle}/characters`);
      const data = await res.json();

      if (Object.keys(data).length === 0) {
        container.innerHTML = `
          <div class="empty-state" style="grid-column: 1/-1;">
            <i data-lucide="users" style="width: 48px; height: 48px;"></i>
            <div class="empty-state-title">No Characters Found</div>
            <p>Characters will appear here after scene extraction</p>
          </div>
        `;
        lucide.createIcons();
        return;
      }

      container.innerHTML = Object.entries(data).map(([name, details]) => `
        <div class="character-card">
          <div class="character-header">
            <div class="character-avatar">
              ${name.substring(0, 2).toUpperCase()}
            </div>
            <div>
              <div class="character-name">${escapeHtml(name)}</div>
              <div class="character-role">${escapeHtml(details.gender || 'Unknown')} • ${escapeHtml(details.role || 'Character')}</div>
            </div>
          </div>
          <div class="character-description">
            ${escapeHtml(details.description || 'No description available.')}
          </div>
          <div class="character-footer">
            <span class="voice-badge">
              <i data-lucide="mic-2" style="width: 14px; height: 14px;"></i>
              ${details.voice_id ? 'Voice Assigned' : 'Auto-Cast'}
            </span>
            <button class="btn-ghost" style="padding: 0.375rem 0.75rem; font-size: var(--text-xs);">
              <i data-lucide="settings-2" style="width: 14px; height: 14px;"></i>
              Configure
            </button>
          </div>
        </div>
      `).join('');
      lucide.createIcons();

    } catch (e) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column: 1/-1; border-color: var(--error);">
          <i data-lucide="alert-circle" style="width: 48px; height: 48px; color: var(--error);"></i>
          <div class="empty-state-title">Error Loading Characters</div>
          <p>${escapeHtml(e.message)}</p>
        </div>
      `;
      lucide.createIcons();
    }
  }

  // ── Audio Generation ──────────────────────────────────────────────────────
  window.generateAllAudio = async function () {
    if (!state.currentChapterId) {
      showToast('No chapter selected.', 'warning');
      return;
    }

    showLoadingOverlay('Generating Audio...');
    try {
      const safeTitle = encodeURIComponent(state.currentNovelTitle);
      const res = await fetch(`/api/generate/audio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          novel_title: state.currentNovelTitle,
          chapter_id: state.currentChapterId,
          scene_indices: [] // empty array means generate all
        })
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      // Monitor progress
      const evtSource = new EventSource(`/api/progress/${data.job_id}`);
      evtSource.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        updateLoadingOverlay(msg.percent, msg.detail);

        if (msg.step === 'complete') {
          evtSource.close();
          hideLoadingOverlay();
          showToast('All audio generated successfully!', 'success');
        }

        if (msg.step === 'error') {
          evtSource.close();
          hideLoadingOverlay();
          showToast(`Audio generation failed: ${msg.detail}`, 'error');
        }
      };

      evtSource.onerror = () => {
        evtSource.close();
        hideLoadingOverlay();
        showToast('Connection lost during audio generation.', 'error');
      };
    } catch (e) {
      hideLoadingOverlay();
      showToast(`Error: ${e.message}`, 'error');
    }
  };

  // ── Step 4: Production Forge ──────────────────────────────────────────────
  window.runFullPipeline = async function () {
    if (!state.currentJobId && !state.currentChapterId) return;

    const btn = $('#btn-start-production');
    const terminal = $('#terminal-output');

    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="animate-spin" style="width: 16px; height: 16px;"></i> Forging...`;
    lucide.createIcons();

    // Clear and initialize terminal
    terminal.innerHTML = `
      <div class="terminal-line">
        <span class="terminal-timestamp">[${new Date().toLocaleTimeString()}]</span>
        <span class="terminal-info">Initializing Aurora Pipeline...</span>
      </div>
    `;

    try {
      const res = await fetch('/api/pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chapter_path: state.currentChapterPath || state.currentJobId,
          novel_title: state.currentNovelTitle
        })
      });

      const data = await res.json();
      const evtSource = new EventSource(`/api/progress/${data.job_id}`);

      evtSource.onmessage = (e) => {
        const msg = JSON.parse(e.data);

        if (msg.detail) {
          const line = document.createElement('div');
          line.className = 'terminal-line';
          line.innerHTML = `
            <span class="terminal-timestamp">[${new Date().toLocaleTimeString()}]</span>
            ${escapeHtml(msg.detail)}
          `;
          terminal.appendChild(line);
          terminal.scrollTop = terminal.scrollHeight;
        }

        if (msg.chapter_id) state.currentChapterId = msg.chapter_id;

        if (msg.step === 'complete') {
          evtSource.close();

          const completeLine = document.createElement('div');
          completeLine.className = 'terminal-line';
          completeLine.innerHTML = `
            <span class="terminal-timestamp">[${new Date().toLocaleTimeString()}]</span>
            <span class="terminal-success">✓ PRODUCTION COMPLETE</span>
          `;
          terminal.appendChild(completeLine);
          terminal.scrollTop = terminal.scrollHeight;

          btn.innerHTML = `<i data-lucide="check" style="width: 16px; height: 16px;"></i> Complete`;
          btn.disabled = false;

          showToast('Masterpiece created successfully!', 'success');
          lucide.createIcons();

          $('#final-video-container').style.display = 'block';
          loadFinalAssets();
        }

        if (msg.step === 'error') {
          evtSource.close();

          const errorLine = document.createElement('div');
          errorLine.className = 'terminal-line';
          errorLine.innerHTML = `
            <span class="terminal-timestamp">[${new Date().toLocaleTimeString()}]</span>
            <span class="terminal-error">✗ ERROR: ${escapeHtml(msg.detail || 'Unknown error')}</span>
          `;
          terminal.appendChild(errorLine);
          terminal.scrollTop = terminal.scrollHeight;

          btn.disabled = false;
          btn.innerHTML = `<i data-lucide="refresh-cw" style="width: 16px; height: 16px;"></i> Retry Production`;

          showToast('Production failed. Check terminal for details.', 'error');
          lucide.createIcons();
        }
      };

      evtSource.onerror = () => {
        evtSource.close();
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="play" style="width: 16px; height: 16px;"></i> Start Production`;
        lucide.createIcons();
      };

    } catch (e) {
      const errorLine = document.createElement('div');
      errorLine.className = 'terminal-line';
      errorLine.innerHTML = `
        <span class="terminal-timestamp">[${new Date().toLocaleTimeString()}]</span>
        <span class="terminal-error">✗ CRITICAL ERROR: ${escapeHtml(e.message)}</span>
      `;
      terminal.appendChild(errorLine);
      terminal.scrollTop = terminal.scrollHeight;

      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="refresh-cw" style="width: 16px; height: 16px;"></i> Retry Production`;
      lucide.createIcons();
    }
  };

  // ── Step 5: Cinema ────────────────────────────────────────────────────────
  function loadFinalAssets() {
    const container = $('#final-video-container');
    const downloadBtn = $('#btn-download');

    container.innerHTML = `
      <div class="empty-state" style="border: none;">
        <i data-lucide="loader-2" class="animate-spin" style="width: 48px; height: 48px;"></i>
        <div class="empty-state-title">Loading Video...</div>
      </div>
    `;
    lucide.createIcons();

    const outputKey = state.currentChapterId || state.currentJobId;

    const safeTitle = encodeURIComponent(state.currentNovelTitle);
    fetch(`/api/novels/${safeTitle}/outputs/${outputKey}`)
      .then(r => r.json())
      .then(data => {
        if (data.video && data.video.length) {
          const videoPath = data.video[0].name;
          container.innerHTML = `
            <video controls style="width:100%; height:100%; object-fit: contain;" poster="/runs/${outputKey}/images/scene_000.png">
              <source src="/runs/${outputKey}/${videoPath}" type="video/mp4">
              Your browser does not support the video tag.
            </video>
          `;
          downloadBtn.style.display = 'inline-flex';
          downloadBtn.onclick = () => {
            window.open(`/runs/${outputKey}/${videoPath}`, '_blank');
          };
        } else {
          container.innerHTML = `
            <div class="empty-state" style="border: none;">
              <i data-lucide="film" style="width: 64px; height: 64px;"></i>
              <div class="empty-state-title">No Video Found</div>
              <p>Complete the production pipeline to generate your video</p>
            </div>
          `;
          lucide.createIcons();
        }
      })
      .catch(() => {
        container.innerHTML = `
          <div class="empty-state" style="border: none;">
            <i data-lucide="film" style="width: 64px; height: 64px;"></i>
            <div class="empty-state-title">No Video Available</div>
            <p>Complete the production pipeline to generate your video</p>
          </div>
        `;
        lucide.createIcons();
      });
  }

  // ── Toast Notifications ───────────────────────────────────────────────────
  function showToast(message, type = 'info') {
    let toastContainer = $('.toast-container');

    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'toast-container';
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const iconMap = {
      success: 'check-circle',
      error: 'x-circle',
      warning: 'alert-triangle',
      info: 'info'
    };

    // Format message - convert newlines to <br> for display
    const formattedMessage = escapeHtml(message).replace(/\n/g, '<br>');

    toast.innerHTML = `
      <i data-lucide="${iconMap[type]}" style="width: 18px; height: 18px; margin-right: 0.75rem; flex-shrink: 0;"></i>
      <span style="white-space: pre-wrap;">${formattedMessage}</span>
    `;

    toastContainer.appendChild(toast);
    lucide.createIcons();

    // Auto-remove after delay
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // ── Utilities ─────────────────────────────────────────────────────────────
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function checkHealth() {
    fetch('/api/health')
      .then(r => r.json())
      .then(s => {
        const badge = $('#sys-status');
        if (s.status === 'ok') {
          badge.className = 'status-badge success';
          badge.innerHTML = `
            <span class="status-dot" style="box-shadow: 0 0 8px var(--success);"></span>
            System Online
          `;
        } else {
          badge.className = 'status-badge pending';
          badge.innerHTML = `
            <span class="status-dot"></span>
            System Degraded
          `;
        }
      })
      .catch(() => {
        const badge = $('#sys-status');
        badge.className = 'status-badge error';
        badge.innerHTML = `
          <span class="status-dot"></span>
          System Offline
        `;
      });
  }

  // Periodic health check
  setInterval(checkHealth, 30000);

})();
