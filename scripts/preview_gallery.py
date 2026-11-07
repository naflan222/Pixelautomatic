"""Read-only previews: never uses social credentials or writes the posting ledger."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pixelhouse.core import load_config, local_day
from pixelhouse.content import TOPICS, build_plan
from run import render

config = load_config()
for topic in TOPICS:
    post = build_plan(config, {"posts": {}}, local_day(), "image", topic)
    file, _ = render(post, Path("output/gallery") / topic)
    print(f"{topic}: {file}", flush=True)
    if post.get("fallback_reason"):
        print("Generation fallback: " + post["fallback_reason"], flush=True)
