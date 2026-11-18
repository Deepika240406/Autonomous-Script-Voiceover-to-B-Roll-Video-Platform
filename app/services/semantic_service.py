import re
from typing import Dict, Any, List, Tuple, Optional
from app.providers.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingsProvider
from app.services.llm_scene_service import llm_scene_service
from app.core.logging import logger


ABSTRACT_METAPHORS = {
    "trust": ["business partnership handshake", "reliable foundation stones", "calm ocean sunrise", "steady clockwork gears"],
    "patience": ["seed sprouting time lapse", "sand flowing hourglass", "craftsman working carefully", "marathon runner endurance"],
    "success": ["mountain climber reaching summit", "celebrating team in modern office", "sunrise over horizon", "athlete finishing line"],
    "innovation": ["futuristic technology laboratory", "robotics engineer developing hardware", "modern digital network data", "creative brain idea light"],
    "freedom": ["bird flying open sky", "person standing on mountain edge", "open highway journey"],
    "growth": ["plant growing green leaves", "financial upward trending chart", "young tree expanding branches"],
}

AMBIGUOUS_TERMS = {
    "bank": {
        "finance_terms": ["money", "account", "finance", "loan", "deposit", "card", "teller", "cash", "interest", "statement", "save", "saving"],
        "nature_terms": ["river", "stream", "water", "fishing", "grass", "mud", "slope", "lake"],
        "finance_query": "financial bank office teller money transaction",
        "nature_query": "scenic river bank flowing water nature",
    },
    "cloud": {
        "tech_terms": ["computing", "server", "data", "storage", "aws", "azure", "software", "infrastructure", "devops", "platform", "host"],
        "weather_terms": ["sky", "rain", "storm", "sun", "weather", "overcast", "fluffy", "cumulus", "sunset"],
        "tech_query": "cloud computing data center server infrastructure glowing",
        "weather_query": "dramatic blue sky white clouds time lapse",
    },
    "python": {
        "tech_terms": ["programming", "code", "developer", "script", "software", "language", "syntax", "engineer", "algorithm", "pip"],
        "animal_terms": ["snake", "reptile", "zoo", "jungle", "wildlife", "slither", "scales"],
        "tech_query": "programmer writing python code on laptop screen ide",
        "animal_query": "python snake reptile wildlife nature",
    },
    "mouse": {
        "tech_terms": ["click", "cursor", "computer", "desktop", "laptop", "wireless", "pad", "screen", "keyboard"],
        "animal_terms": ["cheese", "rodent", "trap", "fur", "tail", "whiskers", "field"],
        "tech_query": "hand using modern computer mouse on office desk",
        "animal_query": "small wild field mouse animal nature",
    },
    "value": {
        "finance_terms": ["stock", "price", "market", "money", "worth", "cost", "dollar", "asset", "investment", "portfolio"],
        "ethics_terms": ["moral", "integrity", "ethics", "principle", "respect", "honesty", "virtue"],
        "finance_query": "financial investment growth coins and graph",
        "ethics_query": "honest business handshake respectful team integrity",
    }
}

REAL_PEOPLE_NAMES = [
    "elon musk", "tim cook", "steve jobs", "satya nadella", "sundar pichai",
    "mark zuckerberg", "bill gates", "jeff bezos", "donald trump", "joe biden",
    "narendra modi", "taylor swift"
]

BRANDS = [
    "apple", "google", "microsoft", "nike", "amazon", "tesla", "meta",
    "coca cola", "samsung", "netflix"
]

SENSITIVE_TRIGGERS = [
    "war", "death", "died", "funeral", "tragedy", "tragic", "loss", "crash",
    "casualty", "attack", "bomb", "crisis", "victim", "grief", "sad news",
    "accident", "mourning", "disaster", "fatal", "sorrow"
]

TECH_KEYWORDS = {
    "cybersecurity", "security", "hacker", "hackers", "password", "passwords",
    "authentication", "network", "networks", "data", "attack", "attacks", "website",
    "websites", "app", "apps", "application", "applications", "digital", "ai",
    "software", "computer", "computers", "code", "coding", "programming", "cloud",
    "server", "servers", "infrastructure", "internet", "online", "system", "systems",
    "cyber", "device", "devices", "mobile", "tech", "technology", "encryption",
    "two-factor", "protect", "protection", "information", "robot", "robotics", "automation"
}

