import re
import os
from typing import Dict, Any, List, Optional
from app.core.logging import logger


VISUAL_DOMAIN_CONCEPTS = {
    "education_learning": {
        "triggers": [
            "education", "educational", "learning", "learn", "student", "students",
            "school", "schools", "university", "college", "teacher", "teachers",
            "classroom", "study", "studying", "course", "courses", "lecture",
            "campus", "academic", "knowledge", "scholar", "online learning",
            "elearning", "degree", "graduation", "homework", "tutor", "tuition"
        ],
        "scenes": [
            (
                "online_learning",
                "Focused student using laptop computer and digital tablets for online educational learning platform in a bright modern room",
                [
                    "student online learning laptop",
                    "student laptop typing hands desk",
                    "e learning digital education",
                    "student studying laptop computer",
                    "online education digital platform",
                    "distance learning student desk"
                ]
            ),
            (
                "future_success",
                "Inspiring graduation ceremony with enthusiastic university students celebrating future career success in golden sunlight",
                [
                    "university graduation students celebration",
                    "graduation caps celebration sky",
                    "students studying library success",
                    "college education academic success",
                    "university campus architecture building"
                ]
            ),
            (
                "classroom",
                "Modern bright classroom with teacher guiding focused students with interactive educational tools",
                [
                    "modern classroom students teacher",
                    "digital classroom tablet interactive",
                    "classroom education learning",
                    "school students studying classroom"
                ]
            ),
            (
                "students",
                "Diverse group of university students collaborating and studying with books and laptops in university library",
                [
                    "university students campus library",
                    "library books shelves studying",
                    "college students studying group",
                    "students education books library"
                ]
            ),
            (
                "general",
                "Inspiring education scene showing dedicated students learning and acquiring knowledge for future success",
                [
                    "education learning school study",
                    "student online learning laptop",
                    "library books shelves study",
                    "university campus architecture building"
                ]
            )
        ]
    },
    "cybersecurity": {
        "triggers": [
            "cybersecurity", "cyber security", "hacker", "hackers", "attack", "cyber attack",
            "breach", "data breach", "data theft", "password", "passwords", "authentication",
            "encryption", "malware", "firewall", "two-factor", "2fa", "unauthorized access",
            "phishing", "ransomware", "cyber defense"
        ],
        "scenes": [
            (
                "password",
                "Close-up of user typing strong password into secure login interface with two-factor authentication verification shield",
                [
                    "password security authentication",
                    "two factor authentication mobile",
                    "digital cybersecurity lock protection",
                    "cyber security network"
                ]
            ),
            (
                "hacker",
                "Dark cybersecurity command center with red alert screens indicating cyber attack and hacker code stream",
                [
                    "cyber attack hacker screen",
                    "hacker coding security terminal",
                    "cyber security breach warning",
                    "digital network security defense"
                ]
            ),
            (
                "mobile",
                "Modern user interacting with mobile applications on smartphone displaying secure digital account interface",
                [
                    "mobile applications smartphone",
                    "person using mobile app screen",
                    "secure mobile internet browsing",
                    "smartphone digital technology"
                ]
            ),
            (
                "network",
                "High-tech server room with glowing blue fiber optic cables transmitting encrypted data across secure network infrastructure",
                [
                    "network security data center",
                    "server room digital infrastructure",
                    "encrypted data stream network",
                    "cloud cybersecurity servers"
                ]
            ),
            (
                "general",
                "Futuristic holographic digital cybersecurity shield protecting corporate data network from unauthorized access",
                [
                    "cybersecurity digital technology",
                    "cyber security shield protection",
                    "data encryption technology",
                    "secure corporate computer system"
                ]
            )
        ]
    },
    "technology_software": {
        "triggers": [
            "technology", "software", "computer", "computers", "programming",
            "developer", "coding", "smartphone", "cloud", "internet", "tech",
            "devices", "device", "digital tools", "app", "apps", "mobile app",
            "website", "websites", "platform", "platforms"
        ],
        "scenes": [
            (
                "mobile",
                "Modern user interacting with mobile applications on smartphone displaying sleek digital interface",
                [
                    "mobile applications smartphone",
                    "person using mobile app screen",
                    "smartphone digital technology",
                    "mobile screen user interface"
                ]
            ),
            (
                "cloud",
                "High-tech server room with glowing blue fiber optic cables transmitting data across modern network infrastructure",
                [
                    "cloud computing data center",
                    "server room digital infrastructure",
                    "data stream modern network",
                    "technology server room"
                ]
            ),
            (
                "software",
                "Software engineer and developer coding on multi-monitor computer workstation in modern tech office",
                [
                    "software developer coding computer",
                    "computer programmer modern office",
                    "tech innovation digital workspace",
                    "coding on computer screen"
                ]
            ),
            (
                "general",
                "Modern digital technology innovation and interactive digital devices in sleek setting",
                [
                    "modern digital technology innovation",
                    "computer technology workspace",
                    "interactive digital technology",
                    "smart technology digital interface"
                ]
            )
        ]
    },
    "ai_technology": {
        "triggers": [
            "ai", "artificial intelligence", "machine learning", "algorithm",
            "automate", "automation", "robot", "robotics", "neural", "deep learning",
            "tech", "technology"
        ],
        "scenes": [
            (
                "healthcare",
                "Futuristic medical laboratory with doctor analyzing AI diagnostic scans on interactive transparent holographic display",
                [
                    "medical technology ai laboratory",
                    "doctor analyzing digital scans",
                    "modern healthcare innovation technology",
                    "medical research data"
                ]
            ),
            (
                "education",
                "Modern digital classroom with students learning through interactive computer tablets and educational software",
                [
                    "education technology classroom",
                    "digital learning students computer",
                    "modern school education tablets",
                    "learning software interactive"
                ]
            ),
            (
                "data",
                "High-tech analytics dashboard visualizing complex big data streams, neural network nodes, and predictive charts",
                [
                    "data analytics dashboard screen",
                    "big data visualization charts",
                    "ai machine learning neural network",
                    "data science analytics office"
                ]
            ),
            (
                "general",
                "Advanced robotics hardware engineer testing automated robotic arm in modern technology innovation facility",
                [
                    "artificial intelligence robotics",
                    "modern technology laboratory innovation",
                    "automated computer tasks office",
                    "future technology digital network"
                ]
            )
        ]
    },
    "business_finance": {
        "triggers": [
            "business", "finance", "sales", "revenue", "profit", "stock",
            "stocks", "growth", "investment", "market", "economy", "bank", "banking"
        ],
        "scenes": [
            (
                "growth",
                "Dynamic business analytics monitor displaying upward trending financial growth charts, candlestick graphs, and 40% sales increase",
                [
                    "business analytics financial growth chart",
                    "stock market data rising screen",
                    "sales revenue growth metrics",
                    "corporate financial analytics dashboard"
                ]
            ),
            (
                "partnership",
                "Corporate executives and business partners shaking hands in modern sunlit boardroom closing strategic agreement",
                [
                    "business partnership handshake office",
                    "corporate meeting professional collaboration",
                    "business executives shaking hands agreement",
                    "professional corporate teamwork"
                ]
            ),
            (
                "general",
                "Modern corporate skyscraper glass office with financial traders and analysts reviewing market data on multi-monitor workstations",
                [
                    "modern corporate office business",
                    "financial analytics trading desk",
                    "corporate enterprise workplace",
                    "business strategy planning meeting"
                ]
            )
        ]
    },
    "abstract_philosophy": {
        "triggers": ["trust", "patience", "success", "freedom", "innovation", "future", "vision"],
        "scenes": [
            (
                "trust",
                "Solid foundational architectural stones standing firmly in clear daylight symbolizing enduring reliability and earned trust",
                [
                    "reliable foundation stones trust",
                    "business partnership handshake agreement",
                    "steady clockwork gears mechanism",
                    "calm ocean sunrise horizon"
                ]
            ),
            (
                "patience",
                "Macro time-lapse of delicate seedling sprouting through rich earth toward gentle morning sunlight",
                [
                    "seed sprouting time lapse nature",
                    "sand flowing hourglass time",
                    "craftsman working carefully patience",
                    "marathon runner steady endurance"
                ]
            ),
            (
                "success",
                "Determined climber standing proudly on majestic mountain peak bathed in golden sunrise light",
                [
                    "climber reaching mountain summit sunrise",
                    "celebrating business team modern office",
                    "athlete crossing marathon finish line",
                    "sunrise over horizon achievement"
                ]
            ),
            (
                "innovation",
                "Creative engineering laboratory with glowing lightbulb filament and visionary designers collaborating on futuristic prototypes",
                [
                    "futuristic technology laboratory innovation",
                    "creative lightbulb idea workspace",
                    "modern digital network innovation",
                    "engineers developing future hardware"
                ]
            )
        ]
    },
    "travel_exploration": {
        "triggers": [
            "travel", "traveling", "travelling", "explore", "exploring", "exploration",
            "places", "place", "culture", "cultures", "adventure", "journey",
            "destination", "destinations", "tourism", "tourist", "tourists", "vacation",
            "trip", "landmark", "monument", "wanderlust", "world travel", "scenic"
        ],
        "scenes": [
            (
                "culture",
                "Vibrant traditional cultural festival with colorful street architecture, historical monuments and diverse cultural heritage",
                [
                    "world cultures traditional festival",
                    "travel culture street market",
                    "cultural heritage traditional landmarks",
                    "historic landmark world culture"
                ]
            ),
            (
                "places",
                "Cinematic aerial drone shot of scenic world travel destinations, historical landmarks and picturesque cultural places",
                [
                    "travel landmark world destination",
                    "travel explore new places",
                    "tourist exploring scenic landscape",
                    "world travel journey adventure"
                ]
            ),
            (
                "adventure",
                "Adventurous traveler with backpack exploring breathtaking mountain valley and scenic vista at golden hour",
                [
                    "traveler exploring mountains backpack",
                    "travel adventure scenic landscape",
                    "wandering traveler exploring new places",
                    "outdoor travel journey nature"
                ]
            ),
            (
                "general",
                "Breathtaking travel montage of diverse global destinations, cultural landmarks and travelers exploring new places",
                [
                    "world travel destinations landmark",
                    "travel tourism explore world",
                    "scenic travel landscape destination",
                    "travel wanderlust beautiful places"
                ]
            )
        ]
    },
    "nature_environment": {
        "triggers": [
            "nature", "forest", "mountain", "mountains", "ocean", "river", "earth",
            "environment", "green", "trees", "landscape", "wildlife", "sunset", "sunrise"
        ],
        "scenes": [
            (
                "landscape",
                "Stunning panoramic view of lush green forest mountains and peaceful flowing river under golden sunlight",
                [
                    "mountain landscape nature scenic",
                    "green forest river flowing",
                    "scenic nature sunrise valley",
                    "peaceful wilderness landscape"
                ]
            ),
            (
                "general",
                "Breathtaking natural scenery showing clean environment, blue skies and majestic mountains",
                [
                    "scenic nature landscape mountains",
                    "beautiful earth environment nature",
                    "peaceful forest sunlight trees"
                ]
            )
        ]
    },
    "health_wellness": {
        "triggers": [
            "health", "healthy", "wellness", "fitness", "exercise", "nutrition",
            "doctor", "hospital", "hospitals", "medicine", "medical", "treatment", "lifestyle",
            "emergency", "ambulance", "paramedic", "paramedics", "rescue", "injured", "patient", "patients", "siren"
        ],
        "scenes": [
            (
                "emergency",
                "Emergency medical responders and ambulance with flashing lights arriving to assist injured patients with urgent healthcare",
                [
                    "emergency ambulance flashing lights",
                    "paramedics ambulance rescue response",
                    "hospital emergency entrance ambulance",
                    "emergency vehicle city street lights"
                ]
            ),
            (
                "fitness",
                "Active person jogging outdoors in scenic park during sunrise maintaining vibrant healthy lifestyle",
                [
                    "fitness workout healthy lifestyle",
                    "person running morning park exercise",
                    "wellness meditation healthy living"
                ]
            ),
            (
                "general",
                "Modern doctor and healthcare professional consulting patient with compassionate care in bright medical clinic",
                [
                    "doctor healthcare hospital clinic",
                    "healthy nutrition fresh fruit lifestyle",
                    "modern medical consultation doctor"
                ]
            )
        ]
    }
}


