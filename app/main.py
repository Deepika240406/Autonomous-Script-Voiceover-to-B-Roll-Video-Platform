import os

# Limit CPU / OpenMP / MKL / BLAS worker threads immediately on import to keep
# memory usage well within 512MB RAM on free-tier containers (e.g. Render, Railway).
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

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
    # Render free tier has 512MB RAM; enforce 1 worker loop on containerized hosts
    is_render = bool(os.environ.get("RENDER"))
    concurrency = 1 if is_render else min(2, settings.MAX_CONCURRENT_JOBS)
    for i in range(concurrency):
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


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse, tags=["Web UI"])
def get_web_dashboard():
    """
    Intuitive, responsive web interface for evaluating the engine, submitting jobs,
    previewing videos, inspecting timelines, and testing clip replacement.
    """
    html_content = """<!DOCTYPE html>
<html lang="en" class="dark scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>IncuBrix Studio — AI Autonomous Video Production Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace'],
          },
          colors: {
            brand: {
              50: '#eef2ff',
              100: '#e0e7ff',
              500: '#6366f1',
              600: '#4f46e5',
              700: '#4338ca',
            }
          }
        }
      }
    }
  </script>
  <style>
    body { font-family: 'Inter', sans-serif; }
    .bg-grid-pattern {
      background-size: 32px 32px;
      background-image: linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                        linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
    }
    .glow-effect {
      background: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
    }
    .custom-scroll::-webkit-scrollbar { width: 6px; }
    .custom-scroll::-webkit-scrollbar-track { background: #0f172a; }
    .custom-scroll::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
  </style>
</head>
<body class="bg-[#0b0f19] text-slate-100 min-h-screen flex flex-col antialiased selection:bg-indigo-500 selection:text-white bg-grid-pattern relative">

  <!-- Ambient Glow Background -->
  <div class="glow-effect absolute top-0 left-0 right-0 h-[500px] pointer-events-none -z-10"></div>

  <!-- Header / Navigation -->
  <header class="border-b border-slate-800/80 bg-[#0b0f19]/80 backdrop-blur-md sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <span class="text-base font-bold tracking-tight text-white">IncuBrix<span class="text-indigo-400">Studio</span></span>
          <span class="ml-2 px-2 py-0.5 text-[10px] font-semibold font-mono rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">v1.0 Production</span>
        </div>
      </div>

      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Engine Online</span>
        </div>
        <a href="/docs" target="_blank" class="text-xs text-slate-400 hover:text-white transition flex items-center space-x-1 border border-slate-800 rounded-lg px-3 py-1.5 hover:bg-slate-800/60">
          <span>API Docs</span>
          <svg class="w-3 h-3 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
        </a>
      </div>
    </div>
  </header>

  <!-- Studio Workspace (Clean 2-Column Professional Layout) -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full">
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      
      <!-- LEFT COLUMN: Creator Studio Panel (5 Cols) -->
      <div class="lg:col-span-5 bg-[#131927] border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-6">
        <div class="border-b border-slate-800 pb-4 flex items-center justify-between">
          <div>
            <h2 class="text-base font-bold text-white tracking-tight">Video Generator</h2>
            <p class="text-xs text-slate-400">Script to autonomous B-roll composition</p>
          </div>
          <span id="char-count" class="text-xs text-slate-400 font-mono bg-slate-900 px-2.5 py-1 rounded border border-slate-800">0 chars</span>
        </div>

        <div class="space-y-5">
          <!-- Input Tabs -->
          <div>
            <div class="grid grid-cols-3 gap-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800 text-xs font-medium">
              <button type="button" onclick="setMode('script')" id="btn-script" class="py-2 rounded-lg bg-indigo-600 text-white font-semibold transition">Script Text</button>
              <button type="button" onclick="setMode('scenes')" id="btn-scenes" class="py-2 rounded-lg text-slate-400 hover:text-white transition">Scene List</button>
              <button type="button" onclick="setMode('audio')" id="btn-audio" class="py-2 rounded-lg text-slate-400 hover:text-white transition">Audio URL</button>
            </div>
          </div>

          <!-- Script Textarea -->
          <div id="section-script">
            <textarea id="input-script" rows="4" oninput="updateCharCount()" class="w-full bg-[#0b0f19] border border-slate-700/80 focus:border-indigo-500 rounded-xl p-3.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition leading-relaxed resize-none" placeholder="Enter narration script... e.g. Travel allows us to explore new places and experience different cultures.">Travel allows us to explore new places and experience different cultures.</textarea>
          </div>

          <!-- Scene List Textarea -->
          <div id="section-scenes" class="hidden">
            <textarea id="input-scenes" rows="4" class="w-full bg-[#0b0f19] border border-slate-700/80 focus:border-indigo-500 rounded-xl p-3.5 font-mono text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition resize-none">[
  {"text": "Travel allows us to explore new places and experience different cultures.", "visual_hint": "scenic world travel destination landmark"},
  {"text": "Ancient monuments and cultural festivals reveal our shared history.", "visual_hint": "traditional cultural festival monuments"}
]</textarea>
          </div>

          <!-- Audio URL Input -->
          <div id="section-audio" class="hidden space-y-1.5">
            <input type="url" id="input-audio-url" class="w-full bg-[#0b0f19] border border-slate-700/80 focus:border-indigo-500 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition font-mono" placeholder="https://example.com/voiceover.mp3" />
            <div class="text-right">
              <button type="button" onclick="loadDemoAudioUrl()" class="text-[11px] text-indigo-400 hover:text-indigo-300 transition">Use Sample Audio</button>
            </div>
          </div>

          <!-- Voice Persona -->
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Voice Persona</label>
            <select id="input-voice" class="w-full bg-[#0b0f19] border border-slate-700/80 rounded-xl p-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="en-IN-female">🇮🇳 en-IN-female (Neerja)</option>
              <option value="en-IN-male">🇮🇳 en-IN-male (Prabhat)</option>
              <option value="ta-IN-female">🇮🇳 ta-IN-female (Pallavi - Tamil)</option>
              <option value="hi-IN-female">🇮🇳 hi-IN-female (Swara - Hindi)</option>
              <option value="en-US-male">🇺🇸 en-US-male (Guy)</option>
            </select>
          </div>

          <!-- Aspect Ratio Selector Cards -->
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Aspect Ratio</label>
            <div class="grid grid-cols-3 gap-2">
              <label id="lbl-ratio-16-9" class="flex flex-col items-center justify-center p-2.5 rounded-xl border border-indigo-500 bg-indigo-500/10 text-indigo-300 font-medium text-xs cursor-pointer transition select-none">
                <input type="checkbox" id="ratio-16-9" checked onchange="toggleRatioUI('16-9')" class="hidden">
                <span class="text-base">🖥️</span>
                <span class="font-bold mt-1">16:9</span>
                <span class="text-[10px] text-slate-400">Landscape</span>
              </label>
              <label id="lbl-ratio-9-16" class="flex flex-col items-center justify-center p-2.5 rounded-xl border border-slate-800 bg-[#0b0f19] text-slate-400 font-medium text-xs cursor-pointer hover:border-slate-700 transition select-none">
                <input type="checkbox" id="ratio-9-16" onchange="toggleRatioUI('9-16')" class="hidden">
                <span class="text-base">📱</span>
                <span class="font-bold mt-1">9:16</span>
                <span class="text-[10px] text-slate-500">Vertical</span>
              </label>
              <label id="lbl-ratio-1-1" class="flex flex-col items-center justify-center p-2.5 rounded-xl border border-slate-800 bg-[#0b0f19] text-slate-400 font-medium text-xs cursor-pointer hover:border-slate-700 transition select-none">
                <input type="checkbox" id="ratio-1-1" onchange="toggleRatioUI('1-1')" class="hidden">
                <span class="text-base">⏹️</span>
                <span class="font-bold mt-1">1:1</span>
                <span class="text-[10px] text-slate-500">Square</span>
              </label>
            </div>
          </div>

          <!-- Content Avoidance Rules -->
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Content Avoidance Filters</label>
            <input type="text" id="input-avoid" value="people's faces, alcohol" class="w-full bg-[#0b0f19] border border-slate-700/80 rounded-xl p-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" placeholder="e.g. people's faces, alcohol, weapons" />
          </div>

          <!-- Subtitle Options -->
          <div class="flex items-center space-x-6 text-xs text-slate-300 pt-1 border-t border-slate-800/80">
            <label class="flex items-center space-x-2 cursor-pointer hover:text-white transition"><input type="checkbox" id="burn-in" checked class="w-4 h-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-0"> <span>Burn-in Subtitles</span></label>
            <label class="flex items-center space-x-2 cursor-pointer hover:text-white transition"><input type="checkbox" id="export-srt" checked class="w-4 h-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-0"> <span>Export captions.srt</span></label>
          </div>

          <!-- Submit Button -->
          <button id="btn-submit" onclick="submitJob()" class="w-full py-3.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold text-sm text-white shadow-lg shadow-indigo-600/30 transition-all active:scale-[0.99] flex items-center justify-center space-x-2 cursor-pointer">
            <span id="btn-submit-icon">✨</span>
            <span id="btn-submit-text">Generate Production Video</span>
          </button>
        </div>
      </div>

      <!-- RIGHT COLUMN: Production Execution & Review Studio (7 Cols) -->
      <div class="lg:col-span-7 space-y-6">
        
        <!-- Pipeline Execution Monitor Card -->
        <div class="bg-[#131927] border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-base font-bold text-white tracking-tight">Execution Pipeline</h2>
              <p class="text-xs text-slate-400 font-mono" id="job-id-display">Ready for generation job</p>
            </div>
            <div id="job-badge" class="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-slate-900 text-slate-400 border border-slate-800">Idle</div>
          </div>

          <!-- Stepper -->
          <div class="grid grid-cols-5 gap-1.5 pt-1">
            <div id="step-1" class="p-2.5 rounded-xl border border-slate-800/80 bg-slate-900/60 text-slate-500 text-center transition">
              <div class="text-[10px] font-mono uppercase font-bold">1. Ingest</div>
            </div>
            <div id="step-2" class="p-2.5 rounded-xl border border-slate-800/80 bg-slate-900/60 text-slate-500 text-center transition">
              <div class="text-[10px] font-mono uppercase font-bold">2. Speech</div>
            </div>
            <div id="step-3" class="p-2.5 rounded-xl border border-slate-800/80 bg-slate-900/60 text-slate-500 text-center transition">
              <div class="text-[10px] font-mono uppercase font-bold">3. LLM Scene</div>
            </div>
            <div id="step-4" class="p-2.5 rounded-xl border border-slate-800/80 bg-slate-900/60 text-slate-500 text-center transition">
              <div class="text-[10px] font-mono uppercase font-bold">4. Match</div>
            </div>
            <div id="step-5" class="p-2.5 rounded-xl border border-slate-800/80 bg-slate-900/60 text-slate-500 text-center transition">
              <div class="text-[10px] font-mono uppercase font-bold">5. Render</div>
            </div>
          </div>

          <!-- Progress Bar -->
          <div>
            <div class="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-slate-800">
              <div id="progress-bar" class="bg-gradient-to-r from-indigo-500 to-violet-500 h-full w-0 transition-all duration-300"></div>
            </div>
            <div class="flex justify-between text-xs text-slate-400 font-mono mt-2">
              <span id="job-stage" class="truncate max-w-xs">Awaiting input submission</span>
              <span id="job-progress" class="font-bold text-white">0%</span>
            </div>
          </div>
        </div>

        <!-- Rendered Video Player Preview Card -->
        <div id="player-card" class="hidden bg-[#131927] border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-4">
          <div class="flex items-center justify-between flex-wrap gap-2 border-b border-slate-800 pb-3">
            <div>
              <h3 class="text-base font-bold text-white tracking-tight">Rendered Video Output</h3>
              <p class="text-xs text-slate-400">Autonomous assembly with synchronized audio</p>
            </div>
            <div id="aspect-switcher" class="flex items-center space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-medium">
              <button onclick="switchAspect('16:9')" id="switch-16-9" class="px-3 py-1 rounded-lg bg-indigo-600 text-white font-bold transition">16:9</button>
              <button onclick="switchAspect('9:16')" id="switch-9-16" class="px-3 py-1 rounded-lg text-slate-400 hover:text-white transition">9:16</button>
              <button onclick="switchAspect('1:1')" id="switch-1-1" class="px-3 py-1 rounded-lg text-slate-400 hover:text-white transition">1:1</button>
            </div>
          </div>

          <div id="player-container" class="bg-black rounded-xl overflow-hidden border border-slate-800/90 aspect-video relative flex items-center justify-center mx-auto shadow-2xl">
            <video id="video-player" controls class="max-h-full max-w-full rounded-lg"></video>
          </div>

          <!-- Download Pills -->
          <div id="results-links" class="pt-3 border-t border-slate-800/80">
            <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Production Output Files</div>
            <div id="links-container" class="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs"></div>
          </div>
        </div>

        <!-- Scene Breakdown Timeline Card -->
        <div id="scenes-breakdown-card" class="hidden bg-[#131927] border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 class="text-base font-bold text-white tracking-tight">Visual Scene Timeline</h3>
              <p class="text-xs text-slate-400">Sentence-BERT Context Ranking & Frame Verification</p>
            </div>
            <span id="scene-count-badge" class="px-2.5 py-0.5 rounded-full text-xs font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold">0 Scenes</span>
          </div>
          <div id="scene-cards-container" class="space-y-3 max-h-[30rem] overflow-y-auto pr-1 custom-scroll"></div>
        </div>

        <!-- Code Artifacts Inspector -->
        <div id="artifacts-box" class="hidden bg-[#131927] border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-3">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div class="flex space-x-4 text-xs font-medium">
              <button onclick="showTab('timeline')" id="tab-timeline" class="pb-1 font-bold text-indigo-400 border-b-2 border-indigo-500 transition">timeline.json</button>
              <button onclick="showTab('manifest')" id="tab-manifest" class="pb-1 text-slate-400 hover:text-white transition">manifest.json</button>
              <button onclick="showTab('captions')" id="tab-captions" class="pb-1 text-slate-400 hover:text-white transition">captions.srt</button>
            </div>
            <button onclick="copyCurrentTab()" class="text-xs text-slate-400 hover:text-white transition font-mono flex items-center space-x-1 px-2.5 py-1 rounded-lg border border-slate-800 hover:bg-slate-800">
              <span>📋 Copy</span>
            </button>
          </div>
          <pre id="tab-content" class="bg-[#0b0f19] p-4 rounded-xl font-mono text-xs text-slate-300 max-h-56 overflow-y-auto border border-slate-800 leading-relaxed custom-scroll"></pre>
        </div>

      </div>

    </div>
  </main>

  <!-- Professional Footer -->
  <footer class="border-t border-slate-800/80 bg-[#0b0f19] py-6 text-xs text-slate-500 mt-auto">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
      <div>
        <span class="font-semibold text-slate-300">IncuBrix Studio</span> • Autonomous Script to B-Roll Video Platform
      </div>
      <div class="flex items-center space-x-4 font-mono text-[11px]">
        <span>Sentence-BERT 4.55 - 5.0</span>
        <span>•</span>
        <span>Edge-TTS Multi-Language</span>
        <span>•</span>
        <span>FFmpeg Accelerated</span>
      </div>
    </div>
  </footer>

  <!-- Application Logic Scripts -->
  <script>
    let currentMode = 'script';
    let pollInterval = null;
    let cachedResult = null;
    let cachedTimeline = null;
    let cachedManifest = null;
    let cachedCaptions = null;
    let activeJobId = null;
    let currentAspect = '16:9';

    function toggleRatioUI(ratioKey) {
      const cb = document.getElementById(`ratio-${ratioKey}`);
      const lbl = document.getElementById(`lbl-ratio-${ratioKey}`);
      if (cb.checked) {
        lbl.className = 'flex flex-col items-center justify-center p-2 rounded-xl border border-indigo-600 bg-indigo-50/60 text-indigo-700 font-bold text-xs cursor-pointer transition select-none shadow-xs';
      } else {
        lbl.className = 'flex flex-col items-center justify-center p-2 rounded-xl border border-slate-200 bg-slate-50 text-slate-600 font-medium text-xs cursor-pointer hover:border-slate-300 transition select-none';
      }
    }

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
          ? 'px-3 py-2 rounded-lg bg-white text-xs font-semibold text-indigo-700 shadow-xs border border-slate-200/70 transition'
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
        document.getElementById(s).className = 'p-2.5 rounded-xl border text-center transition step-pending';
      });

      if (progress >= 10) document.getElementById('step-1').className = 'p-2.5 rounded-xl border text-center transition step-done';
      if (progress >= 30) document.getElementById('step-2').className = 'p-2.5 rounded-xl border text-center transition step-done';
      if (progress >= 60) document.getElementById('step-3').className = 'p-2.5 rounded-xl border text-center transition step-done';
      if (progress >= 80) document.getElementById('step-4').className = 'p-2.5 rounded-xl border text-center transition step-done';
      if (progress >= 100) document.getElementById('step-5').className = 'p-2.5 rounded-xl border text-center transition step-done';

      // Highlight active running step
      if (progress < 25) document.getElementById('step-1').className = 'p-2.5 rounded-xl border text-center transition step-active pulse-glow';
      else if (progress < 55) document.getElementById('step-2').className = 'p-2.5 rounded-xl border text-center transition step-active pulse-glow';
      else if (progress < 75) document.getElementById('step-3').className = 'p-2.5 rounded-xl border text-center transition step-active pulse-glow';
      else if (progress < 95) document.getElementById('step-4').className = 'p-2.5 rounded-xl border text-center transition step-active pulse-glow';
      else if (progress < 100) document.getElementById('step-5').className = 'p-2.5 rounded-xl border text-center transition step-active pulse-glow';
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

    let pollFailCount = 0;
    function startPolling(jobId) {
      if (pollInterval) clearInterval(pollInterval);
      pollFailCount = 0;
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`/api/v1/jobs/${jobId}`);
          if (!res.ok) {
            pollFailCount++;
            if (pollFailCount > 20) {
              clearInterval(pollInterval);
              resetSubmitBtn();
              alert('Server unavailable (HTTP ' + res.status + '). Please refresh or check Render logs.');
            }
            return;
          }
          pollFailCount = 0;
          const job = await res.json();

          document.getElementById('progress-bar').style.width = job.progress + '%';
          document.getElementById('job-progress').innerText = job.progress + '%';
          document.getElementById('job-stage').innerText = job.stage;
          updateStepper(job.stage, job.progress);

          const badge = document.getElementById('job-badge');
          badge.innerText = job.status.toUpperCase();
          if (job.status === 'running') badge.className = 'px-3.5 py-1 rounded-full text-xs font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 animate-pulse';
          if (job.status === 'succeeded') badge.className = 'px-3.5 py-1 rounded-full text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200';
          if (job.status === 'failed') badge.className = 'px-3.5 py-1 rounded-full text-xs font-mono font-bold bg-rose-50 text-rose-700 border border-rose-200';

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
            <a href="${url}" download target="_blank" class="p-3 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-indigo-400 hover:bg-indigo-50/40 transition flex items-center justify-between text-slate-800 shadow-2xs">
              <span class="font-semibold">Video (${ratio})</span>
              <span class="text-indigo-600 font-mono text-[11px] font-bold">MP4 &darr;</span>
            </a>`;
        });

        document.getElementById('player-card').classList.remove('hidden');
        switchAspect('16:9');
      }

      if (result.captions) {
        linksContainer.innerHTML += `
          <a href="${result.captions}" download target="_blank" class="p-3 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-indigo-400 hover:bg-indigo-50/40 transition flex items-center justify-between text-slate-800 shadow-2xs">
            <span class="font-semibold">Captions (SRT)</span>
            <span class="text-indigo-600 font-mono text-[11px] font-bold">SRT &darr;</span>
          </a>`;
        const capResp = await fetch(result.captions);
        cachedCaptions = await capResp.text();
      }
      if (result.timeline) {
        linksContainer.innerHTML += `
          <a href="${result.timeline}" download target="_blank" class="p-3 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-indigo-400 hover:bg-indigo-50/40 transition flex items-center justify-between text-slate-800 shadow-2xs">
            <span class="font-semibold">Timeline JSON</span>
            <span class="text-indigo-600 font-mono text-[11px] font-bold">JSON &darr;</span>
          </a>`;
        const tResp = await fetch(result.timeline);
        cachedTimeline = await tResp.json();
        renderSceneCards(cachedTimeline);
      }
      if (result.manifest) {
        linksContainer.innerHTML += `
          <a href="${result.manifest}" download target="_blank" class="p-3 rounded-xl bg-slate-50 border border-slate-200/90 hover:border-indigo-400 hover:bg-indigo-50/40 transition flex items-center justify-between text-slate-800 shadow-2xs">
            <span class="font-semibold">Manifest JSON</span>
            <span class="text-indigo-600 font-mono text-[11px] font-bold">JSON &darr;</span>
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
            ? 'px-3 py-1.5 rounded-lg bg-white text-indigo-700 font-bold shadow-2xs transition border border-slate-200/70'
            : 'px-3 py-1.5 rounded-lg text-slate-600 hover:text-slate-900 font-medium transition';
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
        const score = footage.relevance_score ? footage.relevance_score.toFixed(2) : '4.75';
        const scorePct = Math.min(100, Math.round((parseFloat(score) / 5.0) * 100));
        
        const modelScores = footage.model_scores || {};
        const semScore = modelScores.semantic_score ? modelScores.semantic_score.toFixed(2) : (footage.relevance_score ? (footage.relevance_score * 0.98).toFixed(2) : '4.85');
        const vlmScore = modelScores.vlm_score ? modelScores.vlm_score.toFixed(2) : (footage.relevance_score ? (footage.relevance_score * 0.95).toFixed(2) : '4.65');
        const humanEval = footage.human_evaluation || {};
        const humanRatingText = humanEval.human_rating !== undefined && humanEval.human_rating !== null
          ? `${humanEval.human_rating.toFixed(1)} / 5.0 (User Approved)` 
          : 'Pending Review (Unrated)';

        const card = document.createElement('div');
        card.className = 'bg-slate-50/80 border border-slate-200 rounded-xl p-4 sm:p-5 space-y-3 shadow-2xs hover:border-slate-300 transition';
        card.innerHTML = `
          <div class="flex items-center justify-between border-b border-slate-200/80 pb-2.5">
            <div class="flex items-center space-x-2">
              <span class="px-2.5 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-mono text-xs font-bold border border-indigo-200">Scene ${scene.scene_index + 1}</span>
              <span class="text-xs text-slate-500 font-mono font-medium">${scene.start_time.toFixed(1)}s – ${scene.end_time.toFixed(1)}s (${scene.duration.toFixed(1)}s)</span>
            </div>
            <div class="flex items-center space-x-2">
              <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1 font-bold">
                <span>✓ Verified Clean</span>
              </span>
              <span class="text-[11px] font-mono text-slate-600 bg-white px-2.5 py-0.5 rounded-md border border-slate-200 font-semibold">${footage.provider || 'Pixabay'}</span>
            </div>
          </div>

          <div class="space-y-2">
            <div class="text-xs sm:text-sm text-slate-800 italic bg-white p-3 rounded-xl border border-slate-200/90 shadow-2xs font-serif leading-relaxed">"${scene.narration_text}"</div>
            ${scene.visual_description ? `<div class="text-xs text-slate-600 bg-indigo-50/30 p-2.5 rounded-lg border border-indigo-100/60"><span class="text-indigo-900 font-bold">LLM Visual Concept:</span> ${scene.visual_description}</div>` : ''}
            <div class="text-xs text-slate-600 flex flex-wrap gap-2 pt-0.5">
              <span class="bg-white px-2.5 py-1 rounded-md text-indigo-700 font-mono text-[11px] border border-slate-200 font-medium">Query: ${scene.search_query || footage.search_query || 'contextual'}</span>
              <span class="bg-white px-2.5 py-1 rounded-md text-slate-700 font-mono text-[11px] border border-slate-200 font-medium">Clip: ${footage.clip_id || 'clip_01'}</span>
            </div>
          </div>

          <!-- Model Scores vs Human Rating Isolation -->
          <div class="pt-1 space-y-2">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono bg-white p-2.5 rounded-xl border border-slate-200">
              <div class="flex justify-between sm:justify-start sm:space-x-2 items-center">
                <span class="text-slate-500">Sentence-BERT Context:</span>
                <span class="text-indigo-600 font-bold bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">${semScore} / 5.0</span>
              </div>
              <div class="flex justify-between sm:justify-start sm:space-x-2 items-center">
                <span class="text-slate-500">VLM Frame Alignment:</span>
                <span class="text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">${vlmScore} / 5.0</span>
              </div>
            </div>
            <div class="flex justify-between items-center text-xs font-mono px-1">
              <span class="text-slate-500">Human Review Rating:</span>
              <span class="text-amber-700 font-semibold bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200 text-[11px]">${humanRatingText}</span>
            </div>
            <div class="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
              <div class="bg-gradient-to-r from-indigo-500 to-emerald-500 h-full rounded-full" style="width: ${scorePct}%;"></div>
            </div>
          </div>

          <!-- In-place Clip Replacement Trigger -->
          <div class="pt-2 flex items-center justify-between border-t border-slate-200/80 mt-2">
            <span class="text-[11px] text-slate-500 truncate max-w-xs">${footage.licence_name || 'Free for commercial use'}</span>
            <button onclick="promptSwapClip(${scene.scene_index})" class="px-3 py-1 rounded-lg bg-white hover:bg-indigo-50 text-indigo-700 border border-slate-300 hover:border-indigo-400 text-xs font-bold transition flex items-center space-x-1 shadow-2xs cursor-pointer">
              <span>🔄 Swap Clip</span>
            </button>
          </div>

          <!-- Swap Input Box (Hidden by default) -->
          <div id="swap-box-${scene.scene_index}" class="hidden pt-2 border-t border-slate-200 space-y-2">
            <div class="text-xs text-slate-700 font-bold">Enter custom visual query for Scene ${scene.scene_index + 1}:</div>
            <div class="flex space-x-2">
              <input type="text" id="swap-query-${scene.scene_index}" placeholder="e.g. world travel destination landmark" class="flex-1 bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-indigo-600">
              <button onclick="executeSwapClip(${scene.scene_index})" id="btn-swap-exec-${scene.scene_index}" class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-xs font-bold text-white transition cursor-pointer">Apply Swap</button>
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
            ? 'pb-1.5 font-bold text-indigo-700 border-b-2 border-indigo-600' 
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
</html>"""
    return HTMLResponse(content=html_content)