BUSINESS_KEYWORDS = {
    "business", "finance", "sales", "revenue", "market", "marketing", "stock",
    "stocks", "growth", "investment", "investor", "company", "enterprise", "profit",
    "profits", "bank", "banking", "economy", "economic", "trade", "trading", "office"
}

HEALTH_KEYWORDS = {
    "health", "healthcare", "medicine", "medical", "doctor", "doctors", "patient",
    "patients", "hospital", "clinic", "disease", "treatment", "biology", "pharmacy"
}

TRAVEL_KEYWORDS = {
    "travel", "traveling", "travelling", "explore", "exploring", "exploration",
    "places", "place", "culture", "cultures", "adventure", "journey", "destination",
    "destinations", "tourism", "tourist", "tourists", "vacation", "trip", "monument",
    "landmark", "landmarks", "wanderlust", "passport", "sightseeing"
}

INCOMPATIBLE_NATURE_TAGS = {
    "animal", "animals", "wild", "wildlife", "safari", "jaguar", "leopard", "cheetah",
    "lion", "tiger", "gorilla", "monkey", "chimpanzee", "bear", "wolf", "deer", "fox",
    "birds", "bird", "eagle", "duck", "waterfowl", "cormorants",
    "ocean", "waves", "beach", "seascape", "underwater", "fish", "coral", "reef",
    "volcano", "lava", "chimney", "fireplace", "stone bridge", "waterfall"
}

INCOMPATIBLE_TRAVEL_TAGS = {
    "circuit", "sensor", "arduino", "robot", "robotics", "pcb", "electronics",
    "microcontroller", "wire", "wires", "hardware", "server room", "hacker", "coding",
    "soldering", "ultrasonic", "chip", "semiconductor", "cybersecurity"
}

STOPWORDS_EXTENDED = {
    "a", "an", "the", "in", "on", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "out", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
    "don", "should", "now", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "and", "but", "if",
    "or", "because", "as", "until", "while", "of", "it", "its", "this", "that", "these",
    "those", "today", "used", "helps", "continues", "becoming", "important", "part",
    "everyday", "lives", "large", "amounts", "better", "make", "people", "grow",
    "like", "much", "many", "well", "every", "day", "days", "may", "might", "try",
    "tries", "trying", "steal", "stealing", "strong", "weak", "way", "ways", "time",
    "times", "year", "years", "thing", "things", "help", "good", "great", "small", "big",
    "start", "started", "end", "world", "our", "their", "your", "my", "we", "they", "you",
    "he", "she", "us", "them", "him", "her", "also", "first", "second", "third", "essential"
}