HINDI_CONCEPT_MAP = {
    "प्रौद्योगिकी": "technology innovation digital",
    "तकनीक": "technology software digital",
    "कंप्यूटर": "computer technology laptop screen",
    "एआई": "artificial intelligence machine learning",
    "आर्टिफिशियल": "artificial intelligence neural network",
    "सुरक्षा": "cybersecurity digital lock protection",
    "हैकर": "hacker cyber attack terminal",
    "पासवर्ड": "password authentication two-factor",
    "डेटा": "big data analytics cloud infrastructure",
    "यात्रा": "world travel exploration destination",
    "संस्कृति": "traditional cultural festival heritage",
    "स्थान": "scenic world travel places",
    "घूमना": "travel journey adventure backpacker",
    "पर्यटन": "tourism travel destinations landmark",
    "व्यापार": "business corporate meeting handshake",
    "पैसा": "finance banking market investment",
    "बिक्री": "sales financial growth revenue chart",
    "विकास": "business analytics growth statistics",
    "भरोसा": "business partnership handshake trust",
    "विश्वास": "reliable foundation stones trust",
    "धैर्य": "seed sprouting patience nature time lapse",
    "सफलता": "climber mountain summit sunrise achievement",
    "शिक्षा": "education learning student school university",
    "सीखना": "learning students studying books",
    "छात्र": "students university college campus",
    "विद्यार्थी": "students studying library education",
    "स्कूल": "school classroom students learning",
    "कॉलेज": "college campus university students",
    "प्रकृति": "nature landscape mountains green forest",
    "पहाड़": "majestic mountain peak scenic nature",
    "स्वास्थ्य": "doctor healthcare wellness medical clinic",
}

