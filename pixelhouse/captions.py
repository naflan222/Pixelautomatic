"""Professional, factual caption templates without a paid generation API."""
from __future__ import annotations

import re
from html.parser import HTMLParser


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"p", "div", "li", "br", "ul", "ol"} and not self.hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        elif tag in {"p", "div", "li", "ul", "ol"} and not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean_description(value):
    if not isinstance(value, str) or len(value) > 10_000:
        return ""
    parser = _VisibleText()
    parser.feed(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", "".join(parser.parts))
    return " ".join(text.split())


# Price, scarcity, rankings, testimonials, fulfilment and warranty statements need
# separate verification. Do not reproduce these from decorative storefront copy.
_UNSUPPORTED = re.compile(
    r"\b(?:best[ -]?sell\w*|best|most|guarantee\w*|limited|sale|discount\w*|save|"
    r"free|warrant\w*|authentic|genuine|testimonial\w*|review\w*|rated|"
    r"shipping|delivery|stock|sold|lkr|rs\.?|usd)\b|[%$€£]|https?://|www\.",
    re.IGNORECASE,
)


def source_summary(product):
    text = clean_description(product.get("description", ""))
    comparable = lambda value: re.sub(r"\W+", "", value.casefold())
    # Keep the complete source text, including any compatibility caveats.
    # An overly long description is omitted rather than truncated into a claim.
    if not text or len(text) > 420 or _UNSUPPORTED.search(text):
        return ""
    if comparable(text) == comparable(product["name"]):
        return ""
    return text


def hashtags(product):
    name = product["name"].casefold()
    category = product.get("category", "").casefold()
    text = name + " " + category
    tags = ["#Pixelhouse"]
    tags.append("#ActionCameras" if "cameras" in category and "accessor" not in category else "#CameraAccessories")
    if "gopro" in text:
        tags.extend(["#GoProAccessories" if "accessor" in category else "#GoPro", "#GoProSriLanka"])
    elif "dji" in text or "osmo" in text:
        tags.extend(["#DJI", "#DJISriLanka"])
    elif "insta360" in text or "insta 360" in text:
        tags.extend(["#Insta360", "#ContentCreator"])
    else:
        tags.append("#ContentCreator")
    tags.append("#PhotographySriLanka")
    return " ".join(dict.fromkeys(tags))


_INTROS = [
    "Equip your next creative project.",
    "A fresh perspective starts with your setup.",
    "Make room for your next adventure.",
    "Discover your next camera essential.",
    "Your next story deserves a considered setup.",
    "Explore the details. Plan your next shoot.",
]
_CTAS = [
    "Explore product details and order online:",
    "View product details and current availability:",
    "Discover this product at Pixelhouse:",
]


def professional_caption(product, index, language):
    heading = _INTROS[index % len(_INTROS)]
    price_label = "Price"
    cta = _CTAS[(index // len(_INTROS)) % len(_CTAS)]
    brand = "Pixelhouse | Camera & video accessories in Sri Lanka."
    if language == "si":
        heading = "ඔබේ ඊළඟ නිර්මාණයට ගැළපෙන කැමරා උපකරණ."
        price_label = "මිල"
        cta = "නිෂ්පාදන විස්තර සහ ඇණවුම් සඳහා:"
        brand = "Pixelhouse | ශ්‍රී ලංකාවේ කැමරා සහ වීඩියෝ උපාංග."
    elif language == "mixed":
        heading = "ඔබේ next shoot එකට ගැළපෙන camera essentials."
        price_label = "Price / මිල"
        cta = "Product details සහ ඇණවුම් සඳහා:"
    paragraphs = [heading, product["name"]]
    description = source_summary(product)
    if description:
        paragraphs.append(description)
    else:
        paragraphs.append("Explore cameras and accessories for your next project with Pixelhouse.")
    price = product.get("price")
    if price is not None:
        formatted = f"{price:,.2f}" if price % 1 else f"{price:,.0f}"
        paragraphs.append(f"{price_label}: LKR {formatted}")
    paragraphs.extend([f"{cta}\n{product['url']}", brand, hashtags(product)])
    return "\n\n".join(paragraphs)
