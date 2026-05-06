/* ===================================================
   BRAINROT.AI — Dashboard JS
   =================================================== */

// ---- Navigation ----
const sections = ['generate','queue','analytics','videos','logs'];
const titles = {
  generate:  'Generate Video',
  queue:     'Upload Queue',
  analytics: 'Analytics',
  videos:    'Recent Videos',
  logs:      'Render Logs',
};

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    const sec = item.dataset.section;
    switchSection(sec);
  });
});

function switchSection(sec) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));

  const navEl = document.querySelector(`.nav-item[data-section="${sec}"]`);
  const secEl = document.getElementById(`section-${sec}`);
  if (navEl) navEl.classList.add('active');
  if (secEl) secEl.classList.add('active');

  document.getElementById('page-title').textContent = titles[sec] || sec;

  if (sec === 'queue')     loadQueue();
  if (sec === 'analytics') loadAnalytics();
  if (sec === 'videos')    loadVideos();
  if (sec === 'logs')      loadLogs();
}

// ---- Voice selector ----
document.querySelectorAll('.voice-opt').forEach(opt => {
  opt.addEventListener('click', () => {
    document.querySelectorAll('.voice-opt').forEach(o => o.classList.remove('active'));
    opt.classList.add('active');
    opt.querySelector('input').checked = true;
  });
});

// ---- State ----
let currentScript = null;

// ---- Script Generation ----
async function generateScript() {
  const topic = document.getElementById('topic-input').value.trim();
  if (!topic) { toast('Enter a topic first', 'error'); return; }

  const btn = document.getElementById('generate-btn');
  setLoading(btn, true);
  setStep('script', 'running', 'Generating...');
  log('info', `$ Generating script for: "${topic}"`);

  try {
    const res = await fetch('/api/generate-script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic })
    });
    const data = await res.json();

    if (!data.success) throw new Error(data.error || 'Generation failed');

    currentScript = data;
    renderScriptOutput(data);
    setStep('script', 'done', 'Complete');
    log('success', `✓ Script ready: "${data.title}"`);
    log('info', `  Hook: ${data.hook}`);
    toast('Script generated!', 'success');

    document.getElementById('voice-btn').classList.remove('hidden');
  } catch (err) {
    setStep('script', 'error', 'Failed');
    log('error', `✗ Error: ${err.message}`);
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderScriptOutput(data) {
  document.getElementById('out-hook').textContent    = data.hook;
  document.getElementById('out-title').textContent   = data.title;
  document.getElementById('out-script').value        = data.script;
  const htRow = document.getElementById('out-hashtags');
  htRow.innerHTML = (data.hashtags || [])
    .map(h => `<span class="hashtag">${h}</span>`).join('');
  document.getElementById('script-output').classList.remove('hidden');
}

// ---- Voice Generation ----
async function generateVoice() {
  if (!currentScript) { toast('Generate script first', 'error'); return; }

  const voiceInput = document.querySelector('input[name="voice"]:checked');
  const voice = voiceInput ? voiceInput.value : 'guy';
  const script = document.getElementById('out-script').value.trim();
  const filename = `voice_${Date.now()}`;

  const btn = document.getElementById('voice-btn');
  setLoading(btn, true);
  setStep('voice', 'running', 'Synthesizing...');
  log('info', `$ Generating voice [${voice}]...`);

  try {
    const res = await fetch('/api/generate-voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: script, filename, voice_key: voice })
    });
    const data = await res.json();

    if (!data.success) throw new Error(data.error || 'Voice generation failed');

    window._lastAudioPath = data.path;
    setStep('voice', 'done', `${data.filename}`);
    log('success', `✓ Voice saved: ${data.filename} (${(data.size_bytes/1024).toFixed(1)}KB)`);
    log('warn', `  ⚡ Add gameplay clips to assets/gameplay/ then hit Render`);
    toast('Voice generated!', 'success');

    setStep('gameplay', 'pending', 'Ready');
    setStep('captions', 'pending', 'Waiting...');
    setStep('render',   'pending', 'Waiting...');

    document.getElementById('render-btn').classList.remove('hidden');
  } catch (err) {
    setStep('voice', 'error', 'Failed');
    log('error', `✗ ${err.message}`);
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

// ---- Render ----
async function startRender() {
  if (!currentScript || !window._lastAudioPath) {
    toast('Complete Script + Voice first', 'error'); return;
  }

  const btn = document.getElementById('render-btn');
  setLoading(btn, true);
  setStep('gameplay', 'running', 'Selecting clip...');
  setStep('captions', 'running', 'Transcribing...');
  setStep('render',   'running', 'Rendering...');
  log('info', '$ Starting render pipeline...');

  try {
    const res = await fetch('/api/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title:      currentScript.title,
        script:     currentScript.script,
        audio_path: window._lastAudioPath
      })
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Render failed to start');

    window._renderVideoId = data.video_id;
    log('success', `✓ Pipeline started (video #${data.video_id})`);
    toast('Rendering in background...', 'success');
    pollRenderStatus(data.video_id);
  } catch (err) {
    setStep('render', 'error', 'Failed');
    log('error', `✗ ${err.message}`);
    toast(err.message, 'error');
    setLoading(btn, false);
  }
}

function pollRenderStatus(videoId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch('/api/videos');
      const videos = await res.json();
      const v = videos.find(x => x.id === videoId);
      if (!v) return;

      if (v.status === 'pending') {
        clearInterval(interval);
        setStep('gameplay',  'done', 'Complete');
        setStep('captions', 'done', 'Complete');
        setStep('render',   'done', 'Complete');
        log('success', `✓ Render done! Video #${videoId} is ready.`);
        toast('Video rendered! Check Upload Queue.', 'success');
        document.getElementById('render-btn').disabled = false;
        document.getElementById('render-btn').classList.remove('loading');
        loadQueue();
      } else if (v.status === 'error') {
        clearInterval(interval);
        setStep('render', 'error', 'Failed');
        log('error', '✗ Render failed. Check Render Logs tab.');
        toast('Render failed', 'error');
        document.getElementById('render-btn').disabled = false;
        document.getElementById('render-btn').classList.remove('loading');
      }
    } catch (e) { /* keep polling */ }
  }, 3000);
}

