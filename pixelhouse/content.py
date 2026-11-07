"""Reviewed educational topics and a varied, deterministic daily content calendar."""
from __future__ import annotations

import hashlib
from datetime import date

from .captions import source_summary
from .core import AutomationError, plan, products, select_product, utc_now

TOPICS = ("product", "camera_tip", "travel", "camera_explainer", "accessory_explainer", "exploded_view")
DEFAULT_ROTATION = ["product", "camera_tip", "travel", "camera_explainer", "accessory_explainer", "exploded_view", "product"]
EXPOSURE_SOURCE = "https://www.cambridgeincolour.com/tutorials/camera-exposure.htm"
LENS_SOURCE = "https://www.cambridgeincolour.com/tutorials/camera-lenses.htm"
SENSOR_SOURCE = "https://www.cambridgeincolour.com/tutorials/camera-sensors.htm"


def lesson(id, title, summary, cards, diagram, source=EXPOSURE_SOURCE):
    return {"id": id, "title": title, "summary": summary, "cards": cards, "diagram": diagram,
            "sources": [source], "disclosure": "Simplified educational illustration; settings are examples, not universal recommendations."}


TIPS = [
    lesson("steady-horizon", "Keep your horizon intentional", "A level horizon can make a landscape feel more balanced. Use your camera's grid or electronic level, then check the edges before recording.",
           [("Enable the grid", "Use guide lines to check alignment."), ("Check the edges", "Watch for an accidental tilted horizon."), ("Choose your angle", "A deliberate tilt can still be creative.")], "composition", LENS_SOURCE),
    lesson("freeze-motion", "Choose how motion looks", "A shorter exposure can freeze movement; a longer exposure records more movement as blur. The right shutter speed depends on the subject, focal length and how steadily the camera is held.",
           [("Short exposure", "Can preserve detail in moving subjects."), ("Long exposure", "Can turn movement into a visible trail."), ("Test a frame", "Adjust for the movement in your scene.")], "shutter"),
    lesson("depth", "Give your subject room to stand out", "For the same lens, framing and focus distance, a wider aperture usually gives a shallower depth of field. Subject distance and background distance also affect the result.",
           [("Wider aperture", "Lower f-number; shallower depth of field."), ("Watch distance", "Separate your subject from the background."), ("Check focus", "Make sure the important detail is sharp.")], "aperture", "https://www.cambridgeincolour.com/tutorials/depth-of-field.htm"),
    lesson("white-balance", "Take control of colour", "White balance changes how the camera renders the colour of light. Use a suitable preset or a neutral reference for consistency, or choose a deliberate creative colour cast.",
           [("Read the light", "Daylight and indoor light can differ."), ("Set a reference", "A neutral target can help consistency."), ("Be consistent", "Match settings across related clips.")], "white_balance", "https://www.cambridgeincolour.com/tutorials/white-balance.htm"),
    lesson("highlights", "Protect the detail that matters", "Check the histogram and highlight warning when your camera provides them. Reduce exposure if important highlights are clipping; bright reflections may still be intentionally clipped.",
           [("Check warnings", "Look for lost important highlight detail."), ("Adjust exposure", "Protect detail you want to keep."), ("Review the shot", "Not every bright reflection needs detail.")], "histogram"),
    lesson("shot-sequence", "Build a story in three frames", "Try a wide view to establish the scene, a medium frame for the subject and a close-up for detail. This is a storytelling exercise, not a rule for every sequence.",
           [("Wide", "Show the setting and context."), ("Medium", "Introduce the subject or activity."), ("Close", "Bring attention to a useful detail.")], "framing", LENS_SOURCE),
]

EXPLAINERS = [
    lesson("exposure-triangle", "Understand the exposure triangle", "Aperture and shutter duration affect how much light is recorded. ISO influences image brightness and the camera's signal processing; raising ISO does not make the sensor collect more photons.",
           [("Aperture", "Changes the size of the lens opening."), ("Shutter duration", "Changes the time light is recorded."), ("ISO", "Changes brightness and processing choices.")], "triangle"),
    lesson("iso", "What ISO really changes", "At fixed aperture and shutter duration, increasing ISO usually brightens the rendered image. It does not add captured light. Noise depends on exposure and the camera's design and processing.",
           [("Captured light", "Set by the scene, aperture and duration."), ("ISO setting", "Influences gain and image rendering."), ("Practical choice", "Balance exposure, motion and noise.")], "iso"),
    lesson("focal-length", "Focal length and your frame", "For the same sensor size, a shorter focal length gives a wider angle of view; a longer focal length narrows it. Perspective also depends on where you place the camera.",
           [("Shorter lens", "Includes a wider view on the same sensor."), ("Longer lens", "Narrows the view on the same sensor."), ("Camera position", "Moving the camera changes perspective.")], "field_of_view", LENS_SOURCE),
    lesson("sensor", "From light to an image", "A digital camera's sensor converts light into electrical signals. Processing turns that information into an image; RAW formats, where supported, retain sensor data for later processing.",
           [("Lens", "Directs and focuses incoming light."), ("Sensor", "Converts light into electrical signals."), ("Processor", "Interprets data for the output image.")], "optical_path", SENSOR_SOURCE),
    lesson("aperture", "Why f-numbers work backwards", "The f-number relates focal length to the diameter of the entrance pupil. A smaller f-number represents a wider opening relative to focal length; it is not a direct measurement in millimetres.",
           [("Smaller f-number", "Wider relative lens opening."), ("Larger f-number", "Narrower relative lens opening."), ("Exposure", "Balance with shutter duration and ISO.")], "aperture", LENS_SOURCE),
    lesson("stabilisation", "Stabilisation has different forms", "Some systems move lens elements, some move the sensor, and some use electronic processing or a crop. Support and effectiveness depend on the specific camera, lens and recording mode.",
           [("Optical", "May move elements inside a lens."), ("Sensor shift", "May move the sensor inside the body."), ("Electronic", "May process or crop the recorded image.")], "optical_path", LENS_SOURCE),
]

