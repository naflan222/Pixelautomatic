# Varied Pixelhouse content

The daily image job and every-third-day video job now create more than product ads. Facebook and Instagram use the same existing authorized accounts and durable publication ledger.

## Daily image rotation

The cycle counts calendar days from `start_date` in Asia/Colombo:

1. Product spotlight using a genuine, verified in-stock product photograph.
2. Camera/photography tip with an original educational illustration.
3. A realistic-looking AI-generated Sri Lanka-inspired landscape.
4. Camera explanation: exposure, ISO, focal length, sensor, aperture or stabilisation.
5. Accessory explanation, using the actual product photograph and store-listed details.
6. A labeled conceptual exploded-view illustration explaining generic camera anatomy.
7. Product spotlight, then the cycle repeats with different products/topics.

Video days use a three-category offset so the daily image and video do not repeat the same category. The configured video cadence and posting times are unchanged. Old configurations without `content_rotation` retain product-only behavior; this repository's config explicitly enables all six categories.

Content is chosen from a reviewed library of original educational copy and illustrations. Least-used/oldest-used topics are preferred. The library is finite and can be expanded by adding reviewed lessons to `pixelhouse/content.py`; no paid language model is used. Date-stamped educational artwork prevents byte-identical reposts while preserving consistent explanations.

## Realistic Sri Lankan scenes without paid API keys

`ai_image.provider: local_cpu` runs a pinned open-weight model directly in the GitHub runner. It does not call a paid generation endpoint. The model is AbsoluteReality v1.81 by Lykon, pinned at revision `569d201654dca1426f1e090fca3953acc7db2c30`. Its model card declares CreativeML OpenRAIL-M. Model weights are fetched from Hugging Face with safetensors, not committed into this repository. Respect the upstream license and use restrictions.

- Model card: https://huggingface.co/Lykon/absolute-reality-1.81
- OpenRAIL-M reference: https://huggingface.co/spaces/CompVis/stable-diffusion-license
- Code and pinned model details: `pixelhouse/ai_images.py`.

First generation downloads several GB of public weights. The workflow caches them for later runs. CPU generation is slower than a paid GPU API and output quality varies. The base scene is 512×768 and is composed into 1080×1350 / 1080×1920 branded JPEGs. This is not a promise of native high-resolution camera photography or photographic accuracy of a landmark.

Destinations rotate among Ella, Mirissa, Sigiriya, Tangalle, Nuwara Eliya and Yala. Prompts focus on natural scenery, without people, animals, news events or product demonstrations. Images and captions explicitly say the scene is **AI-generated inspiration**, not a photograph of an actual place/event. They must never be presented as genuine customer footage.

To disable CPU generation, set `ai_image.provider` to `disabled`. AI generation has a bounded timeout. If the provider/dependencies/network are unavailable, the process fails its safety check or the result is blank, the unused draft becomes a camera-tip illustration. Its caption, topic and AI status are changed to match the real fallback, and its reason is recorded. The workflow never labels a vector fallback as a real Sri Lankan scene.

The model runs in a separate process without the Facebook/Instagram/GitHub application tokens. The regular publishing process keeps the credentials needed for official API requests. Generation does not transmit those tokens to the model host.

## Camera tips and explanations

Topics include intentional horizons, motion/shutter duration, depth of field, white balance, highlight clipping, shot sequences, exposure, ISO, focal length, image formation and stabilisation. Illustrations are original programmatic artwork with Pixelhouse branding and readable overlaid text. Settings and results are clearly illustrative; examples are not universal prescriptions.

In particular, ISO is not described as increasing the physical light captured by a sensor. Depth-of-field comparisons state the conditions that matter. Compatibility and stabilisation features are not attributed to a specific product without source information.

Source references live in each post's metadata. Captions contain only `pixelhouse.lk` as the website, as requested; no product links or external reference links are appended to captions.

## Accessory explanations

Only positively verified in-stock accessories are selected. The product photograph and short suitable description come from Pixelhouse's catalog. Exact model/mount compatibility must be checked against the manufacturer. These educational posts omit prices and sales urgency. Live product facts, including description changes, are still checked before final publication.

## Exploded views

These are original, **conceptual**, simplified educational illustrations of a generic camera's functional components: lens, aperture, shutter where fitted, sensor, processor and display. They are **not** a verified teardown of a GoPro/DJI/Insta360 or another specific model, are not to scale, and are not assembly/repair instructions. Layouts separate components to explain functions, not exact placement inside a camera. This distinction appears on the artwork and in the caption.

## Publishing and AI disclosure

All categories use the existing safe official publishing adapters and daily-slot duplicate protection. Instagram media creation includes its documented `is_ai_generated` self-disclosure field for generated scenes. Facebook Reels finish requests include the same documented disclosure field. Generated photos carry a discreet image/caption disclosure; the large top badge has been removed. No undocumented Facebook photo-label field is assumed.

Technical illustrations are labeled educational/conceptual rather than fake product demonstrations. No unlicensed music, testimonials, discounts, bestseller claims or current-trend claims are introduced.

## Preview without publishing

Actions → **Pixelhouse Facebook + Instagram** → Run workflow → command `preview` → choose `topic` and `kind`. Preview does not publish or modify the posting ledger. Leave topic `auto` to preview the scheduled mix. CPU dependencies/weights are installed only for a travel preview/publication when enabled.

Actions → **Preview varied content gallery** creates all six categories as downloadable files and captions in the `pixelhouse-varied-content-gallery` artifact. It never receives social credentials or publishes. The initial request marker `automation/request-content-preview.json` triggers one gallery build when added/updated on main. Re-running it is a preview operation, not a request to post six extra items.

The ordinary test workflow uses camera-tip and camera-explainer previews, so routine CI does not download heavy model weights. Unit tests mock AI and social APIs. A live model sample and the gallery workflow are separate checks.

## Operating limits

Public GitHub runner and cache policies still apply. This uses no paid model API and configures no paid runner, but it is not unlimited GPU hosting. Watch Actions status and cache/storage use. A paused automation switch continues to block posting. Existing published slots are never reset just because the content mix changes; the new categories appear in upcoming scheduled slots.

## Presentation update

Educational artwork prioritises larger diagrams with three concise takeaway cards; full explanations stay in captions. Videos use five four-second chapters, readable teaching points and an end card, exported as 1080×1920 H.264 at 30 FPS. They remain motion graphics, not generated live-action video. Topic-specific discovery hashtags rotate without claims of current trends or guaranteed viral performance. Captions retain only pixelhouse.lk as their website.

## Shared studio renderer and sound

All product, educational and accessory templates use shared layered studio lighting, texture and a rotating palette. Travel photos retain their full-bleed scene. Aperture and shutter lessons use richer original optical/light-trail illustrations; they remain conceptual rather than real camera test results. Video scenes retain sharp subject visuals, subtle frame movement, source branding, readable text and a closing screen. Every new video receives a seeded, original synthesized ambient instrumental score (pads, bass, soft percussion and plucks), faded in/out and exported as stereo AAC. No copyrighted recordings or trending songs are downloaded. This is a free motion-graphics renderer, not a cinematic live-action video generator, and visual quality still depends on source photographs. Existing published media is not changed.
