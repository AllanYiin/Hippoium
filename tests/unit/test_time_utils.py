from datetime import timezone

from hippoium.core.utils.time import utc_now


def test_utc_now_is_timezone_aware():
    now = utc_now()
    assert now.tzinfo is timezone.utc