EXPLODED = [
    lesson("camera-layers", "Inside a camera: the main layers", "This conceptual exploded view separates a lens assembly, aperture, shutter, sensor, processor and display to explain their roles. It is not the internal design of a particular camera.",
           [("Light control", "Lens, aperture and shutter guide exposure."), ("Light capture", "The sensor converts incoming light to signals."), ("Image output", "Processing supports storage and display.")], "exploded", SENSOR_SOURCE),
    lesson("light-path", "Follow the light through a camera", "Light passes through the lens and aperture toward the sensor. A physical shutter may control exposure; electronic-shutter cameras can control it through sensor operation instead.",
           [("Lens + aperture", "Focus light and control the opening."), ("Exposure control", "Physical shutter when fitted; designs vary."), ("Sensor", "Turns light into electrical signals.")], "exploded", SENSOR_SOURCE),
    lesson("image-path", "What happens after light is captured?", "Sensor signals are processed and recorded, and an image can be shown on a display. This is a simplified functional sequence, not an assembly order or repair instruction.",
           [("Sensor", "Creates electrical signals from light."), ("Processor", "Handles image data and camera functions."), ("Display", "Shows a processed view of the image.")], "exploded", SENSOR_SOURCE),
]

DESTINATIONS = [
    {"id": "ella", "name": "Ella", "scene": "Sri Lankan hill country around Ella, rolling emerald tea-covered hills, layers of mist between tropical mountains, soft sunrise, quiet natural valley"},
    {"id": "mirissa", "name": "Mirissa", "scene": "Sri Lankan south coast inspired by Mirissa, palm-lined tropical beach, clear turquoise Indian Ocean, warm sunrise, gentle small waves, empty pristine shoreline"},
    {"id": "sigiriya", "name": "Sigiriya", "scene": "Sri Lankan landscape inspired by Sigiriya, distant massive isolated reddish granite rock above green forest, hazy golden dawn, tropical countryside, realistic natural scale"},
    {"id": "tangalle", "name": "Tangalle", "scene": "Sri Lankan coast inspired by Tangalle, long quiet curved sand beach, leaning coconut palms, clear Indian Ocean surf, natural late afternoon light"},
    {"id": "nuwara-eliya", "name": "Nuwara Eliya", "scene": "Sri Lankan highlands inspired by Nuwara Eliya, neat tea-covered slopes, natural low mist, subtle cool morning light, lush mountain valley"},
    {"id": "yala", "name": "Yala", "scene": "Sri Lankan dry-zone landscape inspired by Yala, golden grass, sparse tropical trees, distant low rocky hills, gentle evening sun, no animals or people"},
]


def rotation_topic(config, day, kind, requested="auto"):
    if requested != "auto":
        if requested not in TOPICS:
            raise AutomationError("Unsupported content topic.")
        return requested
    rotation = config.get("content_rotation", ["product"])
    if not rotation or any(t not in TOPICS for t in rotation):
        raise AutomationError("content_rotation contains an unsupported topic.")
    elapsed = max(0, (day - date.fromisoformat(config["start_date"])).days)
    return rotation[(elapsed + (3 if kind == "video" and len(rotation) > 1 else 0)) % len(rotation)]


def _choose(items, state, topic, day, kind):
    history = [p for p in state.get("posts", {}).values() if p.get("topic") == topic]
    def rank(item):
        uses = [p.get("slot", "") for p in history if p.get("creative_id") == item["id"]]
        tie = hashlib.sha256(f"{day}:{kind}:{topic}:{item['id']}".encode()).hexdigest()
        return len(uses), max(uses, default=""), tie
    return sorted(items, key=rank)[0]