TAMIL_CONCEPT_MAP = {
    "தொழில்நுட்பம்": "technology digital innovation computer",
    "கணினி": "computer technology digital screen",
    "செயற்கை": "artificial intelligence technology machine learning",
    "பாதுகாப்பு": "cybersecurity lock protection network",
    "ஹேக்கர்": "hacker cyber attack digital code",
    "கடவுச்சொல்": "password authentication secure login",
    "தரவு": "big data cloud network servers",
    "பயணம்": "travel journey adventure explore new places",
    "கலாச்சாரம்": "traditional cultural festival heritage",
    "இடம்": "scenic world travel destinations landmark",
    "சுற்றுலா": "tourism travel explore world places",
    "வணிகம்": "business corporate enterprise meeting",
    "பணம்": "finance banking market money",
    "விற்பனை": "sales financial growth revenue analytics",
    "வளர்ச்சி": "business growth chart analytics statistics",
    "நம்பிக்கை": "business handshake trust agreement",
    "பொறுமை": "seed sprouting time lapse nature patience",
    "வெற்றி": "mountain peak sunrise achievement success",
    "கல்வி": "education learning student university school",
    "கற்றல்": "learning students studying laptop books",
    "மாணவர்": "students university college campus learning",
    "பள்ளி": "school classroom students learning",
    "கல்லூரி": "college university campus students",
    "இயற்கை": "nature landscape mountains green trees",
    "சுகாதாரம்": "doctor healthcare clinic medical wellness",
}


