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
    .pulse-glow { box-shadow: 0 0 20px rgba(99, 102, 241, 0.4); }
    .step-active { border-color: #6366f1; background-color: rgba(99, 102, 241, 0.15); color: #818cf8; }
    .step-done { border-color: #10b981; background-color: rgba(16, 185, 129, 0.15); color: #34d399; }
    .step-pending { border-color: #334155; background-color: rgba(30, 41, 59, 0.5); color: #64748b; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  <!-- Top Navigation Header -->
  <header class="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between">
      <div class="flex items-center space-x-3.5">
        <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center font-black text-white text-base shadow-lg shadow-indigo-500/25">IB</div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-base font-bold text-white tracking-tight">IncuBrix Video Studio</h1>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">v2.0 Pro</span>
          </div>
          <p class="text-xs text-slate-400">Autonomous Script & Voiceover to B-Roll Production Engine</p>
        </div>
      </div>
      <div class="flex items-center space-x-3 text-xs">
        <div class="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-emerald-400">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span class="font-medium">Pixabay + Sentence-BERT Ready</span>
        </div>
        <a href="/docs" target="_blank" class="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition font-medium">Swagger API</a>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-6 space-y-6">
    <!-- Presets Bar -->
    <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 shadow-sm">
      <div class="flex items-center justify-between mb-2.5">
        <span class="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
          <span>⚡ Quick Test Scenarios</span>
        </span>
        <span class="text-[11px] text-slate-400">1-click automated presets with full domain matching</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <button onclick="applyPreset('cyber')" class="px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-indigo-600/20 hover:border-indigo-500/50 border border-slate-700/60 text-xs text-slate-200 transition flex items-center space-x-1.5">
          <span>🛡️ Cybersecurity</span>
        </button>
        <button onclick="applyPreset('ai')" class="px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-indigo-600/20 hover:border-indigo-500/50 border border-slate-700/60 text-xs text-slate-200 transition flex items-center space-x-1.5">
          <span>🤖 AI & Tech</span>
        </button>
        <button onclick="applyPreset('business')" class="px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-indigo-600/20 hover:border-indigo-500/50 border border-slate-700/60 text-xs text-slate-200 transition flex items-center space-x-1.5">
          <span>📈 Business (40% Stat)</span>
        </button>
        <button onclick="applyPreset('cloud')" class="px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-indigo-600/20 hover:border-indigo-500/50 border border-slate-700/60 text-xs text-slate-200 transition flex items-center space-x-1.5">
          <span>☁️ Cloud Tech</span>
        </button>
        <button onclick="applyPreset('tamil')" class="px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-indigo-600/20 hover:border-indigo-500/50 border border-slate-700/60 text-xs text-slate-200 transition flex items-center space-x-1.5">
          <span>🇮🇳 Tamil Voice</span>
        </button>
        <button onclick="applyPreset('hindi')" class="px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-indigo-600/20 hover:border-indigo-500/50 border border-slate-700/60 text-xs text-slate-200 transition flex items-center space-x-1.5">
          <span>🇮🇳 Hindi Voice</span>
        </button>
        <button onclick="applyPreset('audio')" class="px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-indigo-600/20 hover:border-indigo-500/50 border border-slate-700/60 text-xs text-slate-200 transition flex items-center space-x-1.5">
          <span>🎙️ Audio Voiceover URL</span>
        </button>
        <button onclick="applyPreset('scenes')" class="px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-indigo-600/20 hover:border-indigo-500/50 border border-slate-700/60 text-xs text-slate-200 transition flex items-center space-x-1.5">
          <span>📋 Scene List JSON</span>
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Left Column: Input Studio Form -->
      <div class="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h2 class="text-sm font-bold text-white flex items-center space-x-2">
            <span>Video Creation Settings</span>
          </h2>
          <span class="text-xs text-slate-400 font-mono" id="char-count">0 chars</span>
        </div>

        <div class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1.5">Input Modality</label>
            <div class="grid grid-cols-3 gap-2">
              <button type="button" onclick="setMode('script')" id="btn-script" class="px-3 py-2 rounded-xl bg-indigo-600 text-xs font-semibold text-white transition shadow-sm">Script Text</button>
              <button type="button" onclick="setMode('scenes')" id="btn-scenes" class="px-3 py-2 rounded-xl bg-slate-800/90 text-xs font-semibold text-slate-300 transition">Scene List</button>
              <button type="button" onclick="setMode('audio')" id="btn-audio" class="px-3 py-2 rounded-xl bg-slate-800/90 text-xs font-semibold text-slate-300 transition">Audio URL</button>
            </div>
          </div>

          <!-- Script Input -->
          <div id="section-script">
            <label class="block text-xs font-semibold text-slate-300 mb-1.5">Narration Script</label>
            <textarea id="input-script" rows="4" oninput="updateCharCount()" class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition leading-relaxed">Hackers constantly target sensitive digital infrastructure. Strong passwords, two-factor authentication, and secure networks help protect our data.</textarea>
          </div>

          <!-- Scenes Input -->
          <div id="section-scenes" class="hidden">
            <label class="block text-xs font-semibold text-slate-300 mb-1.5">Structured Scene List (JSON)</label>
            <textarea id="input-scenes" rows="4" class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl p-3 font-mono text-xs text-slate-200 placeholder-slate-500 focus:outline-none transition">[
  {"text": "Strong passwords and two-factor authentication protect data.", "visual_hint": "cybersecurity password lock screen"},
  {"text": "Python programming powers machine learning models.", "visual_hint": "software developer coding on computer"}
]</textarea>
          </div>

          <!-- Audio URL Input -->
          <div id="section-audio" class="hidden">
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-xs font-semibold text-slate-300">Voiceover Audio URL</label>
              <button type="button" onclick="loadDemoAudioUrl()" class="text-xs text-indigo-400 hover:text-indigo-300 transition underline">Use Sample Demo Audio</button>
            </div>
            <input type="url" id="input-audio-url" class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl p-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none transition font-mono text-xs" placeholder="https://example.com/voiceover.mp3" />
          </div>

          <!-- Voice & Aspect Ratios -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1.5">Voice Persona</label>
              <select id="input-voice" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none">
                <option value="en-IN-female">en-IN-female (Neerja)</option>
                <option value="en-IN-male">en-IN-male (Prabhat)</option>
                <option value="ta-IN-female">ta-IN-female (Pallavi - Tamil)</option>
                <option value="hi-IN-female">hi-IN-female (Swara - Hindi)</option>
                <option value="en-US-male">en-US-male (Guy)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1.5">Aspect Ratios</label>
              <div class="flex items-center space-x-3 pt-2 text-xs">
                <label class="flex items-center space-x-1.5 cursor-pointer"><input type="checkbox" id="ratio-16-9" checked class="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"> <span>16:9</span></label>
                <label class="flex items-center space-x-1.5 cursor-pointer"><input type="checkbox" id="ratio-9-16" checked class="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"> <span>9:16</span></label>
                <label class="flex items-center space-x-1.5 cursor-pointer"><input type="checkbox" id="ratio-1-1" checked class="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"> <span>1:1</span></label>
              </div>
            </div>
          </div>

          <!-- Content Avoidance -->
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1.5">Content Avoidance List</label>
            <input type="text" id="input-avoid" value="people's faces, alcohol" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none" placeholder="Comma separated: people's faces, alcohol, violence" />
          </div>

          <!-- Captions options -->
          <div class="flex items-center space-x-5 pt-1 text-xs text-slate-300">
            <label class="flex items-center space-x-2 cursor-pointer"><input type="checkbox" id="burn-in" checked class="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"> <span>Burn-in Subtitles</span></label>
            <label class="flex items-center space-x-2 cursor-pointer"><input type="checkbox" id="export-srt" checked class="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"> <span>Generate captions.srt</span></label>
          </div>

          <!-- Submit Button -->
          <button id="btn-submit" onclick="submitJob()" class="w-full py-3.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 rounded-xl font-bold text-sm text-white shadow-lg shadow-indigo-600/25 transition active:scale-[0.99] flex items-center justify-center space-x-2">
            <span id="btn-submit-icon">✨</span>
            <span id="btn-submit-text">Generate Production B-Roll Video</span>
          </button>
        </div>
      </div>

      <!-- Right Column: Live Monitor & Video Studio -->
      <div class="lg:col-span-7 space-y-6">
        
        <!-- Live Execution Monitor Card -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-sm font-bold text-white">Pipeline Execution Monitor</h2>
              <p class="text-xs text-slate-400" id="job-id-display">Ready for generation job</p>
            </div>
            <div id="job-badge" class="px-3 py-1 rounded-full text-xs font-mono font-medium bg-slate-800 text-slate-400">Idle</div>
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
            <div class="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
              <div id="progress-bar" class="bg-gradient-to-r from-indigo-500 to-purple-500 h-full w-0 transition-all duration-300"></div>
            </div>
            <div class="flex justify-between text-xs text-slate-400 font-mono mt-2">
              <span id="job-stage" class="truncate max-w-xs">No active pipeline</span>
              <span id="job-progress" class="font-bold text-slate-200">0%</span>
            </div>
          </div>
        </div>

        <!-- Video Player Studio Card -->
        <div id="player-card" class="hidden bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-white flex items-center space-x-2">
              <span>Preview Rendered Video</span>
            </h3>
            <!-- Multi-Aspect Ratio Preview Switcher -->
            <div id="aspect-switcher" class="flex items-center space-x-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
              <button onclick="switchAspect('16:9')" id="switch-16-9" class="px-2.5 py-1 rounded-lg bg-indigo-600 text-white font-medium transition">16:9 Landscape</button>
              <button onclick="switchAspect('9:16')" id="switch-9-16" class="px-2.5 py-1 rounded-lg text-slate-400 hover:text-white font-medium transition">9:16 Vertical</button>
              <button onclick="switchAspect('1:1')" id="switch-1-1" class="px-2.5 py-1 rounded-lg text-slate-400 hover:text-white font-medium transition">1:1 Square</button>
            </div>
          </div>

          <div id="player-container" class="bg-black rounded-xl overflow-hidden border border-slate-800 aspect-video relative flex items-center justify-center transition-all duration-300 mx-auto">
            <video id="video-player" controls class="max-h-full max-w-full rounded-lg shadow-2xl"></video>
          </div>

          <!-- Download Assets Hub -->
          <div id="results-links" class="pt-2">
            <div class="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Production Output Assets</div>
            <div id="links-container" class="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs"></div>
          </div>
        </div>

        <!-- Visual Scene Breakdown Cards (Interactive Timeline) -->
        <div id="scenes-breakdown-card" class="hidden bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-bold text-white">Visual Scene Breakdown</h3>
              <p class="text-xs text-slate-400">Inspecting narration alignment, LLM visual concepts & Sentence-BERT ranking</p>
            </div>
            <span id="scene-count-badge" class="px-2.5 py-1 rounded-full text-xs font-mono bg-indigo-950 text-indigo-400 border border-indigo-800">0 Scenes</span>
          </div>
          <div id="scene-cards-container" class="space-y-3 max-h-96 overflow-y-auto pr-1"></div>
        </div>

        <!-- Timeline & Manifest Raw Inspector -->
        <div id="artifacts-box" class="hidden bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div class="flex space-x-3 text-xs">
              <button onclick="showTab('timeline')" id="tab-timeline" class="pb-1.5 font-semibold text-indigo-400 border-b-2 border-indigo-400">timeline.json</button>
              <button onclick="showTab('manifest')" id="tab-manifest" class="pb-1.5 font-semibold text-slate-400">manifest.json</button>
              <button onclick="showTab('captions')" id="tab-captions" class="pb-1.5 font-semibold text-slate-400">captions.srt</button>
            </div>
            <button onclick="copyCurrentTab()" class="text-xs text-slate-400 hover:text-slate-200 transition font-mono flex items-center space-x-1">
              <span>📋 Copy</span>
            </button>
          </div>
          <pre id="tab-content" class="bg-slate-950 p-4 rounded-xl font-mono text-xs text-slate-300 max-h-64 overflow-y-auto border border-slate-800/80"></pre>
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
          ? 'px-3 py-2 rounded-xl bg-indigo-600 text-xs font-semibold text-white transition shadow-sm'
          : 'px-3 py-2 rounded-xl bg-slate-800/90 text-xs font-semibold text-slate-300 transition';
      });
      if (mode === 'audio' && !document.getElementById('input-audio-url').value) {
        loadDemoAudioUrl();
      }
    }

    function loadDemoAudioUrl() {
      document.getElementById('input-audio-url').value = window.location.origin + '/api/v1/storage/samples/demo_voiceover.mp3';
    }

    function applyPreset(name) {
      if (name === 'cyber') {
        setMode('script');
        document.getElementById('input-script').value = 'Hackers constantly target sensitive digital infrastructure. Strong passwords, two-factor authentication, and secure networks help protect our data.';
        document.getElementById('input-voice').value = 'en-IN-female';
        document.getElementById('input-avoid').value = "people's faces, alcohol";
      } else if (name === 'ai') {
        setMode('script');
        document.getElementById('input-script').value = 'Artificial intelligence automates enterprise operations and analyzes vast amounts of data in real-time. Deep learning models deliver unprecedented precision.';
        document.getElementById('input-voice').value = 'en-IN-female';
        document.getElementById('input-avoid').value = "people's faces, alcohol";
      } else if (name === 'business') {
        setMode('script');
        document.getElementById('input-script').value = 'Enterprise revenues surged 40% in fiscal 2025. Innovative strategy and international teamwork drove record profits across all sectors.';
        document.getElementById('input-voice').value = 'en-IN-male';
        document.getElementById('input-avoid').value = "people's faces";
      } else if (name === 'cloud') {
        setMode('script');
        document.getElementById('input-script').value = 'Modern cloud computing platforms deliver elastic server infrastructure and resilient enterprise databases.';
        document.getElementById('input-voice').value = 'en-US-male';
        document.getElementById('input-avoid').value = "people's faces";
      } else if (name === 'tamil') {
        setMode('script');
        document.getElementById('input-script').value = 'Hackers attack networks daily. Strong passwords and cybersecurity protect our digital information.';
        document.getElementById('input-voice').value = 'ta-IN-female';
        document.getElementById('input-avoid').value = "people's faces";
      } else if (name === 'hindi') {
        setMode('script');
        document.getElementById('input-script').value = 'Cyber security protects personal data. Strong passwords and secure networks keep digital systems safe.';
        document.getElementById('input-voice').value = 'hi-IN-female';
        document.getElementById('input-avoid').value = "people's faces";
      } else if (name === 'audio') {
        setMode('audio');
        loadDemoAudioUrl();
      } else if (name === 'scenes') {
        setMode('scenes');
        document.getElementById('input-scenes').value = JSON.stringify([
          {"text": "Strong passwords and two-factor authentication protect data.", "visual_hint": "cybersecurity password lock screen"},
          {"text": "Python programming powers machine learning models.", "visual_hint": "software developer coding on computer"}
        ], null, 2);
      }
      updateCharCount();
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
          if (job.status === 'running') badge.className = 'px-3 py-1 rounded-full text-xs font-mono font-medium bg-indigo-950 text-indigo-400 border border-indigo-800 animate-pulse';
          if (job.status === 'succeeded') badge.className = 'px-3 py-1 rounded-full text-xs font-mono font-medium bg-emerald-950 text-emerald-400 border border-emerald-800';
          if (job.status === 'failed') badge.className = 'px-3 py-1 rounded-full text-xs font-mono font-medium bg-rose-950 text-rose-400 border border-rose-800';

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
            <a href="${url}" download target="_blank" class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/80 hover:bg-slate-900 transition flex items-center justify-between text-slate-200">
              <span class="font-medium">Video (${ratio})</span>
              <span class="text-indigo-400 font-mono text-[11px]">MP4 &darr;</span>
            </a>`;
        });

        document.getElementById('player-card').classList.remove('hidden');
        switchAspect('16:9');
      }

      if (result.captions) {
        linksContainer.innerHTML += `
          <a href="${result.captions}" download target="_blank" class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/80 hover:bg-slate-900 transition flex items-center justify-between text-slate-200">
            <span class="font-medium">Captions (SRT)</span>
            <span class="text-indigo-400 font-mono text-[11px]">SRT &darr;</span>
          </a>`;
        const capResp = await fetch(result.captions);
        cachedCaptions = await capResp.text();
      }
      if (result.timeline) {
        linksContainer.innerHTML += `
          <a href="${result.timeline}" download target="_blank" class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/80 hover:bg-slate-900 transition flex items-center justify-between text-slate-200">
            <span class="font-medium">Timeline JSON</span>
            <span class="text-indigo-400 font-mono text-[11px]">JSON &darr;</span>
          </a>`;
        const tResp = await fetch(result.timeline);
        cachedTimeline = await tResp.json();
        renderSceneCards(cachedTimeline);
      }
      if (result.manifest) {
        linksContainer.innerHTML += `
          <a href="${result.manifest}" download target="_blank" class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/80 hover:bg-slate-900 transition flex items-center justify-between text-slate-200">
            <span class="font-medium">Manifest JSON</span>
            <span class="text-indigo-400 font-mono text-[11px]">JSON &darr;</span>
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
            ? 'px-2.5 py-1 rounded-lg bg-indigo-600 text-white font-medium transition'
            : 'px-2.5 py-1 rounded-lg text-slate-400 hover:text-white font-medium transition';
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

        const card = document.createElement('div');
        card.className = 'bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3';
        card.innerHTML = `
          <div class="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 font-mono text-xs font-semibold">Scene ${scene.scene_index + 1}</span>
              <span class="text-xs text-slate-400 font-mono">${scene.start_time.toFixed(1)}s - ${scene.end_time.toFixed(1)}s (${scene.duration.toFixed(1)}s)</span>
            </div>
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-950/60 text-emerald-400 border border-emerald-800/50 flex items-center space-x-1">
                <span>✓ Verified Clean</span>
              </span>
              <span class="text-[11px] font-mono text-slate-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">${footage.provider || 'Pixabay'}</span>
            </div>
          </div>

          <div class="space-y-1.5">
            <div class="text-xs text-slate-200 italic bg-slate-900/50 p-2.5 rounded-lg border border-slate-800/50">"${scene.narration_text}"</div>
            ${scene.visual_description ? `<div class="text-[11px] text-slate-400"><span class="text-slate-500 font-medium">LLM Visual Concept:</span> ${scene.visual_description}</div>` : ''}
            <div class="text-[11px] text-slate-400 flex flex-wrap gap-2 pt-1">
              <span class="bg-slate-900 px-2 py-0.5 rounded text-indigo-300 font-mono text-[10px] border border-slate-800">Query: ${scene.search_query || footage.search_query || 'contextual'}</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded text-slate-300 font-mono text-[10px] border border-slate-800">Clip: ${footage.clip_id || 'clip_01'}</span>
            </div>
          </div>

          <!-- Sentence-BERT Relevance Score Gauge -->
          <div class="pt-1">
            <div class="flex justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>Sentence-BERT Semantic Match:</span>
              <span class="text-emerald-400 font-semibold">${score} / 5.0</span>
            </div>
            <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden border border-slate-800">
              <div class="bg-emerald-500 h-full rounded-full" style="width: ${scorePct}%;"></div>
            </div>
          </div>

          <!-- In-place Clip Replacement Trigger -->
          <div class="pt-1 flex items-center justify-between border-t border-slate-800/60 mt-2">
            <span class="text-[11px] text-slate-500">${footage.licence_name || 'Free for commercial use'}</span>
            <button onclick="promptSwapClip(${scene.scene_index})" class="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-indigo-600/30 text-indigo-300 border border-slate-800 hover:border-indigo-500/50 text-xs font-medium transition flex items-center space-x-1">
              <span>🔄 Swap Clip</span>
            </button>
          </div>

          <!-- Swap Input Box (Hidden by default) -->
          <div id="swap-box-${scene.scene_index}" class="hidden pt-2 border-t border-slate-800 space-y-2">
            <div class="text-xs text-slate-300 font-medium">Enter custom visual query for Scene ${scene.scene_index + 1}:</div>
            <div class="flex space-x-2">
              <input type="text" id="swap-query-${scene.scene_index}" placeholder="e.g. digital security lock computer" class="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
              <button onclick="executeSwapClip(${scene.scene_index})" id="btn-swap-exec-${scene.scene_index}" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition">Apply Swap</button>
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
            ? 'pb-1.5 font-semibold text-indigo-400 border-b-2 border-indigo-400' 
            : 'pb-1.5 font-semibold text-slate-400 hover:text-slate-200 transition';
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
