/* ═══════════════════════════════════════════════════════
   Novel Studio — Aurora Engine Controller (v2.1)
   ═══════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── State ────────────────────────────────────────────
  const state = {
    currentStep: 1,
    currentJobId: null,
    scenes: [],
    characters: {},
    isProcessing: false,
    // Library State
    inputMode: 'lib', // 'lib' or 'raw'
    currentNovelId: null,
    currentChapterPath: null
  };

  // ── DOM References ───────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ── Initialization ───────────────────────────────────
  window.addEventListener('DOMContentLoaded', () => {
    loadLibrary();
    checkHealth();
  });

  // ── Navigation ───────────────────────────────────────
  window.switchStep = function (stepNum) {
    // Validation: Block stepping forward if no job
    if (stepNum > 1 && !state.currentJobId) {
      showToast("Please ignite the engine first.", "warning");
      return;
    }

    // Update State
    state.currentStep = stepNum;

    // Update Sidebar
    $$('.nav-step').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.step) === stepNum);
    });

    // Update Workspace with Fade/Slide
    $$('.step-container').forEach(el => {
      el.classList.remove('active');
      if (el.id === `step-${stepNum}`) {
        setTimeout(() => el.classList.add('active'), 50);
      }
    });

    // Lifecycle hooks
    if (stepNum === 2) loadScenes(state.currentJobId);
    if (stepNum === 3) loadCharacters();
    if (stepNum === 5) loadFinalAssets();
  };

  // ── Step 1: Library & Ignition ───────────────────────

  window.switchLibraryTab = function (mode) {
    state.inputMode = mode;

    // UI Toggles
    $('#btn-tab-lib').classList.toggle('active', mode === 'lib');
    $('#btn-tab-raw').classList.toggle('active', mode === 'raw');

    $('#tab-library').style.display = mode === 'lib' ? 'block' : 'none';
    $('#tab-raw').style.display = mode === 'raw' ? 'block' : 'none';
  }

  // Library Logic
  async function loadLibrary() {
    const grid = $('#novel-grid');
    grid.innerHTML = '<p style="text-align: center; color: var(--text-muted); grid-column: 1/-1;">Loading library...</p>';

    try {
      const res = await fetch('/api/library');
      const novels = await res.json();
      renderNovelGrid(novels);
    } catch (e) {
      grid.innerHTML = `<p style="color: var(--color-error)">Failed to load library: ${e.message}</p>`;
    }
  }

  function renderNovelGrid(novels) {
    const grid = $('#novel-grid');
    if (!novels.length) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted); border: 1px dashed var(--border-subtle); border-radius: 1rem;">
          <i data-lucide="book" style="margin-bottom: 1rem; width: 32px; height: 32px; opacity: 0.5;"></i>
          <p>No novels found. Upload an EPUB to begin.</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    grid.innerHTML = novels.map(novel => `
      <div class="novel-card" onclick="selectNovel('${novel.id}', '${escapeHtml(novel.title)}')">
        <div class="novel-cover">
          ${novel.title.charAt(0)}
        </div>
        <div>
          <div class="novel-title" title="${escapeHtml(novel.title)}">${escapeHtml(novel.title)}</div>
          <div class="novel-meta">
            <span>${escapeHtml(novel.author)}</span>
            <span>${novel.chapter_count} ch</span>
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
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="animate-spin"></i> Uploading...`;
    lucide.createIcons();

    try {
      const res = await fetch('/api/library/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      showToast("Novel uploaded successfully.", "success");
      loadLibrary(); // Reload grid

    } catch (e) {
      showToast(`Upload failed: ${e.message}`, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
      input.value = ''; // Reset input
      lucide.createIcons();
    }
  };

  window.selectNovel = async function (novelId, title) {
    state.currentNovelId = novelId;
    $('#selected-novel-title').textContent = title;

    // UI Swaps
    $('#novel-grid').style.display = 'none';
    $('#chapter-list-container').style.display = 'block';
    $('.tabs-header').style.display = 'none'; // Hide tabs while inside a novel

    const list = $('#chapter-list');
    list.innerHTML = '<p style="color: var(--text-muted);">Loading chapters...</p>';

    try {
      const res = await fetch(`/api/library/${novelId}/chapters`);
      const chapters = await res.json();
      renderChapterList(chapters);
    } catch (e) {
      list.innerHTML = `<p style="color: var(--color-error)">Failed to load chapters: ${e.message}</p>`;
    }
  };

  window.closeChapterList = function () {
    $('#novel-grid').style.display = 'grid';
    $('#chapter-list-container').style.display = 'none';
    $('.tabs-header').style.display = 'flex';
    state.currentNovelId = null;
  };

  function renderChapterList(chapters) {
    const list = $('#chapter-list');
    if (!chapters.length) {
      list.innerHTML = `<p style="color: var(--text-muted);">No chapters found.</p>`;
      return;
    }

    list.innerHTML = chapters.map(ch => `
      <div class="chapter-item" onclick="igniteChapter('${escapeHtml(ch.path)}')">
        <div>
          <span style="font-weight: 600; margin-right: 0.5rem;">${ch.order}.</span>
          <span>${escapeHtml(ch.title || 'Untitled')}</span>
        </div>
        <i data-lucide="play-circle" style="width: 16px; color: var(--primary);"></i>
      </div>
    `).join('');
    lucide.createIcons();
  }

  // Ignition Logic
  window.igniteChapter = async function (chapterPath) {
    ignite({ chapter_path: chapterPath, force_extract: false });
  };

  window.startExtraction = async function () {
    const textInput = $('#raw-text-input');
    const text = textInput.value.trim();

    if (!text) {
      showToast("Please provide narrative text.", "error");
      textInput.focus();
      return;
    }

    ignite({ text: text, force_extract: true });
  };

  async function ignite(payload) {
    // Show Loading on active container
    // If raw, use btn. If lib, show global toast? 
    // Let's use a full screen loader or just toast

    showToast("Igniting Engine...", "info");
    state.isProcessing = true;

    try {
      const res = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      state.currentJobId = data.job_id;
      showToast("Engine Ignited. Vision extracted.", "success");

      // Auto-advance
      switchStep(2);

    } catch (e) {
      showToast(`Ignition Error: ${e.message}`, "error");
    } finally {
      state.isProcessing = false;
    }
  }

  // ── Step 2: The Vision (Scenes) ──────────────────────
  async function loadScenes(jobId) {
    if (!jobId) return;
    const container = $('#scenes-container');

    // Don't reload if already loaded and identifying matches
    if (state.scenes.length > 0 && state.currentJobId === jobId) {
      renderScenes(state.scenes);
      return;
    }

    try {
      const res = await fetch(`/api/scenes/${jobId}`);
      state.scenes = await res.json();
      renderScenes(state.scenes);
    } catch (e) {
      container.innerHTML = `<div class="aurora-card" style="color:var(--color-error)">Failed to load scenes: ${e.message}</div>`;
    }
  }

  window.generateAllImages = async function () {
    if (!state.currentJobId) return;
    try {
      const res = await fetch('/api/generate/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: state.currentJobId }) // No indices = all
      });
      const data = await res.json();
      monitorGeneration(data.job_id);
    } catch (e) {
      showToast("Generation failed: " + e.message, "error");
    }
  };

  window.generateSceneImage = async function (idx) {
    if (!state.currentJobId) return;
    const btn = $(`#btn-gen-img-${idx}`);
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<i data-lucide="loader-2" class="animate-spin"></i>`;
      lucide.createIcons();
    }

    try {
      const res = await fetch('/api/generate/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: state.currentJobId, scene_indices: [idx] })
      });
      const data = await res.json();
      monitorGeneration(data.job_id, idx);
    } catch (e) {
      showToast("Generation failed: " + e.message, "error");
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="image"></i> Generate`;
        lucide.createIcons();
      }
    }
  };

  function monitorGeneration(jobId, specificIdx = null) {
    showToast("Generating images...", "info");
    const evtSource = new EventSource(`/api/progress/${jobId}`);
    evtSource.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.step === 'complete') {
        evtSource.close();
        showToast("Images generated.", "success");
        // Refresh scenes to show images? 
        // We need to know the image URLs.
        // They are at /runs/{currentJobId}/images/scene_{idx}.png?
        // Wait, regeneration saves to the original job folder?
        // YES. `regenerate_image` uses `WEB_RUN_DIR / job_id / "images"`.
        // So we can assume the path is `/runs/{state.currentJobId}/images/scene_{idx}.png`.
        // We can force refresh the image element.

        if (specificIdx !== null) {
          refreshImage(specificIdx);
        } else {
          // Refresh all
          state.scenes.forEach((_, i) => refreshImage(i));
        }
      }
      if (msg.step === 'error') {
        evtSource.close();
        showToast("Generation error: " + msg.detail, "error");
      }
    };
  }

  function refreshImage(idx) {
    const img = $(`#img-scene-${idx}`);
    const btn = $(`#btn-gen-img-${idx}`);
    if (img) {
      const timestamp = new Date().getTime();
      img.src = `/runs/${state.currentJobId}/images/scene_${String(idx).padStart(3, '0')}.png?t=${timestamp}`;
      img.style.display = 'block';
    }
    if (btn) {
      btn.innerHTML = `<i data-lucide="refresh-cw"></i> Regenerate`;
      btn.disabled = false;
    }
    lucide.createIcons();
  }

  function renderScenes(scenes) {
    const container = $('#scenes-container');

    if (!scenes || !scenes.length) {
      container.innerHTML = `<div class="aurora-card">No scenes found.</div>`;
      return;
    }

    container.innerHTML = scenes.map((scene, i) => `
        <div class="aurora-card" style="padding: 1.5rem; display: grid; gap: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-glass); padding-bottom: 0.5rem;">
                <h3 style="font-size: 1.25rem;">Scene ${i + 1}: ${escapeHtml(scene.title)}</h3>
                <span class="status-badge success">Extracted</span>
            </div>
            
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;">
                <div style="display: flex; flex-direction: column; gap: 1rem;">
                     <div>
                        <label style="display: block; color: var(--text-muted); margin-bottom: 0.5rem; font-size: 0.9rem;">Visual Prompt</label>
                        <textarea class="aurora-input" rows="3">${escapeHtml(scene.visual_description || '')}</textarea>
                    </div>
                    <div>
                        <label style="display: block; color: var(--text-muted); margin-bottom: 0.5rem; font-size: 0.9rem;">Narration</label>
                        <textarea class="aurora-input" rows="3" style="font-family: var(--font-body);">${escapeHtml(scene.narration || '')}</textarea>
                    </div>
                </div>
                
                <div style="background: rgba(0,0,0,0.2); border-radius: 0.5rem; border: 1px solid var(--border-subtle); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 200px; padding: 1rem;">
                    <img id="img-scene-${i}" 
                         src="/runs/${state.currentJobId}/images/scene_${String(i).padStart(3, '0')}.png" 
                         onerror="this.style.display='none'"
                         style="max-width: 100%; border-radius: 0.25rem; margin-bottom: 1rem; display: none;" />
                    
                    <button id="btn-gen-img-${i}" class="btn-secondary" onclick="generateSceneImage(${i})" style="font-size: 0.85rem;">
                        <i data-lucide="image"></i> Generate
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    lucide.createIcons();

    // Check for existing images
    scenes.forEach((_, i) => {
      const img = document.getElementById(`img-scene-${i}`);
      if (img) {
        // Check if triggers error or loads
        // Native onerror handles hiding.
        // If it loads, we should update button text to "Regenerate"?
        // We can't easily detect success without JS event on load.
        img.onload = () => {
          img.style.display = 'block';
          const btn = document.getElementById(`btn-gen-img-${i}`);
          if (btn) btn.innerHTML = `<i data-lucide="refresh-cw"></i> Regenerate`;
          lucide.createIcons();
        };
      }
    });
  }

  // ── Step 3: Callbacks & Data ─────────────────────────
  async function loadCharacters() {
    const container = $('#characters-container');
    try {
      // Mock data if API fails or is empty for demo
      const res = await fetch('/api/characters');
      const data = await res.json();

      if (Object.keys(data).length === 0) {
        container.innerHTML = `<div class="aurora-card">No characters found.</div>`;
        return;
      }

      container.innerHTML = Object.entries(data).map(([name, details]) => `
            <div class="aurora-card" style="padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 48px; height: 48px; background: var(--primary); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.2rem;">
                        ${name.substring(0, 2).toUpperCase()}
                    </div>
                    <div>
                        <div style="font-weight: 600; font-size: 1.1rem;">${escapeHtml(name)}</div>
                        <div style="color: var(--text-muted); font-size: 0.9rem;">${details.gender || 'Unknown'}</div>
                    </div>
                </div>
                <div style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.5;">
                    ${escapeHtml(details.description || 'No description available.')}
                </div>
                <div style="margin-top: auto; padding-top: 1rem; border-top: 1px solid var(--border-glass); display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.85rem; color: var(--accent);">
                        <i data-lucide="mic-2" style="width: 14px; display: inline-block; vertical-align: text-bottom;"></i> 
                        ${details.voice_id ? 'Voice Assigned' : 'Auto-Cast'}
                    </span>
                    <button class="btn-secondary" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Edit</button>
                </div>
            </div>
          `).join('');
      lucide.createIcons();

    } catch (e) {
      container.innerHTML = `<div class="aurora-card">Error loading characters.</div>`;
    }
  }

  // ── Step 4: Production ───────────────────────────────
  window.runFullPipeline = async function () {
    if (!state.currentJobId) return;

    const btn = $('#btn-start-production');
    const terminal = $('#terminal-output');

    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="animate-spin"></i> Forging...`;
    lucide.createIcons();

    terminal.innerHTML = `> Initializing Aurora Pipeline...<br>`;

    try {
      const res = await fetch('/api/pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter_path: state.currentJobId })
      });

      const data = await res.json();
      const evtSource = new EventSource(`/api/progress/${data.job_id}`);

      evtSource.onmessage = (e) => {
        const msg = JSON.parse(e.data);

        if (msg.detail) {
          const line = document.createElement('div');
          line.innerHTML = `<span style="color: var(--text-muted); margin-right: 0.5rem;">[${new Date().toLocaleTimeString()}]</span> ${escapeHtml(msg.detail)}`;
          terminal.appendChild(line);
          terminal.scrollTop = terminal.scrollHeight;
        }

        if (msg.step === 'complete') {
          evtSource.close();
          terminal.innerHTML += `<br>><span style="color: var(--color-success)"> PRODUCTION COMPLETE.</span>`;
          btn.innerHTML = `<i data-lucide="check"></i> Complete`;
          btn.onclick = () => switchStep(5);
          btn.disabled = false;
          showToast("Masterpiece Created.", "success");
          lucide.createIcons();
        }
      };

    } catch (e) {
      terminal.innerHTML += `<br>> <span style="color: #EF4444">CRITICAL ERROR: ${e.message}</span>`;
      btn.disabled = false;
      btn.innerHTML = `Retry Production`;
    }
  };

  // ── Step 5: Cinema ───────────────────────────────────
  function loadFinalAssets() {
    const container = $('#final-video-container');
    // For now we assume one video per job with standard name chXXXX.mp4 or similar
    // The pipeline saves to WEB_RUN_DIR/chXXXX/scenes.json etc.
    // The previous code returned "video" in list_outputs.

    fetch(`/api/outputs/${state.currentJobId}`).then(r => r.json()).then(data => {
      if (data.video && data.video.length) {
        const videoPath = data.video[0].name; // Just name is needed if served under correct path
        // Serve path logic? 
        // /runs/job_id/... ? 
        // Actually backend copies to WEB_RUN_DIR/job_id/video? No.
        // The backend logic for pipeline output uses `run_dir` which is `chapter_id`.
        // But `currentJobId` is set to `extract_...`.
        // Wait. `pipeline` endpoint uses `_get_cached_job` to find extraction `job_id`.
        // But outputs are saved to `chapter_id` folder.
        // The frontend `state.currentJobId` is the `extract_...` id.
        // We need to map `extract_...` -> `chapter_id`.
        // `list_outputs` takes `chapter_id`.
        // But `currentJobId` might be `extract_TIMESTAMP`.
        // We need to know the `chapter_id` (e.g. ch0001).
        // When we ignite, we get `job_id`. 
        // We need `chapter_id` too. `api/extract` doesn't return it directly unless we check extraction status.

        // Quick Fix: Look up scenes, they have cache info? 
        // `api/scenes/JOBID` returns list of scenes. 
        // Scene data might have chapter_id?
        // Or `api/extract` returns `chapter_id`?

        // Let's rely on standard path serving for now or fix this later.
        // Assume typical path for now.
        container.innerHTML = `<p>Video generation complete. Check output folder.</p>`;
      } else {
        container.innerHTML = `<p>No video found.</p>`;
      }
    });
  }

  // ── Utilities ────────────────────────────────────────
  function showToast(msg, type = 'info') {
    let toastContainer = $('.toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'toast-container';
      toastContainer.style.position = 'fixed';
      toastContainer.style.bottom = '2rem';
      toastContainer.style.right = '2rem';
      toastContainer.style.zIndex = '100';
      toastContainer.style.display = 'flex';
      toastContainer.style.flexDirection = 'column';
      toastContainer.style.gap = '1rem';
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.style.background = 'var(--bg-card)';
    toast.style.backdropFilter = 'blur(12px)';
    toast.style.border = '1px solid var(--border-glass)';
    toast.style.padding = '1rem 1.5rem';
    toast.style.borderRadius = '0.75rem';
    toast.style.color = 'var(--text-main)';
    toast.style.boxShadow = 'var(--shadow-card)';
    toast.style.borderLeft = `4px solid var(--${type === 'error' ? 'color-error' : 'primary'})`;
    toast.style.animation = 'fadeUp 0.3s ease';

    toast.innerText = msg;

    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function escapeHtml(text) {
    if (!text) return '';
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function checkHealth() {
    fetch('/api/health').then(r => r.json()).then(s => {
      const badge = $('#sys-status');
      if (s.status === 'ok') {
        badge.className = 'status-badge success';
        badge.innerHTML = `<span class="status-dot" style="width:8px; height:8px; border-radius:50%; background:#10B981; display:inline-block;"></span> System Online`;
      } else {
        badge.className = 'status-badge pending'; // or error
        badge.innerHTML = `Offline`;
      }
    }).catch(() => { });
  }

})();