// ---- Queue ----
async function loadQueue() {
  try {
    const res = await fetch('/api/queue');
    const items = await res.json();

    const badge = document.getElementById('queue-count');
    const sizeEl = document.getElementById('queue-size');
    if (items.length > 0) {
      badge.textContent = items.length;
      badge.classList.add('show');
    } else {
      badge.classList.remove('show');
    }
    if (sizeEl) sizeEl.textContent = items.length;

    const tbody = document.getElementById('queue-body');
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-row">No items in queue</td></tr>';
      return;
    }
    tbody.innerHTML = items.map((item, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${item.video_id || '—'}</td>
        <td><span class="status-badge ${item.status}">${item.status}</span></td>
        <td>${item.added_at || '—'}</td>
        <td><button class="btn-sm" onclick="uploadVideo(${item.id})">Upload</button></td>
      </tr>
    `).join('');
  } catch (e) {
    console.error(e);
  }
}

// ---- Analytics ----
async function loadAnalytics() {
  try {
    const res = await fetch('/api/videos');
    const videos = await res.json();

    document.getElementById('total-videos').textContent   = videos.length;
    document.getElementById('uploaded-count').textContent = videos.filter(v => v.status === 'uploaded').length;
    document.getElementById('pending-count').textContent  = videos.filter(v => v.status === 'pending').length;

    const today = new Date().toDateString();
    document.getElementById('today-count').textContent =
      videos.filter(v => new Date(v.created_at).toDateString() === today).length;

    const timeline = document.getElementById('timeline');
    if (!videos.length) {
      timeline.innerHTML = '<span class="muted">No activity yet.</span>';
      return;
    }
    timeline.innerHTML = videos.slice(0, 10).map(v => `
      <div class="timeline-item">
        <div class="timeline-dot" style="background:${statusColor(v.status)}"></div>
        <span class="timeline-time">${timeAgo(v.created_at)}</span>
        <span class="timeline-text">${v.title || 'Untitled'} — <span class="status-badge ${v.status}">${v.status}</span></span>
      </div>
    `).join('');
  } catch (e) { console.error(e); }
}

// ---- Videos ----
async function loadVideos() {
  try {
    const res = await fetch('/api/videos');
    const videos = await res.json();
    const grid = document.getElementById('videos-grid');

    if (!videos.length) {
      grid.innerHTML = '<span class="muted">No videos yet. Generate one above!</span>';
      return;
    }
    grid.innerHTML = videos.map(v => `
      <div class="video-card">
        <div class="video-card-title">${v.title || 'Untitled Video'}</div>
        <div class="video-card-status">
          <span class="status-badge ${v.status}">${v.status}</span>
        </div>
        ${v.youtube_id ? `<a href="https://youtube.com/shorts/${v.youtube_id}" target="_blank" class="btn-sm" style="display:inline-block;margin-top:8px">▶ Watch</a>` : ''}
        <div class="video-card-meta">${formatDate(v.created_at)}</div>
      </div>
    `).join('');
  } catch (e) { console.error(e); }
}

// ---- Logs ----
async function loadLogs() {
  try {
    const res = await fetch('/api/logs');
    const logs = await res.json();
    const el = document.getElementById('logs-list');

    if (!logs.length) {
      el.innerHTML = '<span class="muted">No render logs yet.</span>';
      return;
    }
    el.innerHTML = logs.map(l => `
      <div class="log-entry">
        <div class="log-entry-title">
          ${l.title || 'Unknown'}
          <span class="status-badge ${l.status}" style="margin-left:8px">${l.status}</span>
        </div>
        <div class="log-entry-text">${l.log || 'No log output.'}</div>
      </div>
    `).join('');
  } catch (e) { console.error(e); }
}

// ---- Helpers ----
function setStep(step, state, statusText) {
  const ind = document.getElementById(`si-${step}`);
  const stat = document.getElementById(`ss-${step}`);
  if (ind) { ind.className = `step-indicator ${state}`; }
  if (stat) { stat.textContent = statusText; }
}

function setLoading(btn, loading) {
  if (loading) { btn.classList.add('loading'); btn.disabled = true; }
  else          { btn.classList.remove('loading'); btn.disabled = false; }
}

function log(type, message) {
  const body = document.getElementById('log-body');
  const line = document.createElement('span');
  line.className = `log-line ${type}`;
  line.textContent = message;
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

function toast(msg, type = 'success') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 4200);
}

function statusColor(s) {
  return { pending:'#ffd60a', uploaded:'#00ffc8', error:'#f72585', rendering:'#00d4ff' }[s] || '#aaa';
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h/24)}d ago`;
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}

// ---- Init ----
(async function init() {
  // Auto-sync existing videos on load
  try {
      await fetch('/api/sync', { method: 'POST' });
  } catch(e) {}
  
  await loadQueue();
  await loadAnalytics();
})();
