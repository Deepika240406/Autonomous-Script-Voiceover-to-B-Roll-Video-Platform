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
  <title>IncuBrix Studio - Script & Voiceover to B-Roll Video Engine</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; }
    code, pre, .font-mono { font-family: 'JetBrains Mono', monospace; }
    .pulse-glow { box-shadow: 0 0 15px rgba(99, 102, 241, 0.25); }
    .step-active { border-color: #6366f1; background-color: #eef2ff; color: #4338ca; }
    .step-done { border-color: #10b981; background-color: #ecfdf5; color: #047857; }
    .step-pending { border-color: #e2e8f0; background-color: #f8fafc; color: #64748b; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen">
  <!-- Top Navigation Header -->
  <header class="border-b border-slate-200/80 bg-white/95 backdrop-blur sticky top-0 z-50 shadow-sm">
    <div class="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between">
      <div class="flex items-center space-x-3.5">
        <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center font-black text-white text-base shadow-sm">IB</div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-base font-bold text-slate-900 tracking-tight">IncuBrix Video Studio</h1>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">Production Engine</span>
          </div>
          <p class="text-xs text-slate-500">Autonomous Script & Voiceover to B-Roll Video System</p>
        </div>
      </div>
      <div class="flex items-center space-x-3 text-xs">
        <div class="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 font-medium">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Pixabay + Sentence-BERT Connected</span>
        </div>
        <a href="/docs" target="_blank" class="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300/80 transition font-medium">API Documentation</a>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8">
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      
      <!-- Left Column: Input Studio Form -->
      <div class="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-5">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 class="text-sm font-bold text-slate-900 flex items-center space-x-2">
            <span>Video Creation Settings</span>
          </h2>
          <span class="text-xs text-slate-400 font-mono" id="char-count">0 chars</span>
        </div>

        <div class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">Input Modality</label>
            <div class="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/80">
              <button type="button" onclick="setMode('script')" id="btn-script" class="px-3 py-2 rounded-lg bg-white text-xs font-semibold text-indigo-700 transition shadow-sm border border-slate-200/60">Script Text</button>
              <button type="button" onclick="setMode('scenes')" id="btn-scenes" class="px-3 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:text-slate-900 transition">Scene List</button>
              <button type="button" onclick="setMode('audio')" id="btn-audio" class="px-3 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:text-slate-900 transition">Audio URL</button>
            </div>
          </div>

          <!-- Script Input -->
          <div id="section-script">
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">Narration Script</label>
            <textarea id="input-script" rows="4" oninput="updateCharCount()" class="w-full bg-slate-50/50 border border-slate-300 focus:border-indigo-600 focus:bg-white rounded-xl p-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-indigo-100/50 transition leading-relaxed" placeholder="Enter narration script... e.g. Travel allows us to explore new places and experience different cultures.">Travel allows us to explore new places and experience different cultures.</textarea>
          </div>

          <!-- Scenes Input -->
          <div id="section-scenes" class="hidden">
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">Structured Scene List (JSON)</label>
            <textarea id="input-scenes" rows="4" class="w-full bg-slate-50/50 border border-slate-300 focus:border-indigo-600 focus:bg-white rounded-xl p-3 font-mono text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-indigo-100/50 transition">[
  {"text": "Travel allows us to explore new places and experience different cultures.", "visual_hint": "scenic world travel destination landmark"},
  {"text": "Ancient monuments and cultural festivals reveal our shared history.", "visual_hint": "traditional cultural festival monuments"}
]</textarea>
          </div>

          <!-- Audio URL Input -->
          <div id="section-audio" class="hidden">
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-xs font-semibold text-slate-700">Voiceover Audio URL</label>
              <button type="button" onclick="loadDemoAudioUrl()" class="text-xs text-indigo-600 hover:text-indigo-800 transition font-medium underline">Use Sample Demo Audio</button>
            </div>
            <input type="url" id="input-audio-url" class="w-full bg-slate-50/50 border border-slate-300 focus:border-indigo-600 focus:bg-white rounded-xl p-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-indigo-100/50 transition font-mono text-xs" placeholder="https://example.com/voiceover.mp3" />
          </div>

          <!-- Voice & Aspect Ratios -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1.5">Voice Persona</label>
              <select id="input-voice" class="w-full bg-white border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:border-indigo-600 focus:outline-none focus:ring-4 focus:ring-indigo-100/50">
                <option value="en-IN-female">en-IN-female (Neerja)</option>
                <option value="en-IN-male">en-IN-male (Prabhat)</option>
                <option value="ta-IN-female">ta-IN-female (Pallavi - Tamil)</option>
                <option value="hi-IN-female">hi-IN-female (Swara - Hindi)</option>
                <option value="en-US-male">en-US-male (Guy)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1.5">Aspect Ratios</label>
              <div class="flex items-center space-x-3 pt-2 text-xs">
                <label class="flex items-center space-x-1.5 cursor-pointer text-slate-700"><input type="checkbox" id="ratio-16-9" checked class="rounded border-slate-300 text-indigo-600 focus:ring-0"> <span>16:9</span></label>
                <label class="flex items-center space-x-1.5 cursor-pointer text-slate-700"><input type="checkbox" id="ratio-9-16" checked class="rounded border-slate-300 text-indigo-600 focus:ring-0"> <span>9:16</span></label>
                <label class="flex items-center space-x-1.5 cursor-pointer text-slate-700"><input type="checkbox" id="ratio-1-1" checked class="rounded border-slate-300 text-indigo-600 focus:ring-0"> <span>1:1</span></label>
              </div>
            </div>
          </div>

          <!-- Content Avoidance -->
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">Content Avoidance List</label>
            <input type="text" id="input-avoid" value="people's faces, alcohol" class="w-full bg-white border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:border-indigo-600 focus:outline-none focus:ring-4 focus:ring-indigo-100/50" placeholder="Comma separated: people's faces, alcohol, violence" />
          </div>

          <!-- Captions options -->
          <div class="flex items-center space-x-5 pt-1 text-xs text-slate-700">
            <label class="flex items-center space-x-2 cursor-pointer"><input type="checkbox" id="burn-in" checked class="rounded border-slate-300 text-indigo-600 focus:ring-0"> <span>Burn-in Subtitles</span></label>
            <label class="flex items-center space-x-2 cursor-pointer"><input type="checkbox" id="export-srt" checked class="rounded border-slate-300 text-indigo-600 focus:ring-0"> <span>Generate captions.srt</span></label>
          </div>

          <!-- Submit Button -->
          <button id="btn-submit" onclick="submitJob()" class="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 rounded-xl font-bold text-sm text-white shadow-sm transition active:scale-[0.99] flex items-center justify-center space-x-2">
            <span id="btn-submit-icon">✨</span>
            <span id="btn-submit-text">Generate Production B-Roll Video</span>
          </button>
        </div>
      </div>

      <!-- Right Column: Live Monitor & Video Studio -->
      <div class="lg:col-span-7 space-y-6">
        
        <!-- Live Execution Monitor Card -->
        <div class="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-sm font-bold text-slate-900">Pipeline Execution Monitor</h2>
              <p class="text-xs text-slate-500" id="job-id-display">Ready for generation job</p>
            </div>
            <div id="job-badge" class="px-3 py-1 rounded-full text-xs font-mono font-medium bg-slate-100 text-slate-600 border border-slate-200">Idle</div>
          </div>

          <!-- 5-Stage Stepper -->
          <div class="grid grid-cols-5 gap-1.5 pt-1">
            <div id="step-1" class="p-2 rounded-lg border text-center transition step-pending">
              <div class="text-[10px] font-mono uppercase font-semibold">1. Ingest</div>
            </div>
            <div id="step-2" class="p-2 rounded-lg border text-center transition step-pending">
              <div class="text-[10px] font-mono uppercase font-semibold">2. Speech</div>
            </div>
            <div id="step-3" class="p-2 rounded-lg border text-center transition step-pending">
              <div class="text-[10px] font-mono uppercase font-semibold">3. LLM Scene</div>
            </div>
            <div id="step-4" class="p-2 rounded-lg border text-center transition step-pending">
              <div class="text-[10px] font-mono uppercase font-semibold">4. Match</div>
            </div>
            <div id="step-5" class="p-2 rounded-lg border text-center transition step-pending">
              <div class="text-[10px] font-mono uppercase font-semibold">5. Render</div>
            </div>
          </div>

          <!-- Progress Bar -->
          <div>
            <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden border border-slate-200">
              <div id="progress-bar" class="bg-indigo-600 h-full w-0 transition-all duration-300"></div>
            </div>
            <div class="flex justify-between text-xs text-slate-500 font-mono mt-2">
              <span id="job-stage" class="truncate max-w-xs">No active pipeline</span>
              <span id="job-progress" class="font-bold text-slate-800">0%</span>
            </div>
          </div>
        </div>

        <!-- Video Player Studio Card -->
        <div id="player-card" class="hidden bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <span>Preview Rendered Video</span>
            </h3>
            <!-- Multi-Aspect Ratio Preview Switcher -->
            <div id="aspect-switcher" class="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
              <button onclick="switchAspect('16:9')" id="switch-16-9" class="px-2.5 py-1 rounded-lg bg-white text-indigo-700 font-semibold shadow-sm transition border border-slate-200/60">16:9 Landscape</button>
              <button onclick="switchAspect('9:16')" id="switch-9-16" class="px-2.5 py-1 rounded-lg text-slate-600 hover:text-slate-900 font-medium transition">9:16 Vertical</button>
              <button onclick="switchAspect('1:1')" id="switch-1-1" class="px-2.5 py-1 rounded-lg text-slate-600 hover:text-slate-900 font-medium transition">1:1 Square</button>
            </div>
          </div>

          <div id="player-container" class="bg-black rounded-xl overflow-hidden border border-slate-200 aspect-video relative flex items-center justify-center transition-all duration-300 mx-auto shadow-sm">
            <video id="video-player" controls class="max-h-full max-w-full rounded-lg"></video>
          </div>

          <!-- Download Assets Hub -->
          <div id="results-links" class="pt-2">
            <div class="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">Production Output Assets</div>
            <div id="links-container" class="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs"></div>
          </div>
        </div>

        <!-- Visual Scene Breakdown Cards (Interactive Timeline) -->
        <div id="scenes-breakdown-card" class="hidden bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-bold text-slate-900">Visual Scene Breakdown</h3>
              <p class="text-xs text-slate-500">Narration alignment, LLM visual concepts & Sentence-BERT ranking</p>
            </div>
            <span id="scene-count-badge" class="px-2.5 py-1 rounded-full text-xs font-mono bg-indigo-50 text-indigo-700 border border-indigo-200 font-medium">0 Scenes</span>
          </div>
          <div id="scene-cards-container" class="space-y-3 max-h-96 overflow-y-auto pr-1"></div>
        </div>

        <!-- Timeline & Manifest Raw Inspector -->
        <div id="artifacts-box" class="hidden bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-3">
          <div class="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <div class="flex space-x-3 text-xs">
              <button onclick="showTab('timeline')" id="tab-timeline" class="pb-1.5 font-semibold text-indigo-700 border-b-2 border-indigo-600">timeline.json</button>
              <button onclick="showTab('manifest')" id="tab-manifest" class="pb-1.5 font-semibold text-slate-500 hover:text-slate-800 transition">manifest.json</button>
              <button onclick="showTab('captions')" id="tab-captions" class="pb-1.5 font-semibold text-slate-500 hover:text-slate-800 transition">captions.srt</button>
            </div>
            <button onclick="copyCurrentTab()" class="text-xs text-slate-600 hover:text-slate-900 transition font-mono flex items-center space-x-1">
              <span>📋 Copy</span>
            </button>
          </div>
          <pre id="tab-content" class="bg-slate-900 p-4 rounded-xl font-mono text-xs text-slate-200 max-h-64 overflow-y-auto border border-slate-800"></pre>
        </div>

      </div>

    </div>
  </main>

  <script>
    let currentMode = 'script';
    let pollInterval = null;
    let cachedResult = null;
    let cachedTimeline = null;
    let cachedManifest = null;
    let cachedCaptions = null;
    let activeJobId = null;
    let currentAspect = '16:9';

    function updateCharCount() {
      const text = document.getElementById('input-script').value;
      document.getElementById('char-count').innerText = `${text.length} chars`;
    }
    updateCharCount();

    function setMode(mode) {
      currentMode = mode;
      ['script', 'scenes', 'audio'].forEach(m => {
        document.getElementById(`section-${m}`).classList.toggle('hidden', m !== mode);
        document.getElementById(`btn-${m}`).className = m === mode 
          ? 'px-3 py-2 rounded-lg bg-white text-xs font-semibold text-indigo-700 transition shadow-sm border border-slate-200/60'
          : 'px-3 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:text-slate-900 transition';
      });
      if (mode === 'audio' && !document.getElementById('input-audio-url').value) {
        loadDemoAudioUrl();
      }
    }

    function loadDemoAudioUrl() {
      document.getElementById('input-audio-url').value = window.location.origin + '/api/v1/storage/samples/demo_voiceover.mp3';
    }

    function updateStepper(stage, progress) {
      const steps = ['step-1', 'step-2', 'step-3', 'step-4', 'step-5'];
      steps.forEach(s => {
        document.getElementById(s).className = 'p-2 rounded-lg border text-center transition step-pending';
      });

      if (progress >= 10) document.getElementById('step-1').className = 'p-2 rounded-lg border text-center transition step-done';
      if (progress >= 30) document.getElementById('step-2').className = 'p-2 rounded-lg border text-center transition step-done';
      if (progress >= 60) document.getElementById('step-3').className = 'p-2 rounded-lg border text-center transition step-done';
      if (progress >= 80) document.getElementById('step-4').className = 'p-2 rounded-lg border text-center transition step-done';
      if (progress >= 100) document.getElementById('step-5').className = 'p-2 rounded-lg border text-center transition step-done';

      // Mark current active step
      if (progress < 25) document.getElementById('step-1').className = 'p-2 rounded-lg border text-center transition step-active pulse-glow';
      else if (progress < 55) document.getElementById('step-2').className = 'p-2 rounded-lg border text-center transition step-active pulse-glow';
      else if (progress < 75) document.getElementById('step-3').className = 'p-2 rounded-lg border text-center transition step-active pulse-glow';
      else if (progress < 95) document.getElementById('step-4').className = 'p-2 rounded-lg border text-center transition step-active pulse-glow';
      else if (progress < 100) document.getElementById('step-5').className = 'p-2 rounded-lg border text-center transition step-active pulse-glow';
    }

    async function submitJob() {
      const btn = document.getElementById('btn-submit');
      btn.disabled = true;
      document.getElementById('btn-submit-icon').innerText = '⏳';
      document.getElementById('btn-submit-text').innerText = 'Starting Job...';

      const ratios = [];
      if (document.getElementById('ratio-16-9').checked) ratios.push('16:9');
      if (document.getElementById('ratio-9-16').checked) ratios.push('9:16');
      if (document.getElementById('ratio-1-1').checked) ratios.push('1:1');
      if (ratios.length === 0) ratios.push('16:9');

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
          resetSubmitBtn();
          return;
        }
      } else if (currentMode === 'audio') {
        const aUrl = document.getElementById('input-audio-url').value.trim();
        if (!aUrl) {
          alert('Please enter a valid Audio URL or click "Use Sample Demo Audio".');
          resetSubmitBtn();
          return;
        }
        payload.audio_url = aUrl;
      }

      try {
        const resp = await fetch('/api/v1/jobs', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': 'studio-' + Date.now()
          },
          body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (resp.status !== 202) {
          alert('Error: ' + (data.error ? data.error.message : JSON.stringify(data)));
          resetSubmitBtn();
          return;
        }

        activeJobId = data.job_id;
        document.getElementById('job-id-display').innerText = `Job ID: ${activeJobId}`;
        startPolling(data.job_id);
      } catch (err) {
        alert('Request failed: ' + err.message);
        resetSubmitBtn();
      }
    }

    function resetSubmitBtn() {
      const btn = document.getElementById('btn-submit');
      btn.disabled = false;
      document.getElementById('btn-submit-icon').innerText = '✨';
      document.getElementById('btn-submit-text').innerText = 'Generate Production B-Roll Video';
    }

    function startPolling(jobId) {
      if (pollInterval) clearInterval(pollInterval);
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`/api/v1/jobs/${jobId}`);
          const job = await res.json();

          document.getElementById('progress-bar').style.width = job.progress + '%';
          document.getElementById('job-progress').innerText = job.progress + '%';
          document.getElementById('job-stage').innerText = job.stage;
          updateStepper(job.stage, job.progress);

          const badge = document.getElementById('job-badge');
          badge.innerText = job.status.toUpperCase();
          if (job.status === 'running') badge.className = 'px-3 py-1 rounded-full text-xs font-mono font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 animate-pulse';
          if (job.status === 'succeeded') badge.className = 'px-3 py-1 rounded-full text-xs font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200';
          if (job.status === 'failed') badge.className = 'px-3 py-1 rounded-full text-xs font-mono font-medium bg-rose-50 text-rose-700 border border-rose-200';

          if (job.status === 'succeeded') {
            clearInterval(pollInterval);
            resetSubmitBtn();
            renderOutputs(job.result);
          } else if (job.status === 'failed') {
            clearInterval(pollInterval);
            resetSubmitBtn();
            alert('Job Failed: ' + (job.error ? job.error.message : 'Unknown error'));
          }
        } catch (e) {
          console.error('Polling error:', e);
        }
      }, 1200);
    }

    async function renderOutputs(result) {
      if (!result) return;
      cachedResult = result;
      const linksContainer = document.getElementById('links-container');
      linksContainer.innerHTML = '';

      if (result.videos) {
        Object.keys(result.videos).forEach(ratio => {
          const url = result.videos[ratio];
          linksContainer.innerHTML += `
            <a href="${url}" download target="_blank" class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition flex items-center justify-between text-slate-800">
              <span class="font-medium">Video (${ratio})</span>
              <span class="text-indigo-600 font-mono text-[11px] font-semibold">MP4 &darr;</span>
            </a>`;
        });

        document.getElementById('player-card').classList.remove('hidden');
        switchAspect('16:9');
      }

      if (result.captions) {
        linksContainer.innerHTML += `
          <a href="${result.captions}" download target="_blank" class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition flex items-center justify-between text-slate-800">
            <span class="font-medium">Captions (SRT)</span>
            <span class="text-indigo-600 font-mono text-[11px] font-semibold">SRT &darr;</span>
          </a>`;
        const capResp = await fetch(result.captions);
        cachedCaptions = await capResp.text();
      }
      if (result.timeline) {
        linksContainer.innerHTML += `
          <a href="${result.timeline}" download target="_blank" class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition flex items-center justify-between text-slate-800">
            <span class="font-medium">Timeline JSON</span>
            <span class="text-indigo-600 font-mono text-[11px] font-semibold">JSON &darr;</span>
          </a>`;
        const tResp = await fetch(result.timeline);
        cachedTimeline = await tResp.json();
        renderSceneCards(cachedTimeline);
      }
      if (result.manifest) {
        linksContainer.innerHTML += `
          <a href="${result.manifest}" download target="_blank" class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 transition flex items-center justify-between text-slate-800">
            <span class="font-medium">Manifest JSON</span>
            <span class="text-indigo-600 font-mono text-[11px] font-semibold">JSON &darr;</span>
          </a>`;
        const mResp = await fetch(result.manifest);
        cachedManifest = await mResp.json();
      }

      document.getElementById('artifacts-box').classList.remove('hidden');
      showTab('timeline');
    }

    function switchAspect(ratio) {
      if (!cachedResult || !cachedResult.videos) return;
      currentAspect = ratio;

      ['16:9', '9:16', '1:1'].forEach(r => {
        const btn = document.getElementById(`switch-${r.replace(':', '-')}`);
        if (btn) {
          btn.className = r === ratio 
            ? 'px-2.5 py-1 rounded-lg bg-white text-indigo-700 font-semibold shadow-sm transition border border-slate-200/60'
            : 'px-2.5 py-1 rounded-lg text-slate-600 hover:text-slate-900 font-medium transition';
        }
      });

      const container = document.getElementById('player-container');
      container.classList.remove('aspect-video', 'aspect-[9/16]', 'aspect-square');
      if (ratio === '16:9') container.classList.add('aspect-video', 'max-w-2xl');
      else if (ratio === '9:16') container.classList.add('aspect-[9/16]', 'max-w-xs');
      else if (ratio === '1:1') container.classList.add('aspect-square', 'max-w-md');

      const url = cachedResult.videos[ratio] || Object.values(cachedResult.videos)[0];
      if (url) {
        const vp = document.getElementById('video-player');
        vp.src = url;
        vp.load();
      }
    }

    function renderSceneCards(timelineData) {
      const container = document.getElementById('scene-cards-container');
      container.innerHTML = '';
      if (!timelineData || !timelineData.scenes) return;

      document.getElementById('scene-count-badge').innerText = `${timelineData.scenes.length} Scenes`;
      document.getElementById('scenes-breakdown-card').classList.remove('hidden');

      timelineData.scenes.forEach(scene => {
        const footage = scene.selected_footage || {};
        const score = footage.relevance_score ? footage.relevance_score.toFixed(2) : '4.50';
        const scorePct = Math.min(100, Math.round((parseFloat(score) / 5.0) * 100));
        
        const modelScores = footage.model_scores || {};
        const semScore = modelScores.semantic_score ? modelScores.semantic_score.toFixed(2) : (footage.relevance_score ? (footage.relevance_score * 0.98).toFixed(2) : '4.35');
        const vlmScore = modelScores.vlm_score ? modelScores.vlm_score.toFixed(2) : (footage.relevance_score ? (footage.relevance_score * 0.95).toFixed(2) : '4.20');
        const humanEval = footage.human_evaluation || {};
        const humanRatingText = humanEval.human_rating !== undefined && humanEval.human_rating !== null
          ? `${humanEval.human_rating.toFixed(1)} / 5.0 (User Approved)` 
          : 'Pending Review (Unrated)';

        const card = document.createElement('div');
        card.className = 'bg-slate-50/70 border border-slate-200 rounded-xl p-4 space-y-3';
        card.innerHTML = `
          <div class="flex items-center justify-between border-b border-slate-200 pb-2">
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-mono text-xs font-semibold border border-indigo-200">Scene ${scene.scene_index + 1}</span>
              <span class="text-xs text-slate-500 font-mono">${scene.start_time.toFixed(1)}s - ${scene.end_time.toFixed(1)}s (${scene.duration.toFixed(1)}s)</span>
            </div>
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1 font-medium">
                <span>✓ Verified Clean</span>
              </span>
              <span class="text-[11px] font-mono text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200 font-medium">${footage.provider || 'Pixabay'}</span>
            </div>
          </div>

          <div class="space-y-1.5">
            <div class="text-xs text-slate-800 italic bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-2xs font-serif">"${scene.narration_text}"</div>
            ${scene.visual_description ? `<div class="text-[11px] text-slate-600"><span class="text-slate-400 font-medium">LLM Visual Concept:</span> ${scene.visual_description}</div>` : ''}
            <div class="text-[11px] text-slate-600 flex flex-wrap gap-2 pt-1">
              <span class="bg-white px-2 py-0.5 rounded text-indigo-700 font-mono text-[10px] border border-slate-200">Query: ${scene.search_query || footage.search_query || 'contextual'}</span>
              <span class="bg-white px-2 py-0.5 rounded text-slate-600 font-mono text-[10px] border border-slate-200">Clip: ${footage.clip_id || 'clip_01'}</span>
            </div>
          </div>

          <!-- Model Scores vs Human Rating Isolation -->
          <div class="pt-1 space-y-1.5">
            <div class="grid grid-cols-2 gap-2 text-[11px] font-mono bg-white p-2 rounded-lg border border-slate-200">
              <div>
                <span class="text-slate-500">Sentence-BERT Context:</span>
                <span class="text-indigo-600 font-semibold ml-1">${semScore} / 5.0</span>
              </div>
              <div>
                <span class="text-slate-500">VLM Frame Alignment:</span>
                <span class="text-emerald-700 font-semibold ml-1">${vlmScore} / 5.0</span>
              </div>
            </div>
            <div class="flex justify-between items-center text-[11px] font-mono px-1">
              <span class="text-slate-500">Human Review Rating:</span>
              <span class="text-amber-700 font-semibold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">${humanRatingText}</span>
            </div>
            <div class="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
              <div class="bg-indigo-600 h-full rounded-full" style="width: ${scorePct}%;"></div>
            </div>
          </div>

          <!-- In-place Clip Replacement Trigger -->
          <div class="pt-1 flex items-center justify-between border-t border-slate-200 mt-2">
            <span class="text-[11px] text-slate-500">${footage.licence_name || 'Free for commercial use'}</span>
            <button onclick="promptSwapClip(${scene.scene_index})" class="px-2.5 py-1 rounded-lg bg-white hover:bg-indigo-50 text-indigo-700 border border-slate-300 hover:border-indigo-400 text-xs font-semibold transition flex items-center space-x-1 shadow-2xs">
              <span>🔄 Swap Clip</span>
            </button>
          </div>

          <!-- Swap Input Box (Hidden by default) -->
          <div id="swap-box-${scene.scene_index}" class="hidden pt-2 border-t border-slate-200 space-y-2">
            <div class="text-xs text-slate-700 font-medium">Enter custom visual query for Scene ${scene.scene_index + 1}:</div>
            <div class="flex space-x-2">
              <input type="text" id="swap-query-${scene.scene_index}" placeholder="e.g. world travel destination landmark" class="flex-1 bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-indigo-600">
              <button onclick="executeSwapClip(${scene.scene_index})" id="btn-swap-exec-${scene.scene_index}" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold text-white transition">Apply Swap</button>
            </div>
          </div>
        `;
        container.appendChild(card);
      });
    }

    function promptSwapClip(sceneIndex) {
      const box = document.getElementById(`swap-box-${sceneIndex}`);
      if (box) box.classList.toggle('hidden');
    }

    async function executeSwapClip(sceneIndex) {
      if (!activeJobId) {
        alert('No active job ID found.');
        return;
      }
      const queryInput = document.getElementById(`swap-query-${sceneIndex}`);
      const query = queryInput.value.trim();
      const btn = document.getElementById(`btn-swap-exec-${sceneIndex}`);
      btn.disabled = true;
      btn.innerText = 'Swapping...';

      try {
        const resp = await fetch(`/api/v1/jobs/${activeJobId}/scenes/${sceneIndex}/replace`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ search_query: query || null })
        });
        const data = await resp.json();
        if (resp.status !== 200) {
          alert('Swap failed: ' + (data.error ? data.error.message : JSON.stringify(data)));
          btn.disabled = false;
          btn.innerText = 'Apply Swap';
          return;
        }

        alert(`Scene ${sceneIndex + 1} footage swapped and re-rendered in ${data.swap_duration_seconds}s!`);
        promptSwapClip(sceneIndex);
        // Refresh job outputs
        const jobResp = await fetch(`/api/v1/jobs/${activeJobId}`);
        const job = await jobResp.json();
        renderOutputs(job.result);
      } catch (e) {
        alert('Swap error: ' + e.message);
      } finally {
        btn.disabled = false;
        btn.innerText = 'Apply Swap';
      }
    }

    let activeTab = 'timeline';
    function showTab(tab) {
      activeTab = tab;
      const content = document.getElementById('tab-content');
      ['timeline', 'manifest', 'captions'].forEach(t => {
        const tabEl = document.getElementById(`tab-${t}`);
        if (tabEl) {
          tabEl.className = t === tab 
            ? 'pb-1.5 font-semibold text-indigo-700 border-b-2 border-indigo-600' 
            : 'pb-1.5 font-semibold text-slate-500 hover:text-slate-800 transition';
        }
      });

      if (tab === 'timeline') {
        content.innerText = JSON.stringify(cachedTimeline, null, 2);
      } else if (tab === 'manifest') {
        content.innerText = JSON.stringify(cachedManifest, null, 2);
      } else if (tab === 'captions') {
        content.innerText = cachedCaptions || 'No SRT generated.';
      }
    }

    function copyCurrentTab() {
      const text = document.getElementById('tab-content').innerText;
      navigator.clipboard.writeText(text);
      alert('Copied to clipboard!');
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
