import pytest

from argus.vlm.parser import ParseError, parse_assessment


def test_parses_clean_json():
    p = parse_assessment('{"score": 0.83, "tags": ["concealment"], "reason": "item hidden"}')
    assert p.score == 0.83
    assert p.tags == ("concealment",)
    assert p.reason == "item hidden"


def test_extracts_json_from_prose_and_code_fence():
    text = 'Sure!\n```json\n{"score": 0.4, "reason": "browsing", "tags": []}\n```\nHope that helps.'
    p = parse_assessment(text)
    assert p.score == 0.4
    assert p.reason == "browsing"
    assert p.tags == ()


def test_clamps_out_of_range_score():
    assert parse_assessment('{"score": 1.7}').score == 1.0
    assert parse_assessment('{"score": -0.5}').score == 0.0


def test_string_tag_coerced_to_tuple():
    assert parse_assessment('{"score": 0.5, "tags": "theft"}').tags == ("theft",)


def test_missing_score_raises():
    with pytest.raises(ParseError):
        parse_assessment('{"reason": "no score here"}')


def test_empty_output_raises():
    with pytest.raises(ParseError):
        parse_assessment("   ")


def test_non_numeric_score_raises():
    with pytest.raises(ParseError):
        parse_assessment('{"score": "high"}')


def test_no_json_raises():
    with pytest.raises(ParseError):
        parse_assessment("the model refused to answer")