def editorial_caption(post, language="en"):
    info = post["lesson"]
    lines = [info["title"], info["summary"]]
    lines.append("\n".join(f"• {heading}: {text}" for heading, text in info["cards"]))
    if post["topic"] == "travel":
        lines.append("AI-generated Sri Lanka-inspired scene. This is visual inspiration, not a photograph of an actual location or event.")
        tags = "#Pixelhouse #SriLankaTravel #TravelPhotography #AIArt"
    elif post["topic"] == "exploded_view":
        lines.append("Conceptual exploded-view illustration. Not model-specific, not to scale and not a repair guide. Camera designs vary.")
        tags = "#Pixelhouse #CameraExplained #PhotographyEducation #CameraAnatomy"
    elif post["topic"] == "accessory_explainer":
        lines.append("Check your exact camera and mounting interface against the manufacturer's compatibility information before buying or fitting accessories.")
        tags = "#Pixelhouse #CameraAccessories #CreatorTips #PhotographySriLanka"
    else:
        lines.append(info["disclosure"])
        tags = "#Pixelhouse #PhotographyTips #CameraExplained #PhotographySriLanka"
    footer = "Learn more with Pixelhouse."
    if language == "si":
        footer = "Pixelhouse සමඟ ඡායාරූපකරණය ගැන තව දැනගන්න."
    elif language == "mixed":
        footer = "ඔබේ next shoot එකට තවත් camera tips — Pixelhouse."
    discovery = {
        "travel": ["#LandscapePhotography", "#TravelInspiration", "#VisitSriLanka"],
        "camera_tip": ["#LearnPhotography", "#PhotographyTutorial", "#CreatorTips"],
        "camera_explainer": ["#CameraSettings", "#LearnPhotography", "#PhotographyTutorial"],
        "accessory_explainer": ["#CameraGear", "#Filmmaking", "#ContentCreation"],
        "exploded_view": ["#HowItWorks", "#CameraTechnology", "#LearnPhotography"],
    }[post["topic"]]
    index = post.get("design_seed", 0) % len(discovery)
    tags = " ".join(dict.fromkeys((tags + " " + discovery[index] + " " + discovery[(index + 1) % len(discovery)]).split()))
    lines.extend([footer + "\npixelhouse.lk", tags])
    return "\n\n".join(lines)


def editorial_post(item, topic, day, kind, language):
    seed = int(hashlib.sha256(f"{day}:{kind}:{topic}:{item['id']}".encode()).hexdigest()[:8], 16)
    post = {"slot": f"{day}-{kind}", "date": str(day), "kind": kind, "topic": topic,
            "creative_id": item["id"], "headline": item["title"], "hook": item["title"] if len(item["title"]) <= 50 else "Know your camera accessories.",
            "design_seed": seed, "product": None, "lesson": item, "sources": item["sources"],
            "ai_generated": topic == "travel", "created_at": utc_now(), "language": language}
    post["caption"] = editorial_caption(post, language)
    return post


def fallback_to_tip(post, reason):
    # Preserve slot, creation time and all publication state; only unused media is replaced.
    item = TIPS[post["design_seed"] % len(TIPS)]
    new = editorial_post(item, "camera_tip", date.fromisoformat(post["date"]), post["kind"], post.get("language", "en"))
    new.update(created_at=post["created_at"], requested_topic=post.get("requested_topic", post["topic"]), fallback_reason=reason)
    for key in ("publications",):
        if key in post:
            new[key] = post[key]
    post.clear()
    post.update(new)


def build_plan(config, state, day, kind, requested="auto"):
    topic = rotation_topic(config, day, kind, requested)
    language = config.get("language", "en")
    if topic in ("product", "accessory_explainer"):
        catalog = products()
        if topic == "accessory_explainer":
            catalog = [p for p in catalog if "accessor" in p.get("category", "").lower()]
        product = select_product(catalog, state, day, kind, config.get("excluded_product_ids", []))
        if topic == "product":
            post = plan(product, day, kind, language)
            post.update(topic="product", ai_generated=False)
            return post
        detail = source_summary(product) or "Review the store listing for this accessory's details and verify compatibility with your exact camera."
        item = lesson("accessory-" + product["id"], product["name"], detail,
                      [("Store-listed details", "Use the verified product listing."), ("Check compatibility", "Match camera model and mounting interface."), ("Fit correctly", "Follow the manufacturer's fitting instructions.")], "accessory", "https://pixelhouse.lk")
        post = editorial_post(item, topic, day, kind, language)
        post["product"] = product
        return post
    if topic == "travel":
        place = _choose(DESTINATIONS, state, topic, day, kind)
        item = lesson("travel-" + place["id"], place["name"] + ": imagine a new perspective",
                      "An imagined Sri Lankan landscape inspired by " + place["name"] + ". Use the light, layers and composition as inspiration for your own photography.",
                      [("Look for light", "Notice soft light and natural contrast."), ("Build depth", "Find a foreground, middle and background."), ("Tell a story", "Choose a view with a clear visual subject.")], "travel", "https://www.srilanka.travel/")
        item["id"] = place["id"]
        post = editorial_post(item, topic, day, kind, language)
        post["destination"] = place
        post["ai_image"] = config.get("ai_image", {"provider": "disabled"})
        return post
    library = TIPS if topic == "camera_tip" else EXPLAINERS if topic == "camera_explainer" else EXPLODED
    return editorial_post(_choose(library, state, topic, day, kind), topic, day, kind, language)
