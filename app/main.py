import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.core.logging import logger, correlation_id_ctx
from app.api.errors.handlers import register_error_handlers
from app.api.routes import system, jobs
from app.workers.task_runner import worker_loop


worker_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize background worker tasks
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    for i in range(settings.MAX_CONCURRENT_JOBS):
        task = asyncio.create_task(worker_loop())
        worker_tasks.append(task)
    yield
    # Shutdown: Cleanly cancel worker tasks
    logger.info("Shutting down background workers...")
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production Script & Voiceover to B-roll Video Engine for IncuBrix Assessment 3",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    token = correlation_id_ctx.set(corr_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = corr_id
        return response
    finally:
        correlation_id_ctx.reset(token)


# Register standardized IncuBrix error handlers
register_error_handlers(app)

# Include routes
app.include_router(system.router)
app.include_router(jobs.router, prefix=settings.API_V1_PREFIX)

# Also mount explicitly at /api/v1/broll/jobs per IncuBrix brief
app.add_api_route(
    f"{settings.API_V1_PREFIX}/broll/jobs",
    jobs.create_broll_job,
    methods=["POST"],
    tags=["B-Roll Jobs"],
    summary="Submit B-roll video job (Brief route)"
)


@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
def get_web_dashboard():
    """
    Intuitive, responsive web interface for evaluating the engine, submitting jobs,
    previewing videos, inspecting timelines, and testing clip replacement.
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>IncuBrix - Script & Voiceover to B-Roll Video Engine</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
  <header class="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="h-9 w-9 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">IB</div>
        <div>
          <h1 class="text-lg font-bold text-white">IncuBrix Video Engine</h1>
          <p class="text-xs text-slate-400">Assessment 3: Script to B-Roll System</p>
        </div>
      </div>
      <div class="flex items-center space-x-4 text-xs font-mono">
        <a href="/docs" class="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">OpenAPI Docs</a>
        <a href="/health" class="px-3 py-1.5 rounded-md bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">System Healthy</a>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8">
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      
      <!-- Input Control Form -->
      <div class="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h2 class="text-base font-semibold text-white mb-4 flex items-center space-x-2">
          <span>Submit Generation Job</span>
        </h2>

        <div class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1.5">Input Mode</label>
            <div class="grid grid-cols-3 gap-2">
              <button type="button" onclick="setMode('script')" id="btn-script" class="px-3 py-2 rounded-lg bg-indigo-600 text-xs font-medium text-white transition">Script Text</button>
              <button type="button" onclick="setMode('scenes')" id="btn-scenes" class="px-3 py-2 rounded-lg bg-slate-800 text-xs font-medium text-slate-300 transition">Scene List</button>
              <button type="button" onclick="setMode('audio')" id="btn-audio" class="px-3 py-2 rounded-lg bg-slate-800 text-xs font-medium text-slate-300 transition">Audio URL</button>
            </div>
          </div>

          <!-- Script Input -->
          <div id="section-script">
            <label class="block text-xs font-medium text-slate-300 mb-1.5">Narration Script</label>
            <textarea id="input-script" rows="4" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" placeholder="Enter narration script... e.g. Trust is earned slowly. Sales grew 40% in 2025. Modern cloud computing revolutionizes enterprise tech.">Trust is earned slowly. Sales grew 40% in 2025. Modern cloud computing revolutionizes enterprise tech.</textarea>
          </div>

          <!-- Scenes Input -->
          <div id="section-scenes" class="hidden">
            <label class="block text-xs font-medium text-slate-300 mb-1.5">Scene List JSON</label>
            <textarea id="input-scenes" rows="4" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-indigo-500">[
  {"text": "Trust is built carefully over many years.", "visual_hint": "reliable partnership handshake"},
  {"text": "Python programming powers machine learning models.", "visual_hint": "software developer coding on computer"}
]</textarea>
          </div>

          <!-- Audio URL Input -->
          <div id="section-audio" class="hidden">
            <label class="block text-xs font-medium text-slate-300 mb-1.5">Audio URL</label>
            <input type="url" id="input-audio-url" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" placeholder="https://example.com/voiceover.mp3" />
          </div>

          <!-- Options -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1.5">Voice</label>
              <select id="input-voice" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200">
                <option value="en-IN-female">en-IN-female (Neerja)</option>
                <option value="en-IN-male">en-IN-male (Prabhat)</option>
                <option value="hi-IN-female">hi-IN-female (Swara - Hindi)</option>
                <option value="ta-IN-female">ta-IN-female (Pallavi - Tamil)</option>
                <option value="en-US-male">en-US-male (Guy)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1.5">Aspect Ratios</label>
              <div class="flex items-center space-x-3 pt-2 text-xs">
                <label class="flex items-center space-x-1.5"><input type="checkbox" id="ratio-16-9" checked class="rounded bg-slate-950 border-slate-700 text-indigo-600"> <span>16:9</span></label>
                <label class="flex items-center space-x-1.5"><input type="checkbox" id="ratio-9-16" checked class="rounded bg-slate-950 border-slate-700 text-indigo-600"> <span>9:16</span></label>
                <label class="flex items-center space-x-1.5"><input type="checkbox" id="ratio-1-1" class="rounded bg-slate-950 border-slate-700 text-indigo-600"> <span>1:1</span></label>
              </div>
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1.5">Content Avoidance List</label>
            <input type="text" id="input-avoid" value="people's faces, alcohol" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200" placeholder="Comma separated: people's faces, violence, etc." />
          </div>

          <div class="flex items-center space-x-4 pt-1 text-xs">
            <label class="flex items-center space-x-1.5"><input type="checkbox" id="burn-in" checked class="rounded bg-slate-950 text-indigo-600"> <span>Burn-in Captions</span></label>
            <label class="flex items-center space-x-1.5"><input type="checkbox" id="export-srt" checked class="rounded bg-slate-950 text-indigo-600"> <span>Export captions.srt</span></label>
          </div>

          <button id="btn-submit" onclick="submitJob()" class="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-semibold text-sm text-white shadow-lg shadow-indigo-600/30 transition">
            Generate B-Roll Video
          </button>
        </div>
      </div>

      <!-- Live Job Monitor and Outputs -->
      <div class="lg:col-span-7 space-y-6">
        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-base font-semibold text-white">Execution Status</h2>
            <div id="job-badge" class="px-2.5 py-1 rounded-full text-xs font-mono bg-slate-800 text-slate-400">Idle</div>
          </div>

          <!-- Progress bar -->
          <div class="w-full bg-slate-950 h-3 rounded-full overflow-hidden mb-3 border border-slate-800">
            <div id="progress-bar" class="bg-indigo-600 h-full w-0 transition-all duration-300"></div>
          </div>
          <div class="flex justify-between text-xs text-slate-400 font-mono mb-4">
            <span id="job-stage">No active job</span>
            <span id="job-progress">0%</span>
          </div>

          <!-- Video Player Box -->
          <div id="player-container" class="hidden bg-black rounded-xl overflow-hidden border border-slate-800 aspect-video mb-4 relative flex items-center justify-center">
            <video id="video-player" controls class="max-h-full max-w-full"></video>
          </div>

          <!-- Results Downloads -->
          <div id="results-links" class="hidden space-y-3 pt-2">
            <h3 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Output Assets</h3>
            <div id="links-container" class="grid grid-cols-2 gap-2 text-xs"></div>
          </div>

          <!-- Timeline & Manifest Inspector -->
          <div id="artifacts-box" class="hidden mt-4 pt-4 border-t border-slate-800">
            <div class="flex space-x-4 border-b border-slate-800 mb-3">
              <button onclick="showTab('timeline')" id="tab-timeline" class="pb-2 text-xs font-medium text-indigo-400 border-b-2 border-indigo-400">Scene Timeline</button>
              <button onclick="showTab('manifest')" id="tab-manifest" class="pb-2 text-xs font-medium text-slate-400">Manifest</button>
            </div>
            <pre id="tab-content" class="bg-slate-950 p-4 rounded-lg font-mono text-xs text-slate-300 max-h-72 overflow-y-auto"></pre>
          </div>
        </div>
      </div>

    </div>
  </main>

  <script>
    let currentMode = 'script';
    let pollInterval = null;
    let cachedTimeline = null;
    let cachedManifest = null;

    function setMode(mode) {
      currentMode = mode;
      ['script', 'scenes', 'audio'].forEach(m => {
        document.getElementById(`section-${m}`).classList.toggle('hidden', m !== mode);
        document.getElementById(`btn-${m}`).className = m === mode 
          ? 'px-3 py-2 rounded-lg bg-indigo-600 text-xs font-medium text-white transition'
          : 'px-3 py-2 rounded-lg bg-slate-800 text-xs font-medium text-slate-300 transition';
      });
    }

    async function submitJob() {
      const btn = document.getElementById('btn-submit');
      btn.disabled = true;
      btn.innerText = 'Submitting Job...';

      const ratios = [];
      if (document.getElementById('ratio-16-9').checked) ratios.push('16:9');
      if (document.getElementById('ratio-9-16').checked) ratios.push('9:16');
      if (document.getElementById('ratio-1-1').checked) ratios.push('1:1');

      const avoid = document.getElementById('input-avoid').value.split(',').map(s => s.trim()).filter(Boolean);
      const voice = document.getElementById('input-voice').value;
      const burn_in = document.getElementById('burn-in').checked;
      const srt = document.getElementById('export-srt').checked;

      const payload = {
        aspect_ratios: ratios,
        voice: voice,
        avoid: avoid,
        captions: { burn_in, srt },
        audio_url: null,
        script: null,
        scenes: null,
      };

      if (currentMode === 'script') {
        payload.script = document.getElementById('input-script').value;
      } else if (currentMode === 'scenes') {
        try {
          payload.scenes = JSON.parse(document.getElementById('input-scenes').value);
        } catch (e) {
          alert('Invalid JSON in scene list: ' + e.message);
          btn.disabled = false;
          btn.innerText = 'Generate B-Roll Video';
          return;
        }
      } else if (currentMode === 'audio') {
        payload.audio_url = document.getElementById('input-audio-url').value;
      }

      try {
        const resp = await fetch('/api/v1/broll/jobs', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': 'web-ui-' + Date.now()
          },
          body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (resp.status !== 202) {
          alert('Error: ' + (data.error ? data.error.message : JSON.stringify(data)));
          btn.disabled = false;
          btn.innerText = 'Generate B-Roll Video';
          return;
        }

        startPolling(data.job_id);
      } catch (err) {
        alert('Request failed: ' + err.message);
        btn.disabled = false;
        btn.innerText = 'Generate B-Roll Video';
      }
    }

    function startPolling(jobId) {
      if (pollInterval) clearInterval(pollInterval);
      pollInterval = setInterval(async () => {
        const res = await fetch(`/api/v1/jobs/${jobId}`);
        const job = await res.json();

        document.getElementById('progress-bar').style.width = job.progress + '%';
        document.getElementById('job-progress').innerText = job.progress + '%';
        document.getElementById('job-stage').innerText = job.stage;

        const badge = document.getElementById('job-badge');
        badge.innerText = job.status.toUpperCase();
        if (job.status === 'running') badge.className = 'px-2.5 py-1 rounded-full text-xs font-mono bg-indigo-950 text-indigo-400 border border-indigo-800';
        if (job.status === 'succeeded') badge.className = 'px-2.5 py-1 rounded-full text-xs font-mono bg-emerald-950 text-emerald-400 border border-emerald-800';
        if (job.status === 'failed') badge.className = 'px-2.5 py-1 rounded-full text-xs font-mono bg-rose-950 text-rose-400 border border-rose-800';

        if (job.status === 'succeeded') {
          clearInterval(pollInterval);
          document.getElementById('btn-submit').disabled = false;
          document.getElementById('btn-submit').innerText = 'Generate B-Roll Video';
          renderOutputs(job.result);
        } else if (job.status === 'failed') {
          clearInterval(pollInterval);
          document.getElementById('btn-submit').disabled = false;
          document.getElementById('btn-submit').innerText = 'Generate B-Roll Video';
          alert('Job Failed: ' + (job.error ? job.error.message : 'Unknown error'));
        }
      }, 1500);
    }

    async function renderOutputs(result) {
      if (!result) return;
      const linksContainer = document.getElementById('links-container');
      linksContainer.innerHTML = '';

      if (result.videos) {
        Object.keys(result.videos).forEach(ratio => {
          const url = result.videos[ratio];
          linksContainer.innerHTML += `<a href="${url}" target="_blank" class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500 flex items-center justify-between text-slate-200"><span>Video (${ratio})</span><span class="text-indigo-400">Download &rarr;</span></a>`;
        });

        // Set primary video to video player
        const primary = result.videos['16:9'] || Object.values(result.videos)[0];
        if (primary) {
          const vp = document.getElementById('video-player');
          vp.src = primary;
          vp.load();
          document.getElementById('player-container').classList.remove('hidden');
        }
      }

      if (result.captions) {
        linksContainer.innerHTML += `<a href="${result.captions}" target="_blank" class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500 flex items-center justify-between text-slate-200"><span>captions.srt</span><span class="text-indigo-400">Download &rarr;</span></a>`;
      }
      if (result.timeline) {
        linksContainer.innerHTML += `<a href="${result.timeline}" target="_blank" class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500 flex items-center justify-between text-slate-200"><span>timeline.json</span><span class="text-indigo-400">Download &rarr;</span></a>`;
        const tResp = await fetch(result.timeline);
        cachedTimeline = await tResp.json();
      }
      if (result.manifest) {
        linksContainer.innerHTML += `<a href="${result.manifest}" target="_blank" class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500 flex items-center justify-between text-slate-200"><span>manifest.json</span><span class="text-indigo-400">Download &rarr;</span></a>`;
        const mResp = await fetch(result.manifest);
        cachedManifest = await mResp.json();
      }

      document.getElementById('results-links').classList.remove('hidden');
      document.getElementById('artifacts-box').classList.remove('hidden');
      showTab('timeline');
    }

    function showTab(tab) {
      if (tab === 'timeline') {
        document.getElementById('tab-content').innerText = JSON.stringify(cachedTimeline, null, 2);
        document.getElementById('tab-timeline').className = 'pb-2 text-xs font-medium text-indigo-400 border-b-2 border-indigo-400';
        document.getElementById('tab-manifest').className = 'pb-2 text-xs font-medium text-slate-400';
      } else {
        document.getElementById('tab-content').innerText = JSON.stringify(cachedManifest, null, 2);
        document.getElementById('tab-manifest').className = 'pb-2 text-xs font-medium text-indigo-400 border-b-2 border-indigo-400';
        document.getElementById('tab-timeline').className = 'pb-2 text-xs font-medium text-slate-400';
      }
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
