# IncuBrix B-Roll Video Engine — Sources and Commercial Licences

This document provides a comprehensive, honest disclosure of every model, API, library, and media provider used in this service, including verified commercial usability information per IncuBrix requirements.

---

## 1. AI Models & Algorithms

| Model / Architecture | Source & Authority | Version / Identifier | Commercial Licence | Permitted Use & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Whisper** | OpenAI / Hugging Face | `whisper-base` | **MIT Licence** | Commercial speech recognition and word timestamp extraction. |
| **Sentence-BERT** | UKPLab / Hugging Face | `all-MiniLM-L6-v2` | **Apache 2.0 Licence** | Contextual sentence embedding and semantic cosine similarity. |
| **Contextual IR Embedder** | IncuBrix Internal | v1.0.0 | **Proprietary / MIT Compatible** | Sub-word n-gram containment & asymmetric concept relevance scorer. |
| **Edge Neural TTS** | Microsoft Cognitive Speech (via edge-tts) | v7.3.1 | **MIT Licence (Tool) / Standard Speech Terms** | Synthetic voiceover generation with native word-boundary timestamps. Includes `en-IN`, `hi-IN`, `ta-IN`. |
| **Pyttsx3 TTS** | Nican / pyttsx3 community | v2.99 | **MPL 2.0 / LGPL Compatible** | 100% offline fallback TTS engine. |

---

## 2. Media & Stock Footage Sources

All video media utilized in the application default path adheres to commercial redistribution standards:

| Provider | Access Method | Licence Name | Terms Summary | AI-Generated Flag |
| :--- | :--- | :--- | :--- | :--- |
| **Pexels Video API** | REST API (`/videos/search`) | **Pexels Licence** | Free commercial use. No attribution required. Modification permitted. | `False` |
| **Pixabay Video API** | REST API (`/api/videos`) | **Pixabay Content Licence** | Free commercial use. Safe for digital publication without royalties. | `False` |
| **IncuBrix Verified Mock Library** | Local MP4 Asset Store | **IncuBrix Commercial Mock Licence** | Locally generated and owned video streams for zero-network testing. | Flagged per clip |
| **Procedural Video Generator** | FFmpeg procedural filtergraph | **CC0 / Public Domain Equivalent** | Programmatically synthesized HD gradient motion backdrops for 100% outage resilience. | `True` |

---

## 3. Core Software Libraries & Tools

| Library / Tool | Version | Role in Architecture | Licence |
| :--- | :--- | :--- | :--- |
| **FastAPI** | 0.109.0 | High-performance asynchronous API framework | MIT |
| **Uvicorn** | 0.27.0 | Lightning-fast ASGI web server | BSD 3-Clause |
| **FFmpeg & FFprobe** | 8.0.1 | Video scaling, cropping, normalization, subtitle burning, audio remuxing | LGPL v2.1+ / GPL v2+ |
| **Pydantic** | 2.11+ | Data validation and schema enforcement | MIT |
| **HTTPX** | 0.28.1 | Asynchronous HTTP client with SSRF protection & HMAC callbacks | BSD 3-Clause |
| **Boto3** | 1.42.38 | Amazon S3 / MinIO object storage client | Apache 2.0 |
| **Pytest** | 9.2.0 | Unit, integration, and end-to-end testing | MIT |

---

## 4. Licence Governance & Restrictions
1. **No Non-Commercial Footage**: No CC BY-NC or non-commercial research datasets are utilized in default generation pipelines.
2. **No Celebrity Likeness / Deepfakes**: Named public figures are intercepted by safety guardrails and mapped to neutral corporate or keynote imagery.
3. **No Watermarks**: All footage is sourced at high definition (1080p-class) without watermarks or stock logos.
