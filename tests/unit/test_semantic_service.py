import pytest
from app.services.semantic_service import semantic_service


def test_ambiguous_word_disambiguation():
    # 1. Cloud computing vs Sky clouds
    res_tech = semantic_service.analyze_hard_cases("Modern cloud computing infrastructure with servers.")
    assert "data center" in res_tech["primary_query"] or "server" in res_tech["primary_query"]

    res_sky = semantic_service.analyze_hard_cases("White fluffy cloud in the sunny blue sky.")
    assert "sky" in res_sky["primary_query"] or "clouds" in res_sky["primary_query"]

    # 2. Bank account vs River bank
    res_fin = semantic_service.analyze_hard_cases("Deposit money into your bank savings account.")
    assert "financial" in res_fin["primary_query"] or "bank" in res_fin["primary_query"]

    res_river = semantic_service.analyze_hard_cases("Sitting near the river bank watching calm water.")
    assert "river" in res_river["primary_query"] or "water" in res_river["primary_query"]

    # 3. Python programming vs Python snake
    res_code = semantic_service.analyze_hard_cases("Writing python code and software scripts.")
    assert "programming" in res_code["primary_query"] or "code" in res_code["primary_query"]


def test_abstract_concepts():
    res = semantic_service.analyze_hard_cases("Trust is earned slowly.")
    assert any("handshake" in q or "foundation" in q or "partnership" in q for q in res["all_queries"])

    res_pat = semantic_service.analyze_hard_cases("Success requires patience.")
    assert any("mountain" in q or "climber" in q or "hourglass" in q or "sprouting" in q for q in res_pat["all_queries"])


def test_statistics_preservation():
    res = semantic_service.analyze_hard_cases("Sales grew 40% in 2025.")
    assert res["detected_concept"] == "statistics_growth"
    assert any("chart" in q or "analytics" in q or "graph" in q for q in res["all_queries"])


def test_celebrity_and_brand_safety():
    res = semantic_service.analyze_hard_cases("Elon Musk and Steve Jobs introduced new Apple devices.")
    assert len(res["warnings"]) > 0
    # Prohibits real face generation; maps to neutral presentation
    assert "elon musk" in res["neutralized_entities"]
    assert "apple" in res["neutralized_entities"]


def test_sensitive_news_respectful_treatment():
    res = semantic_service.analyze_hard_cases("The tragic loss and funeral of community members.")
    assert res["is_sensitive"] is True
    assert len(res["warnings"]) > 0
    assert "memorial" in res["primary_query"] or "dawn" in res["primary_query"]


def test_avoidance_filter():
    violates, reason = semantic_service.violates_avoid_rules(
        metadata_text="Close-up portrait of a woman's face smiling",
        avoid_list=["people's faces"]
    )
    assert violates is True
    assert reason == "people's faces"

    violates_no, _ = semantic_service.violates_avoid_rules(
        metadata_text="Server racks glowing blue in data center",
        avoid_list=["people's faces", "alcohol"]
    )
    assert violates_no is False


def test_relevance_scoring_range():
    score = semantic_service.compute_relevance(
        scene_text="High performance servers in a cloud facility",
        candidate_description="Cloud data center servers and high tech network cables"
    )
    assert 1.0 <= score <= 5.0
    assert score >= 3.0  # High semantic relevance
