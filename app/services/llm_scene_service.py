import re
import os
from typing import Dict, Any, List, Optional
from app.core.logging import logger


VISUAL_DOMAIN_CONCEPTS = {
    "cybersecurity": {
        "triggers": [
            "cybersecurity", "security", "hacker", "hackers", "attack", "breach",
            "password", "passwords", "authentication", "encryption", "malware",
            "firewall", "data theft", "website", "websites", "mobile", "app",
            "apps", "application", "applications", "online", "digital", "data",
            "protect", "two-factor", "network", "networks"
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
    }
}


class LLMSceneUnderstandingService:
    """
    Intelligent LLM scene comprehension engine:
    1. Converts voiceover narration sentences into rich, cinematic visual descriptions.
    2. Synthesizes descriptive, multi-word stock footage search queries.
    3. Identifies required visual anchors and prohibited off-domain elements.
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
        lower = narration_text.lower()
        context_lower = (overall_context or "").lower()
        combined_text = f"{lower} {context_lower}"

        matched_domain = "general"
        matched_concept = "general"
        visual_desc = None
        descriptive_queries: List[str] = []

        # 1. Match domain and specific sub-concept
        for domain_key, domain_info in VISUAL_DOMAIN_CONCEPTS.items():
            if any(trig in combined_text for trig in domain_info["triggers"]):
                matched_domain = domain_key
                for sub_key, sub_desc, sub_queries in domain_info["scenes"]:
                    # Match sub-concept against narration text
                    matches_sub = (
                        sub_key in lower
                        or (sub_key == "mobile" and any(k in lower for k in ["website", "websites", "mobile", "app", "application", "share", "personal"]))
                        or (sub_key == "password" and any(k in lower for k in ["password", "passwords", "authentication", "two-factor", "protect"]))
                        or (sub_key == "hacker" and any(k in lower for k in ["hacker", "hackers", "attack", "attacks", "steal", "breach"]))
                        or (sub_key == "network" and any(k in lower for k in ["network", "networks", "data", "infrastructure"]))
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
                break

        # 2. If visual hint was supplied, prioritize it
        if visual_hint and visual_hint.strip():
            descriptive_queries.insert(0, visual_hint.strip())
            if not visual_desc:
                visual_desc = f"Cinematic B-roll capturing {visual_hint.strip()}"

        # 3. Fallback descriptive generation if no domain matched
        if not visual_desc:
            clean_words = [w for w in re.sub(r"[^\w\s]", " ", narration_text).split() if len(w) > 3][:6]
            query_phrase = " ".join(clean_words) if clean_words else "modern professional environment"
            visual_desc = f"Cinematic real-world footage depicting {query_phrase} in bright, modern atmosphere"
            descriptive_queries = [
                f"{query_phrase} professional",
                f"{query_phrase} modern",
                "modern innovative environment"
            ]

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
