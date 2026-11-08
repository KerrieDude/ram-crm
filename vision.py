"""Identifies furniture/objects in a photo using Google Cloud Vision's label
detection REST API. For junk-removal and moving quotes: snap a photo of a room
or a single piece and get back a list of likely item labels to cross-reference
against the inventory list.

Requires a Google Cloud Vision API key (GOOGLE_VISION_API_KEY env var / Streamlit
secret). Get one at https://console.cloud.google.com/apis/credentials after
enabling the Cloud Vision API on a project (it's pay-per-use after a free tier).
Without a key set, identify_items() returns an empty list with a clear reason
instead of crashing, so the rest of the app still works -- staff can tag items
by hand in the meantime.
"""
import base64
import os

import requests

VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


def api_key_configured() -> bool:
    return bool(os.environ.get("GOOGLE_VISION_API_KEY"))


def identify_items(image_bytes: bytes, max_results: int = 10):
    """Returns (labels, error). labels is a list of {"description", "score"} dicts."""
    key = os.environ.get("GOOGLE_VISION_API_KEY")
    if not key:
        return [], "No GOOGLE_VISION_API_KEY configured -- add one in Settings/secrets to enable this."

    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "requests": [{
            "image": {"content": b64},
            "features": [
                {"type": "LABEL_DETECTION", "maxResults": max_results},
                {"type": "OBJECT_LOCALIZATION", "maxResults": max_results},
            ],
        }]
    }
    try:
        resp = requests.post(f"{VISION_ENDPOINT}?key={key}", json=payload, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        return [], f"Vision API request failed: {e}"

    result = resp.json().get("responses", [{}])[0]
    if "error" in result:
        return [], f"Vision API error: {result['error'].get('message', 'unknown error')}"

    labels = [
        {"description": a["description"], "score": a["score"]}
        for a in result.get("labelAnnotations", [])
    ]
    objects = [
        {"description": o["name"], "score": o["score"]}
        for o in result.get("localizedObjectAnnotations", [])
    ]
    # Objects are usually more specific/useful for furniture; put them first.
    seen = set()
    combined = []
    for item in objects + labels:
        if item["description"].lower() not in seen:
            seen.add(item["description"].lower())
            combined.append(item)
    return combined[:max_results], None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vision.py <image_path>")
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        found, err = identify_items(f.read())
    if err:
        print("Error:", err)
    for item in found:
        print(f"{item['description']} ({item['score']:.2f})")
