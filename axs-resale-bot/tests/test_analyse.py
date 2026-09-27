import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot import DEFAULT_BLOCKED, Config, _csv, analyse


def cfg(max_price=None, keywords="standing,general admission"):
    return Config(
        token="t",  # noqa: S106
        chat_id="1",
        event_url="https://example.test",
        match_keywords=_csv(keywords),
        blocked_phrases=_csv(DEFAULT_BLOCKED),
        max_price=max_price,
        interval=60,
        jitter=0,
        headless=True,
        profile_dir=Path("unused"),
    )


def test_standing_listing_with_price_is_available():
    page = "Official Resale\nStanding\n£65.50 each\nSeated Block A\n£80.00"
    r = analyse(page, cfg())
    assert r.status == "available"
    assert len(r.matches) == 1
    assert "£65.50" in r.matches[0]


def test_heading_without_price_is_not_a_match():
    page = "Ticket types\nStanding\nThere are currently no tickets available"
    assert analyse(page, cfg()).status == "none"


def test_seated_only_is_not_a_match():
    assert analyse("Seated Block C Row F\n£90.00", cfg()).status == "none"


def test_max_price_filters_expensive_listings():
    page = "General Admission Standing\n£250.00"
    assert analyse(page, cfg(max_price=100)).status == "none"
    assert analyse(page, cfg(max_price=300)).status == "available"


def test_thousands_separator_price():
    page = "Standing\n£1,200.00"
    assert analyse(page, cfg(max_price=1500)).status == "available"


def test_queue_or_bot_check_is_blocked():
    assert analyse("You are now in line\nStanding £50", cfg()).status == "blocked"


def test_fingerprint_changes_with_listings():
    a = analyse("Standing\n£50.00", cfg())
    b = analyse("Standing\n£55.00", cfg())
    assert a.fingerprint != b.fingerprint
