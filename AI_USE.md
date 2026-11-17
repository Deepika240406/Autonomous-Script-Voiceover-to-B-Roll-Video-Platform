# AI Coding Assistant Disclosure — AI_USE.md

In compliance with IncuBrix Engineering Assessment guidelines ("Disclose everything: List every AI coding tool you used and for what in AI_USE.md"), this document records all AI tooling, models, and workflows employed during development.

---

## 1. AI Coding Assistants & Models Used

| Assistant / Environment | Underlying Model | Primary Responsibilities & Contributions |
| :--- | :--- | :--- |
| **Antigravity IDE Assistant** | **Gemini 3.8 Flash** | Architecture design, test-driven development implementation, FFmpeg filter pipeline generation, error handler contracts, test fixtures, and batch runner automation. |
| **GitHub Copilot / VS Code** | Claude 3.5 Sonnet / GPT-4o | Boilerplate autocompletion, docstrings, schema validation checks. |

---

## 2. Specific Contributions & Engineering Traceability

1. **System Architecture & OpenAPI Contract**:
   - Designed modular FastAPI directory layout with clean separation between providers, domain models, services, storage, and API routes.
   - Enforced IncuBrix error payload schema `{"error": {"code", "message", "retryable", "details"}}` and uppercase snake_case formatting across all endpoints.

2. **Semantic Scene Segmentation & Disambiguation**:
   - Implemented hard-case context analyzers for ambiguous keywords (`bank`, `cloud`, `mouse`, `python`, `value`).
   - Built safety mitigations for real named people (preventing deepfake/likeness synthesis) and sensitive tragic news (ensuring dignified symbolic visuals).

3. **FFmpeg Video Normalization & 9:16 Composite**:
   - Formulated complex filtergraph for intelligent portrait 9:16 cropping:
     `[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2`
   - Configured exact duration trimming, loop expansion, and audio-video timestamp synchronization.

4. **Reliability & Idempotency**:
   - Developed memory-backed TTL idempotency store guaranteeing zero duplicate job executions for identical `Idempotency-Key` headers.
   - Built HMAC-SHA256 signature generator for `X-IncuBrix-Signature` webhooks.

5. **Test Pack & Verification**:
   - Authored 24 comprehensive test cases across unit, integration, e2e, and 5 hidden test categories.
   - Developed `scripts/batch_runner.py` for automated polling, downloading, and metrics reporting across all 10 Core fixtures.

---

## 3. Human Engineering Accountability
All AI-generated code was actively reviewed, tested against live FFmpeg builds on Windows, debugged (including cross-platform path escaping, event loop queue initialization, and file-handle concurrency), and verified by the candidate.
The candidate can explain, trace, debug, and modify any component of this repository during the 60–90 minute technical live evaluation.