class SemanticService:
    def __init__(self):
        self.embeddings_provider = SentenceTransformerEmbeddingsProvider()

    def detect_domain(self, text: str) -> str:
        lower = text.lower()
        tech_hits = sum(1 for kw in TECH_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", lower))
        biz_hits = sum(1 for kw in BUSINESS_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", lower))
        health_hits = sum(1 for kw in HEALTH_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", lower))
        travel_hits = sum(1 for kw in TRAVEL_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", lower))

        if travel_hits >= 2 or (travel_hits > 0 and travel_hits >= tech_hits and travel_hits >= biz_hits and travel_hits >= health_hits):
            return "travel"
        if tech_hits >= 2 or (tech_hits > 0 and tech_hits >= biz_hits and tech_hits >= health_hits):
            return "tech"
        if biz_hits >= 2 or (biz_hits > 0 and biz_hits >= health_hits):
            return "business"
        if health_hits >= 2 or health_hits > 0:
            return "health"
        return "general"

    def analyze_hard_cases(
        self,
        text: str,
        visual_hint: Optional[str] = None,
        overall_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes text for abstract concepts, statistics, ambiguous terms,
        celebrities, brands, and sensitive topics using LLM scene understanding.
        """
        lower = text.lower()
        warnings: List[str] = []
        is_sensitive = False
        neutralized_entities: List[str] = []
        search_candidates: List[str] = []
        detected_concept = None
        domain = self.detect_domain(f"{text} {overall_context or ''}")

        # 1. Real people & brand checks (Section 8.D)
        for person in REAL_PEOPLE_NAMES:
            if re.search(rf"\b{re.escape(person)}\b", lower):
                neutralized_entities.append(person)
                warnings.append(
                    f"Named person '{person}' detected. Policy: Realistic depiction of real people prohibited. "
                    "Selected neutral contextual imagery without celebrity likeness or endorsement."
                )
                search_candidates.append("technology leader giving visionary keynote presentation on stage")

        for brand in BRANDS:
            if re.search(rf"\b{re.escape(brand)}\b", lower):
                neutralized_entities.append(brand)
                warnings.append(
                    f"Brand '{brand}' detected. Policy: Fake brand logos prohibited. "
                    "Selected generic modern industry footage without implied endorsement."
                )
                search_candidates.append("modern innovative tech product in sleek workspace")

        # 2. Sensitive content check (Section 8.E)
        for term in SENSITIVE_TRIGGERS:
            if re.search(rf"\b{re.escape(term)}\b", lower):
                is_sensitive = True
                warnings.append(
                    f"Sensitive topic '{term}' detected. Policy: Respectful, non-sensational, "
                    "neutral symbolic footage selected."
                )
                search_candidates.append("peaceful somber dawn over quiet landscape memorial reflection")
                break

        # 3. Numbers & Statistics check (Section 8.B)
        stat_match = re.search(r"(\d+%\s*|\$\d+|\d+\s*percent|\b20\d\d\b|\bgrew\b|\bincreased\b|\bdecreased\b)", lower)
        if stat_match and not is_sensitive:
            search_candidates.append("business analytics dashboard displaying growth metrics and charts")
            search_candidates.append("financial stock chart data rising on digital monitor")
            detected_concept = "statistics_growth"

        # 4. Ambiguous words disambiguation (Section 8.C)
        for ambiguous_word, info in AMBIGUOUS_TERMS.items():
            if re.search(rf"\b{re.escape(ambiguous_word)}\b", lower):
                finance_hits = sum(1 for t in info.get("finance_terms", []) if re.search(rf"\b{t}\b", lower))
                tech_hits = sum(1 for t in info.get("tech_terms", []) if re.search(rf"\b{t}\b", lower))
                nature_hits = sum(1 for t in info.get("nature_terms", []) if re.search(rf"\b{t}\b", lower))
                weather_hits = sum(1 for t in info.get("weather_terms", []) if re.search(rf"\b{t}\b", lower))
                animal_hits = sum(1 for t in info.get("animal_terms", []) if re.search(rf"\b{t}\b", lower))

                if ambiguous_word == "bank":
                    if nature_hits > finance_hits:
                        search_candidates.insert(0, info["nature_query"])
                    else:
                        search_candidates.insert(0, info["finance_query"])
                elif ambiguous_word == "cloud":
                    if weather_hits > tech_hits:
                        search_candidates.insert(0, info["weather_query"])
                    else:
                        search_candidates.insert(0, info["tech_query"])
                elif ambiguous_word == "python":
                    if animal_hits > tech_hits:
                        search_candidates.insert(0, info["animal_query"])
                    else:
                        search_candidates.insert(0, info["tech_query"])
                elif ambiguous_word == "mouse":
                    if animal_hits > tech_hits:
                        search_candidates.insert(0, info["animal_query"])
                    else:
                        search_candidates.insert(0, info["tech_query"])
                elif ambiguous_word == "value":
                    if finance_hits > 0:
                        search_candidates.insert(0, info["finance_query"])
                    else:
                        search_candidates.insert(0, info["ethics_query"])

        # 5. Abstract metaphors (Section 8.A)
        for concept, visual_list in ABSTRACT_METAPHORS.items():
            if re.search(rf"\b{re.escape(concept)}\b", lower):
                detected_concept = concept
                search_candidates.extend(visual_list)

        # 6. LLM-Powered Scene Understanding & Visual Description Generation
        llm_analysis = llm_scene_service.understand_scene(
            narration_text=text,
            overall_context=overall_context,
            visual_hint=visual_hint,
        )
        visual_desc = llm_analysis["visual_description"]
        search_candidates.extend(llm_analysis["descriptive_queries"])

        # 7. Include user visual hint if available
        if visual_hint:
            search_candidates.insert(0, visual_hint.strip())

        # 8. Domain-specific semantic concept queries
        if domain == "tech":
            if any(w in lower for w in ["password", "passwords", "authentication", "lock"]):
                search_candidates.append("password security authentication")
                search_candidates.append("digital security lock")
            if any(w in lower for w in ["hacker", "hackers", "attack", "attacks", "breach"]):
                search_candidates.append("cyber attack hacker")
                search_candidates.append("hacker coding security")
            if any(w in lower for w in ["network", "networks", "data", "protect", "protection"]):
                search_candidates.append("network security data protection")
                search_candidates.append("cyber security technology")
            if any(w in lower for w in ["mobile", "app", "apps", "application", "applications", "website", "websites"]):
                search_candidates.append("mobile applications smartphone")
                search_candidates.append("computer website browsing")
            if any(w in lower for w in ["ai", "artificial intelligence", "automate", "automation"]):
                search_candidates.append("artificial intelligence technology")
                search_candidates.append("data analytics dashboard")

        # 9. Extract substantive visual nouns
        clean_text_query = re.sub(r"[^\w\s]", " ", text)
        substantive_words = [
            w for w in clean_text_query.split()
            if len(w) > 2 and w.lower() not in STOPWORDS_EXTENDED
        ]

        if len(substantive_words) >= 2:
            search_candidates.append(f"{substantive_words[0]} {substantive_words[1]}")
            if len(substantive_words) >= 4:
                search_candidates.append(f"{substantive_words[2]} {substantive_words[3]}")
        elif substantive_words:
            search_candidates.append(substantive_words[0])

        if domain == "tech" and not search_candidates:
            search_candidates.append("cybersecurity digital technology")

        primary_query = search_candidates[0] if search_candidates else text[:50]

        return {
            "primary_query": primary_query,
            "all_queries": list(dict.fromkeys(search_candidates)),
            "warnings": warnings,
            "is_sensitive": is_sensitive,
            "neutralized_entities": neutralized_entities,
            "detected_concept": detected_concept,
            "domain": domain,
            "visual_description": visual_desc,
        }

    def is_domain_incompatible(self, metadata_text: str, expected_domain: str) -> Tuple[bool, Optional[str]]:
        """
        Anti-drift domain consistency check.
        Rejects wildlife/nature clips when the topic is tech, business, or health.
        Rejects electronic/sensor/hardware clips when the topic is travel or tourism.
        """
        lower = metadata_text.lower()
        if expected_domain in ("tech", "business", "health"):
            for tag in INCOMPATIBLE_NATURE_TAGS:
                if re.search(rf"\b{re.escape(tag)}\b", lower):
                    return True, f"Incompatible domain concept '{tag}' for {expected_domain} content"
        elif expected_domain in ("travel", "travel_exploration"):
            for tag in INCOMPATIBLE_TRAVEL_TAGS:
                if re.search(rf"\b{re.escape(tag)}\b", lower):
                    return True, f"Incompatible hardware/tech concept '{tag}' for travel content"
        return False, None

    def compute_relevance(self, scene_text: str, candidate_description: str, visual_hint: Optional[str] = None) -> float:
        """
        Computes 1.0 to 5.0 semantic relevance score between scene meaning and footage metadata.
        """
        target = f"{scene_text} {visual_hint or ''}".strip()
        sim = self.embeddings_provider.compute_similarity(target, candidate_description)
        # Scale [0.0, 1.0] to [1.0, 5.0]
        score = round(1.0 + (sim * 4.0), 2)
        return min(5.0, max(1.0, score))

    def compute_batch_relevance(self, scene_text: str, candidate_descriptions: List[str], visual_hint: Optional[str] = None) -> List[float]:
        """
        Vectorized batch relevance computation using Sentence-BERT dense matrix multiplication.
        """
        if not candidate_descriptions:
            return []
        target = f"{scene_text} {visual_hint or ''}".strip()
        sims = self.embeddings_provider.compute_batch_similarities(target, candidate_descriptions)
        return [min(5.0, max(1.0, round(1.0 + (s * 4.0), 2))) for s in sims]

    def violates_avoid_rules(self, metadata_text: str, avoid_list: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Checks whether candidate footage metadata violates the user avoid list.
        Uses precise word-boundary matching so words like 'interface' are not falsely flagged.
        """
        lower = metadata_text.lower()
        for avoid_term in avoid_list:
            clean = avoid_term.strip().lower()
            if not clean:
                continue
            # e.g. "people's faces" -> check distinct word boundaries for face, faces, portrait, selfie
            if clean in ("people's faces", "faces", "face"):
                if re.search(r"\b(face|faces|portrait|selfie|close up face)\b", lower):
                    return True, avoid_term
            else:
                escaped = re.escape(clean)
                if re.search(rf"\b{escaped}\b", lower):
                    return True, avoid_term
        return False, None


semantic_service = SemanticService()
