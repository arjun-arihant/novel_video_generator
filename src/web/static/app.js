/* ═══════════════════════════════════════════════════════
   Novel Video Generator — App Controller
   ═══════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── State ────────────────────────────────────────────
  const state = {
    selectedChapter: null,
    currentJobId: null,
    scenes: [],
    characters: {},
    locations: {},
  };

  // ── DOM References ───────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ── Toast System ─────────────────────────────────────
  function showToast(message, type = 'info', duration = 4000) {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="toast-message">${message}</span>
      <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      toast.style.transition = 'all 300ms ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // ── Tab Navigation ───────────────────────────────────
  function initTabs() {
    $$('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        $$('.tab-btn').forEach((b) => b.classList.remove('active'));
        $$('.tab-panel').forEach((p) => p.classList.remove('active'));
        btn.classList.add('active');
        $(`#panel-${btn.dataset.tab}`).classList.add('active');

        // Load data when switching tabs
        if (btn.dataset.tab === 'characters') loadCharacters();
        if (btn.dataset.tab === 'locations') loadLocations();
        if (btn.dataset.tab === 'scenes' && state.currentJobId) loadScenes(state.currentJobId);
      });
    });
  }

  // ── Chapter Loading ──────────────────────────────────
  async function loadChapters() {
    try {
      const res = await fetch('/api/chapters');
      const chapters = await res.json();
      renderChapters(chapters);
    } catch (e) {
      $('#chapter-grid').innerHTML = `
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          <h3>Failed to load chapters</h3>
          <p>${e.message}</p>
        </div>
      `;
    }
  }

  function renderChapters(chapters) {
    const grid = $('#chapter-grid');
    if (!chapters.length) {
      grid.innerHTML = `
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <h3>No chapters found</h3>
          <p>Upload a chapter JSON file to get started</p>
        </div>
      `;
      return;
    }
    grid.innerHTML = chapters.map((ch) => `
      <div class="chapter-card ${ch.extracted ? 'extracted' : ''}" data-path="${ch.path}" data-jobid="${ch.job_id || ''}" onclick="window._selectChapter(this, '${ch.path.replace(/\\/g, '\\\\')}', '${ch.job_id || ''}')">
        <div class="chapter-number">
          Chapter ${ch.chapter_number}
          ${ch.extracted ? '<span style="font-size:var(--text-xs);color:var(--success);margin-left:var(--space-sm)">✓ Extracted</span>' : ''}
        </div>
        <div class="chapter-title">${escapeHtml(ch.title)}</div>
        <div class="chapter-meta">${ch.paragraph_count} paragraphs &middot; ${ch.path.split(/[\\/]/).pop()}</div>
      </div>
    `).join('');
  }

  window._selectChapter = function (el, path, jobId) {
    $$('.chapter-card').forEach((c) => c.classList.remove('selected'));
    el.classList.add('selected');
    state.selectedChapter = path;
    $('#btn-extract').disabled = false;
    $('#btn-pipeline').disabled = false;

    // If chapter has cached scenes, load them immediately
    if (jobId) {
      state.currentJobId = jobId;
      loadScenes(jobId);
    }
  };

  // ── File Upload ──────────────────────────────────────
  function initUpload() {
    const input = $('#file-input');
    input.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.error) {
          showToast(data.error, 'error');
          return;
        }
        showToast(`Uploaded: ${file.name}`, 'success');
        loadChapters();
      } catch (e) {
        showToast(`Upload failed: ${e.message}`, 'error');
      }
    });
  }

  // ── Pipeline Execution ───────────────────────────────
  function setStatus(text, dotClass = '') {
    $('#status-text').textContent = text;
    const dot = $('#status-dot');
    dot.className = 'status-dot';
    if (dotClass) dot.classList.add(dotClass);
  }

  function updatePipelineStep(step, status) {
    // Map step names to step IDs
    const stepMap = {
      loading: 'step-extract',
      extracting: 'step-extract',
      voices: 'step-voices',
      enriching: 'step-voices',
      images: 'step-images',
      images_skip: 'step-images',
      audio: 'step-audio',
      audio_done: 'step-audio',
      audio_skip: 'step-audio',
      video: 'step-video',
      video_skip: 'step-video',
      done: 'step-video',
    };

    const stepOrder = ['step-extract', 'step-voices', 'step-images', 'step-audio', 'step-video'];
    const activeId = stepMap[step];
    if (!activeId) return;

    const activeIdx = stepOrder.indexOf(activeId);
    stepOrder.forEach((id, i) => {
      const el = $(`#${id}`);
      el.classList.remove('active', 'done', 'error');
      if (status === 'error') {
        if (id === activeId) el.classList.add('error');
        return;
      }
      if (i < activeIdx) el.classList.add('done');
      else if (i === activeIdx) el.classList.add('active');
    });
  }

  function appendLog(msg) {
    const log = $('#pipeline-log');
    log.classList.remove('hidden');
    const time = new Date().toLocaleTimeString();
    log.innerHTML += `<div>[${time}] ${escapeHtml(msg)}</div>`;
    log.scrollTop = log.scrollHeight;
  }

  async function startExtraction() {
    if (!state.selectedChapter) return;

    const force = $('#chk-force-extract').checked;
    const container = $('#progress-container');
    container.classList.remove('hidden');
    $('#pipeline-log').innerHTML = '';
    setStatus(force ? 'Extracting (Forced)...' : 'Extracting...', 'busy');
    $('#btn-extract').disabled = true;
    $('#btn-pipeline').disabled = true;

    try {
      const res = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chapter_path: state.selectedChapter,
          force_extract: force
        }),
      });
      const data = await res.json();

      // Handle cached response — scenes already extracted
      if (data.status === 'cached') {
        state.currentJobId = data.job_id;
        setStatus('Ready');
        showToast(data.message || `Scenes already extracted (${data.scenes_count} scenes)`, 'info', 5000);
        appendLog(`Using cached scenes: ${data.job_id} (${data.scenes_count} scenes)`);
        container.classList.add('hidden');
        loadScenes(data.job_id);
        loadCharacters();
        loadLocations();
        loadChapters(); // refresh badges
        $('#btn-extract').disabled = false;
        $('#btn-pipeline').disabled = false;

        setTimeout(() => $('#tab-btn-scenes').click(), 500);
        return;
      }

      state.currentJobId = data.job_id;
      appendLog(`Job started: ${data.job_id}`);
      listenToProgress(data.job_id, false);
    } catch (e) {
      showToast(`Extraction failed: ${e.message}`, 'error');
      setStatus('Error', 'offline');
      $('#btn-extract').disabled = false;
      $('#btn-pipeline').disabled = false;
    }
  }

  async function startFullPipeline() {
    if (!state.selectedChapter) return;

    const container = $('#progress-container');
    container.classList.remove('hidden');
    $('#pipeline-log').innerHTML = '';
    setStatus('Pipeline running...', 'busy');
    $('#btn-extract').disabled = true;
    $('#btn-pipeline').disabled = true;

    try {
      const res = await fetch('/api/pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter_path: state.selectedChapter }),
      });
      const { job_id } = await res.json();
      state.currentJobId = job_id;
      appendLog(`Full pipeline started: ${job_id}`);
      listenToProgress(job_id, true);
    } catch (e) {
      showToast(`Pipeline failed: ${e.message}`, 'error');
      setStatus('Error', 'offline');
      $('#btn-extract').disabled = false;
      $('#btn-pipeline').disabled = false;
    }
  }

  function listenToProgress(jobId, isFullPipeline) {
    const evtSource = new EventSource(`/api/progress/${jobId}`);

    evtSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const { step, percent, detail } = data;

      if (step === 'heartbeat') return;

      if (percent >= 0) {
        $('#progress-bar').style.width = `${percent}%`;
        $('#progress-pct').textContent = `${percent}%`;
      }
      $('#progress-step').textContent = detail || step;
      updatePipelineStep(step, step === 'error' ? 'error' : 'active');

      if (detail) appendLog(detail);

      if (step === 'complete') {
        evtSource.close();
        setStatus('Ready');

        // Build summary toast
        let msg = `Pipeline complete! ${data.scenes_count || ''} scenes processed`;
        if (data.detail) msg += `\n${data.detail}`;
        showToast(msg, 'success', 8000);

        // Show output directory in log
        if (data.output_dir) appendLog(`Output directory: ${data.output_dir}`);
        if (data.detail) appendLog(data.detail);

        $('#btn-extract').disabled = false;
        $('#btn-pipeline').disabled = false;

        // Auto-load results
        loadCharacters();
        loadLocations();
        loadChapters(); // refresh extracted badges
        if (data.job_id) {
          state.currentJobId = data.job_id;
          loadScenes(data.job_id);
        }

        // Switch to scenes tab
        setTimeout(() => {
          $('#tab-btn-scenes').click();
        }, 1000);
      }

      if (step === 'error') {
        evtSource.close();
        setStatus('Error', 'offline');
        showToast(`Pipeline error: ${detail}`, 'error', 8000);
        $('#btn-extract').disabled = false;
        $('#btn-pipeline').disabled = false;
      }
    };

    evtSource.onerror = () => {
      evtSource.close();
      setStatus('Connection lost', 'offline');
    };
  }

  // ── Character Gallery ────────────────────────────────
  async function loadCharacters() {
    try {
      const res = await fetch('/api/characters');
      state.characters = await res.json();
      renderCharacters(state.characters);
    } catch (e) {
      console.error('Failed to load characters:', e);
    }
  }

  function renderCharacters(characters) {
    const grid = $('#character-grid');
    const names = Object.keys(characters);

    if (!names.length) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
          <h3>No characters yet</h3>
          <p>Extract scenes from a chapter to populate the character database</p>
        </div>
      `;
      return;
    }

    const colors = ['#6C5CE7', '#00D9A5', '#FF6B6B', '#FDCB6E', '#74B9FF', '#A29BFE', '#FD79A8', '#55EFC4'];

    grid.innerHTML = names.map((name, i) => {
      const ch = characters[name];
      const initials = name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
      const color = colors[i % colors.length];

      const fields = [
        ['Gender', ch.gender],
        ['Age', ch.age_range],
        ['Build', ch.build],
        ['Hair', [ch.hair_color, ch.hair_style].filter(Boolean).join(', ')],
        ['Eyes', ch.eye_color],
        ['Skin', ch.skin_tone],
        ['Clothing', ch.clothing],
        ['Features', ch.distinguishing_features],
      ].filter(([, v]) => v);

      const voiceInfo = ch.voice_id ?
        `<div class="char-voice-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>
          ${ch.voice_id}${ch.voice_speed && ch.voice_speed !== 1 ? ` @${ch.voice_speed}x` : ''}
        </div>` : '';

      return `
        <div class="character-card">
          <div class="char-header">
            <div class="char-avatar" style="background:${color}">${initials}</div>
            <div>
              <div class="char-name">${escapeHtml(name)}</div>
              <div class="char-role">${escapeHtml(ch.role || ch.disposition || '')}</div>
            </div>
          </div>
          <div class="char-body">
            ${fields.map(([label, val]) => `
              <div class="char-field">
                <span class="char-field-label">${label}</span>
                <span class="char-field-value">${escapeHtml(String(val))}</span>
              </div>
            `).join('')}
            ${voiceInfo ? `<div class="mt-md">${voiceInfo}</div>` : ''}
            ${ch.voice_notes ? `<div class="char-field mt-md"><span class="char-field-label">Voice note</span><span class="char-field-value text-muted" style="font-size:var(--text-xs)">${escapeHtml(ch.voice_notes)}</span></div>` : ''}
          </div>
        </div>
      `;
    }).join('');
  }

  // ── Scene Viewer ─────────────────────────────────────
  async function loadScenes(jobId) {
    try {
      const res = await fetch(`/api/scenes/${jobId}`);
      if (!res.ok) return;
      state.scenes = await res.json();
      renderScenes(state.scenes);
    } catch (e) {
      console.error('Failed to load scenes:', e);
    }
  }

  function renderScenes(scenes) {
    const list = $('#scene-list');

    if (!scenes.length) {
      list.innerHTML = `
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          <h3>No scenes yet</h3>
          <p>Run the extraction pipeline to generate scenes</p>
        </div>
      `;
      return;
    }

    list.innerHTML = scenes.map((scene, i) => {
      const sequence = scene.sequence || [];
      const dialogues = scene.dialogues || [];
      const characters = scene.characters || [];

      // Count dialogues
      const dlgCount = sequence.length
        ? sequence.filter(s => s.type === 'dialogue').length
        : dialogues.length;

      let contentHtml = '';

      if (sequence.length) {
        // Render chronological sequence
        contentHtml = `
          <div class="scene-section">
            <h4>Script</h4>
            <div class="script-container">
              ${sequence.map(item => {
          if (item.type === 'dialogue') {
            return `
                    <div class="dialogue-item">
                      <div class="dialogue-speaker">${escapeHtml(item.speaker || 'Unknown')}</div>
                      <div class="dialogue-line">"${escapeHtml(item.text || '')}"</div>
                    </div>
                  `;
          } else {
            return `<div class="scene-text mb-md">${escapeHtml(item.text || '')}</div>`;
          }
        }).join('')}
            </div>
          </div>
        `;
      } else {
        // Fallback: Legacy separate narration/dialogues
        contentHtml = `
          <div class="scene-section">
            <h4>Narration</h4>
            <div class="scene-text">${escapeHtml(scene.narration || '')}</div>
          </div>
          ${dialogues.length ? `
            <div class="scene-section mt-md">
              <h4>Dialogues</h4>
              <div class="dialogue-list">
                ${dialogues.map((d) => `
                  <div class="dialogue-item">
                    <div class="dialogue-speaker">${escapeHtml(d.speaker || 'Unknown')}</div>
                    <div class="dialogue-line">"${escapeHtml(d.line || '')}"</div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        `;
      }

      return `
        <div class="scene-card">
          <div class="scene-header">
            <span class="scene-number">${scene.id || i + 1}</span>
            <span class="scene-title">${escapeHtml(scene.title || `Scene ${i + 1}`)}</span>
            <div class="scene-meta">
              <span>${scene.time_of_day || ''}</span>
              <span>${scene.mood || ''}</span>
              <span>${dlgCount} dialogue${dlgCount !== 1 ? 's' : ''}</span>
            </div>
          </div>
          <div class="scene-body">
            <div class="scene-section mb-lg">
              <h4>Visual Description</h4>
              <div class="scene-text" style="max-height:120px;font-style:italic;color:var(--text-muted)">${escapeHtml(truncate(scene.visual_description || '', 400))}</div>
              ${characters.length ? `
                <div class="mt-sm scene-tags">${characters.map((c) => `<span class="scene-tag">${escapeHtml(c)}</span>`).join('')}</div>
              ` : ''}
            </div>
            ${contentHtml}
          </div>
        </div>
      `;
    }).join('');
  }

  // ── Location Viewer ──────────────────────────────────
  async function loadLocations() {
    try {
      const res = await fetch('/api/locations');
      state.locations = await res.json();
      renderLocations(state.locations);
    } catch (e) {
      console.error('Failed to load locations:', e);
    }
  }

  function renderLocations(locations) {
    const grid = $('#location-grid');
    const names = Object.keys(locations);

    if (!names.length) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
          <h3>No locations yet</h3>
          <p>Extract scenes to populate the location database</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = names.map((name) => {
      const loc = locations[name];
      const tags = [
        loc.time_of_day,
        loc.weather,
        loc.architecture_style,
      ].filter(Boolean);

      return `
        <div class="location-card">
          <div class="location-name">${escapeHtml(name)}</div>
          <div class="location-desc">${escapeHtml(loc.description || '')}</div>
          ${loc.mood ? `<div style="margin-top:var(--space-sm);font-size:var(--text-xs);color:var(--text-accent)">Mood: ${escapeHtml(loc.mood)}</div>` : ''}
          ${loc.lighting ? `<div style="font-size:var(--text-xs);color:var(--text-muted)">Lighting: ${escapeHtml(loc.lighting)}</div>` : ''}
          ${loc.color_palette ? `<div style="font-size:var(--text-xs);color:var(--text-muted)">Colors: ${escapeHtml(loc.color_palette)}</div>` : ''}
          <div class="location-meta">
            ${tags.map((t) => `<span class="location-tag">${escapeHtml(t)}</span>`).join('')}
          </div>
        </div>
      `;
    }).join('');
  }

  // ── Utilities ────────────────────────────────────────
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function truncate(text, max) {
    if (text.length <= max) return text;
    return text.slice(0, max) + '...';
  }

  // ── Service Health ────────────────────────────────────
  async function checkServiceHealth() {
    try {
      const res = await fetch('/api/health');
      const status = await res.json();

      const services = [
        { key: 'wangp', label: 'WanGP (Images)' },
        { key: 'kokoro', label: 'Kokoro TTS (Audio)' },
        { key: 'ffmpeg', label: 'FFmpeg (Video)' },
      ];

      services.forEach(({ key, label }) => {
        const svc = status[key];
        if (!svc) return;
        if (!svc.available) {
          showToast(`${label}: Offline — ${svc.detail}`, 'warning', 6000);
        }
      });
    } catch (e) {
      console.warn('Health check failed:', e);
    }
  }

  // ── Initialize ───────────────────────────────────────
  function init() {
    initTabs();
    initUpload();
    loadChapters();
    checkServiceHealth();

    $('#btn-extract').addEventListener('click', startExtraction);
    $('#btn-pipeline').addEventListener('click', startFullPipeline);
    $('#btn-refresh-chars').addEventListener('click', loadCharacters);

    // Pre-load character & location data if available
    loadCharacters();
    loadLocations();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