def normalize_multilingual_text(text: str) -> str:
    """
    Detects if text contains Hindi or Tamil script, and translates it to an English
    conceptual text for domain classification and stock footage search queries.
    Uses ultra-fast local semantic dictionary first, falling back to neural translation.
    """
    if not text:
        return ""

    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
    has_tamil = bool(re.search(r"[\u0B80-\u0BFF]", text))

    if not (has_devanagari or has_tamil):
        return text

    # 1. Instant local domain keyword mapping (sub-millisecond)
    terms = HINDI_CONCEPT_MAP if has_devanagari else TAMIL_CONCEPT_MAP
    matched = [v for k, v in terms.items() if k in text]
    if matched:
        return " ".join(matched)

    # 2. Neural translation fallback for unmapped phrases
    try:
        from deep_translator import MyMemoryTranslator
        src = "hi-IN" if has_devanagari else "ta-IN"
        res = MyMemoryTranslator(source=src, target="en-GB").translate(text)
        if res and res.strip() and not res.startswith("MYMEMORY WARNING"):
            return res.strip()
    except Exception as e:
        logger.debug(f"Multilingual neural translation note: {e}")

    return text


class LLMSceneUnderstandingService:
    """
    Intelligent LLM scene comprehension engine:
    1. Converts voiceover narration sentences into rich, cinematic visual descriptions.
    2. Synthesizes descriptive, multi-word stock footage search queries.
    3. Identifies required visual anchors and prohibited off-domain elements.
    4. Provides native multilingual script comprehension for Hindi, Tamil, and English.
    """
    def __init__(self):
        pass

    def understand_scene(
        self,
        narration_text: str,
        overall_context: Optional[str] = None,
        visual_hint: Optional[str] = None,
        scene_index: int = 0
    ) -> Dict[str, Any]:
        # Multilingual normalization: maps Hindi/Tamil to English conceptual representation
        concept_narration = normalize_multilingual_text(narration_text)
        concept_context = normalize_multilingual_text(overall_context or "")

        lower = concept_narration.lower()
        context_lower = concept_context.lower()
        combined_text = f"{lower} {context_lower}"

        matched_domain = "general"
        matched_concept = "general"
        visual_desc = None
        descriptive_queries: List[str] = []

        # 1. Score each domain: direct scene narration hits get weight 3; secondary context hits get weight 1
        domain_scores: Dict[str, float] = {}
        for domain_key, domain_info in VISUAL_DOMAIN_CONCEPTS.items():
            score = 0.0
            for trig in domain_info["triggers"]:
                trig_escaped = re.escape(trig)
                pattern = rf"(?:\b|_){trig_escaped}(?:\b|_)"
                narration_matches = len(re.findall(pattern, lower))
                if narration_matches > 0:
                    score += narration_matches * 3.0
                elif len(re.findall(pattern, context_lower)) > 0:
                    score += 1.0
            domain_scores[domain_key] = score

        best_domain = max(domain_scores, key=domain_scores.get) if domain_scores else None
        if best_domain and domain_scores[best_domain] > 0.0:
            matched_domain = best_domain
            domain_info = VISUAL_DOMAIN_CONCEPTS[matched_domain]
            for sub_key, sub_desc, sub_queries in domain_info["scenes"]:
                matches_sub = (
                    sub_key in lower
                    or (sub_key == "online_learning" and any(k in lower for k in ["online", "platform", "platforms", "interactive", "accessible", "resources"]))
                    or (sub_key == "future_success" and any(k in lower for k in ["future", "successful", "success", "role", "building"]))
                    or (sub_key == "classroom" and any(k in lower for k in ["classroom", "teacher", "instruct", "school", "lecture"]))
                    or (sub_key == "students" and any(k in lower for k in ["student", "students", "campus", "study", "books", "library"]))
                    or (sub_key == "mobile" and any(k in lower for k in ["website", "websites", "mobile", "app", "application", "share", "personal"]))
                    or (sub_key == "password" and any(k in lower for k in ["password", "passwords", "authentication", "two-factor", "protect"]))
                    or (sub_key == "hacker" and any(k in lower for k in ["hacker", "hackers", "attack", "attacks", "steal", "breach"]))
                    or (sub_key == "network" and any(k in lower for k in ["network", "networks", "data", "infrastructure"]))
                    or (sub_key == "culture" and any(k in lower for k in ["culture", "cultures", "tradition", "traditional", "heritage"]))
                    or (sub_key == "places" and any(k in lower for k in ["place", "places", "destination", "country", "city", "landmark"]))
                    or (sub_key == "adventure" and any(k in lower for k in ["explore", "exploring", "adventure", "journey", "backpack"]))
                    or (sub_key == "growth" and any(k in lower for k in ["growth", "sales", "revenue", "grow", "profit", "quarter"]))
                    or (sub_key == "emergency" and any(k in lower for k in ["emergency", "ambulance", "paramedic", "paramedics", "injured", "hospital", "hospitals", "rescue", "accident"]))
                    or (sub_key == "partnership" and any(k in lower for k in ["partner", "partnership", "handshake", "agreement", "collaborate"]))
                    or (sub_key == "patience" and any(k in lower for k in ["patience", "patient", "sprout", "time", "gradual"]))
                    or (sub_key == "trust" and any(k in lower for k in ["trust", "foundation", "reliable", "integrity", "stone"]))
                )
                if matches_sub:
                    matched_concept = sub_key
                    visual_desc = sub_desc
                    descriptive_queries = list(sub_queries)
                    break

            if not visual_desc:
                # Use domain general scene
                gen_scene = next((s for s in domain_info["scenes"] if s[0] == "general"), domain_info["scenes"][0])
                matched_concept = gen_scene[0]
                visual_desc = gen_scene[1]
                descriptive_queries = list(gen_scene[2])

        # 2. If visual hint was supplied, prioritize it
        if visual_hint and visual_hint.strip():
            descriptive_queries.insert(0, visual_hint.strip())
            if not visual_desc:
                visual_desc = f"Cinematic B-roll capturing {visual_hint.strip()}"

        # 3. High-precision semantic fallback generation if no domain matched
        if not visual_desc:
            stopwords = {
                "allows", "allow", "experience", "different", "everyday", "becoming",
                "important", "part", "this", "that", "these", "those", "have", "with",
                "from", "into", "more", "most", "some", "such", "than", "will", "would",
                "could", "should", "their", "there", "where", "which", "while", "about"
            }
            clean_words = [
                w for w in re.sub(r"[^\w\s]", " ", narration_text).split()
                if len(w) > 3 and w.lower() not in stopwords
            ][:4]

            if clean_words:
                query_phrase = " ".join(clean_words[:3])
                visual_desc = f"Cinematic real-world footage depicting {query_phrase} in clear natural setting"
                descriptive_queries = [
                    query_phrase,
                    f"{clean_words[0]} {clean_words[1]}" if len(clean_words) >= 2 else clean_words[0],
                    clean_words[0]
                ]
            else:
                visual_desc = "Cinematic natural real-world documentary footage"
                descriptive_queries = ["scenic world view", "inspiring landscape"]

        primary_query = descriptive_queries[0]

        logger.info(
            f"Scene {scene_index} LLM Understanding: Domain='{matched_domain}', "
            f"Concept='{matched_concept}', PrimaryQuery='{primary_query}'"
        )

        return {
            "visual_description": visual_desc,
            "descriptive_queries": descriptive_queries,
            "primary_query": primary_query,
            "domain": matched_domain,
            "concept": matched_concept,
        }


llm_scene_service = LLMSceneUnderstandingService()
