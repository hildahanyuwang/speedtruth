"""
SpeedTruth, stage 2: automated ROAD-CONDITION classification via a vision LLM.

Reads a manifest of staged street images and asks a Claude vision model to read
each image's STATIC ROAD CONDITION (separation, footpath, roadside development,
genuine pedestrian mixing) and the Safe-System speed the visible condition
implies, the iRAP-style coding task, automated and repeatable. Output feeds a
CORRECTED safe-threshold that no longer relies only on the OSM POI buffer.

Validation: run it first on output/roadaudit_results.json (the 32 segments a
human rated blind) to measure model-vs-human agreement, then on the full sample.

Usage:
  ANTHROPIC_API_KEY=...  python src/streetview_cv_classify.py [manifest.json] [out.json]
Defaults: output/cv_manifest.json -> output/cv_labels.json
Model via CV_MODEL env (default claude-haiku-4-5-20251001).
"""
import os, sys, json, base64, time, urllib.request, urllib.error

API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("CV_MODEL", "claude-haiku-4-5-20251001")
MANIFEST = sys.argv[1] if len(sys.argv) > 1 else "output/cv_manifest.json"
OUTFILE = sys.argv[2] if len(sys.argv) > 2 else "output/cv_labels.json"

RUBRIC = (
 "You are auditing a road-safety dataset. From this SINGLE street-level image, classify the "
 "STATIC ROAD CONDITION (ignore transient traffic counts). Reply with ONLY one JSON object, no prose:\n"
 '{"road_visible": true|false,'
 ' "separation": "grade_separated"|"divided_barrier"|"undivided",'
 ' "footpath": "yes"|"no",'
 ' "roadside": "built_up"|"rural_open",'
 ' "pedestrian_environment": "genuine"|"light"|"none",'
 ' "implied_safe_speed_kmh": 30|50|70|110,'
 ' "confidence": "high"|"medium"|"low"}\n'
 "Guidance: grade_separated/divided_barrier with no footpath and no pedestrians => 70-110. "
 "Undivided road through dwellings/shops/markets, or a pedestrian crossing/footpath present, "
 "or people walking on/beside the carriageway => 30-50. Open rural undivided => 70. "
 "implied_safe_speed_kmh is the Safe System survivable speed the VISIBLE condition implies."
)

def classify(path):
    with open(path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode()
    body = json.dumps({
        "model": MODEL, "max_tokens": 300,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": RUBRIC},
        ]}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    for attempt in range(4):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=60))
            txt = r["content"][0]["text"].strip()
            s, e = txt.find("{"), txt.rfind("}")
            return json.loads(txt[s:e+1])
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError, ValueError) as ex:
            if attempt < 3:
                time.sleep(3 * (attempt + 1)); continue
            return {"error": str(ex)}

def main():
    manifest = json.load(open(MANIFEST))
    out = {}
    if os.path.exists(OUTFILE):
        out = json.load(open(OUTFILE))            # resume
    items = [(k, v) for k, v in manifest.items() if k not in out]
    print(f"Classifying {len(items)} images with {MODEL} (resuming {len(out)} done)…", flush=True)
    for i, (iid, m) in enumerate(items, 1):
        path = m.get("file")
        if not path or not os.path.exists(path):
            out[iid] = {**m, "cv": {"error": "no_image"}}; continue
        out[iid] = {**m, "cv": classify(path)}
        if i % 10 == 0:
            json.dump(out, open(OUTFILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"  {i}/{len(items)}", flush=True)
        time.sleep(0.3)
    json.dump(out, open(OUTFILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ok = sum(1 for v in out.values() if "error" not in v.get("cv", {}))
    print(f"Done. {ok}/{len(out)} classified -> {OUTFILE}")

if __name__ == "__main__":
    main()
