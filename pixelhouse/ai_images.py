"""No paid endpoint: run a pinned, ungated OpenRAIL model on the local CPU."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

MODEL = "Lykon/absolute-reality-1.81"
REVISION = "569d201654dca1426f1e090fca3953acc7db2c30"


def generate(post, output):
    # Imported in the isolated generation process only, never in ordinary posting jobs.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import torch
    from diffusers import StableDiffusionPipeline, DEISMultistepScheduler
    torch.set_num_threads(min(4, os.cpu_count() or 2))
    flags = Path("/proc/cpuinfo").read_text() if Path("/proc/cpuinfo").exists() else ""
    limit_path = Path("/sys/fs/cgroup/memory.max")
    limit_text = limit_path.read_text().strip() if limit_path.exists() else "max"
    limit = int(limit_text) if limit_text.isdigit() else 16 * 1024**3
    # Prefer native BF16; use FP32 on roomy CPUs without BF16 instructions.
    # FP16 can be very slow on CPU hardware lacking AVX512-FP16.
    dtype = torch.bfloat16 if "avx512_bf16" in flags or "amx_bf16" in flags or limit < 12 * 1024**3 else torch.float32
    print("CPU landscape generation dtype: " + str(dtype), flush=True)
    pipe = StableDiffusionPipeline.from_pretrained(
        MODEL, revision=REVISION, variant="fp16", torch_dtype=dtype,
        use_safetensors=True, low_cpu_mem_usage=True,
    )
    pipe.scheduler = DEISMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.enable_attention_slicing("auto")
    pipe.set_progress_bar_config(disable=True)
    prompt = ("Professional natural travel landscape photograph, " + post["destination"]["scene"] +
              ", realistic fine foliage and water, atmospheric depth, beautiful natural light, restrained colours, documentary-style camera optics, detailed photography, empty landscape")
    negative = "painting, illustration, drawing, anime, cartoon, CGI, 3d render, oversaturated, text, watermark, logo, people, crowds, animals, camera equipment, distorted geometry, blurry, low detail"
    def progress(pipeline, step, timestep, tensors):
        if step % 5 == 0:
            print(f"AI landscape step {step + 1}/20", flush=True)
        return tensors
    result = pipe(prompt, negative_prompt=negative, width=512, height=768,
                  num_inference_steps=20, guidance_scale=7.0, callback_on_step_end=progress,
                  generator=torch.Generator(device="cpu").manual_seed(post["design_seed"]))
    if result.nsfw_content_detected and any(result.nsfw_content_detected):
        raise RuntimeError("Image did not pass the model's safety check.")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.images[0].save(destination, "PNG")
    print("Generated an original AI landscape with the pinned CPU model.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--post", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate(json.loads(Path(args.post).read_text()), args.output)
