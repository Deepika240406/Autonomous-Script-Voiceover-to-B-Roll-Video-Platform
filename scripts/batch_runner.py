import os
import sys
import json
import time
import argparse
import httpx
from typing import List, Dict, Any


def run_batch(input_path: str, api_url: str, output_dir: str, poll_interval: float = 2.0, max_wait: float = 300.0):
    os.makedirs(output_dir, exist_ok=True)
    api_url = api_url.rstrip("/")

    # Discover inputs
    items_to_run = []
    if os.path.isfile(input_path):
        if input_path.endswith(".json"):
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    items_to_run = data
                else:
                    items_to_run = [data]
        else:
            with open(input_path, "r", encoding="utf-8") as f:
                items_to_run = [{"script": f.read().strip(), "name": os.path.basename(input_path)}]
    elif os.path.isdir(input_path):
        for fname in sorted(os.listdir(input_path)):
            fpath = os.path.join(input_path, fname)
            if fname.endswith(".txt"):
                with open(fpath, "r", encoding="utf-8") as f:
                    items_to_run.append({"script": f.read().strip(), "name": fname})
            elif fname.endswith(".json"):
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        items_to_run.extend(data)
                    else:
                        items_to_run.append(data)
            elif any(fname.endswith(ext) for ext in [".mp3", ".wav", ".m4a"]):
                items_to_run.append({"audio_file_path": fpath, "name": fname})

    print(f"\n==================================================================")
    print(f" IncuBrix Batch Runner: Executing {len(items_to_run)} test inputs")
    print(f" Target API: {api_url}")
    print(f" Output Folder: {output_dir}")
    print(f"==================================================================\n")

    summary_results = []

    client = httpx.Client(timeout=30.0)

    for idx, item in enumerate(items_to_run, 1):
        item_name = item.get("name", f"test_input_{idx}")
        print(f"[{idx}/{len(items_to_run)}] Submitting '{item_name}'...")

        t_start = time.time()
        job_id = None
        status = "failed"
        error_info = None

        try:
            # Check if multipart upload or JSON
            if "audio_file_path" in item and os.path.exists(item["audio_file_path"]):
                fpath = item["audio_file_path"]
                with open(fpath, "rb") as af:
                    files = {"audio_file": (os.path.basename(fpath), af, "audio/mpeg")}
                    data = {"voice": item.get("voice", "en-IN-female")}
                    resp = client.post(
                        f"{api_url}/api/v1/jobs/upload",
                        files=files,
                        data=data,
                        headers={"Idempotency-Key": f"batch-{item_name}-{int(time.time())}"}
                    )
            else:
                payload = {
                    "script": item.get("script"),
                    "scenes": item.get("scenes"),
                    "audio_url": item.get("audio_url"),
                    "voice": item.get("voice", "en-IN-female"),
                    "aspect_ratios": item.get("aspect_ratios", ["16:9", "9:16"]),
                    "style": item.get("style", "bright, modern, real-world footage"),
                    "avoid": item.get("avoid", []),
                    "captions": item.get("captions", {"burn_in": True, "srt": True})
                }
                resp = client.post(
                    f"{api_url}/api/v1/broll/jobs",
                    json=payload,
                    headers={"Idempotency-Key": f"batch-{item_name}-{int(time.time())}"}
                )

            if resp.status_code != 202:
                print(f"   [!] Submission rejected: HTTP {resp.status_code} - {resp.text}")
                error_info = resp.text
                summary_results.append({
                    "name": item_name,
                    "status": "submission_error",
                    "error": error_info,
                    "elapsed_seconds": round(time.time() - t_start, 2)
                })
                continue

            resp_json = resp.json()
            job_id = resp_json["job_id"]
            print(f"   Job accepted: {job_id}. Polling execution...")

            # Polling loop
            poll_start = time.time()
            job_data = {}
            while time.time() - poll_start < max_wait:
                status_resp = client.get(f"{api_url}/api/v1/jobs/{job_id}")
                if status_resp.status_code == 200:
                    job_data = status_resp.json()
                    st = job_data.get("status")
                    prog = job_data.get("progress", 0)
                    stage = job_data.get("stage", "")
                    print(f"\r   Progress: {prog}% [{stage}]           ", end="", flush=True)

                    if st in ("succeeded", "failed"):
                        print()
                        status = st
                        break
                time.sleep(poll_interval)

            elapsed = round(time.time() - t_start, 2)

            if status == "succeeded":
                # Create destination folder for this job
                item_out_dir = os.path.join(output_dir, f"{idx:02d}_{item_name}")
                os.makedirs(item_out_dir, exist_ok=True)

                res = job_data.get("result", {})

                # Download video files
                videos = res.get("videos", {})
                for ratio, v_url in videos.items():
                    r_clean = ratio.replace(":", "_")
                    dest_v = os.path.join(item_out_dir, f"video_{r_clean}.mp4")
                    full_dl_url = v_url if v_url.startswith("http") else f"{api_url}{v_url}"
                    v_bytes = client.get(full_dl_url).content
                    with open(dest_v, "wb") as f:
                        f.write(v_bytes)

                # Download captions
                if res.get("captions"):
                    c_url = res["captions"]
                    full_c_url = c_url if c_url.startswith("http") else f"{api_url}{c_url}"
                    c_bytes = client.get(full_c_url).content
                    with open(os.path.join(item_out_dir, "captions.srt"), "wb") as f:
                        f.write(c_bytes)

                # Download timeline
                timeline_obj = {}
                if res.get("timeline"):
                    t_url = res["timeline"]
                    full_t_url = t_url if t_url.startswith("http") else f"{api_url}{t_url}"
                    t_bytes = client.get(full_t_url).content
                    with open(os.path.join(item_out_dir, "timeline.json"), "wb") as f:
                        f.write(t_bytes)
                    try:
                        timeline_obj = json.loads(t_bytes)
                    except Exception:
                        pass

                # Download manifest
                manifest_obj = {}
                if res.get("manifest"):
                    m_url = res["manifest"]
                    full_m_url = m_url if m_url.startswith("http") else f"{api_url}{m_url}"
                    m_bytes = client.get(full_m_url).content
                    with open(os.path.join(item_out_dir, "manifest.json"), "wb") as f:
                        f.write(m_bytes)
                    try:
                        manifest_obj = json.loads(m_bytes)
                    except Exception:
                        pass

                scenes = timeline_obj.get("scenes", [])
                avg_relevance = (
                    sum(s.get("selected_footage", {}).get("relevance_score", 0.0) for s in scenes) / len(scenes)
                ) if scenes else 0.0

                print(f"   [PASS] Completed in {elapsed}s | Scenes: {len(scenes)} | Avg Relevance: {avg_relevance:.2f}/5.0")

                summary_results.append({
                    "name": item_name,
                    "job_id": job_id,
                    "status": "succeeded",
                    "elapsed_seconds": elapsed,
                    "scenes_count": len(scenes),
                    "avg_relevance": round(avg_relevance, 2),
                    "cost_estimate_usd": manifest_obj.get("cost_estimates_usd", {}).get("total_estimated_usd", 0.0),
                    "warnings": manifest_obj.get("warnings_and_fallback_decisions", []),
                    "artifacts_folder": item_out_dir,
                })
            else:
                error_info = job_data.get("error") or "Job timed out or failed without details."
                print(f"   [FAIL] Job failed: {error_info}")
                summary_results.append({
                    "name": item_name,
                    "job_id": job_id,
                    "status": "failed",
                    "elapsed_seconds": elapsed,
                    "error": error_info
                })

        except Exception as e:
            print(f"   [EXCEPTION] {e}")
            summary_results.append({
                "name": item_name,
                "job_id": job_id,
                "status": "exception",
                "error": str(e)
            })

    # Save summary report
    summary_file = os.path.join(output_dir, "batch_summary_report.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, indent=2)

    md_summary = os.path.join(output_dir, "batch_summary_report.md")
    with open(md_summary, "w", encoding="utf-8") as f:
        f.write("# IncuBrix Batch Runner Execution Report\n\n")
        f.write(f"- Total jobs run: {len(summary_results)}\n")
        passed = sum(1 for r in summary_results if r.get("status") == "succeeded")
        f.write(f"- Passed: {passed} / {len(summary_results)}\n\n")
        f.write("| Input Name | Status | Time (s) | Scenes | Avg Relevance | Cost ($) |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
        for r in summary_results:
            st = r.get("status")
            badge = "PASSED" if st == "succeeded" else "FAILED"
            f.write(f"| {r.get('name')} | {badge} | {r.get('elapsed_seconds', '-')} | {r.get('scenes_count', '-')} | {r.get('avg_relevance', '-')} | {r.get('cost_estimate_usd', '-')} |\n")

    print(f"\n==================================================================")
    print(f" Batch run completed. Summary saved to:")
    print(f" JSON: {summary_file}")
    print(f" Markdown: {md_summary}")
    print(f"==================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IncuBrix B-Roll Engine Batch Runner")
    parser.add_argument("--input", required=True, help="Path to input test JSON file or directory")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Root URL of running IncuBrix API")
    parser.add_argument("--output-dir", default="./batch_results", help="Directory where results will be written")
    args = parser.parse_args()

    run_batch(args.input, args.api_url, args.output_dir)
