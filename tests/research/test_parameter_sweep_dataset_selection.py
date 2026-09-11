from collections import deque


def _select(boundaries: range, mode: str, maximum: int | None):
    selected = deque(maxlen=maximum) if mode == "LATEST_N_UNTIL_CUTOFF" else []
    for boundary in boundaries:
        selected.append(boundary)
    return list(selected)


def test_latest_n_keeps_freshest_tail_and_omits_only_oldest_rows():
    selected = _select(range(11_037), "LATEST_N_UNTIL_CUTOFF", 10_000)
    assert len(selected) == 10_000
    assert selected[0] == 1_037
    assert selected[-1] == 11_036
    assert 11_037 - len(selected) == 1_037


def test_all_until_cutoff_keeps_complete_eligible_universe():
    selected = _select(range(11_037), "ALL_UNTIL_CUTOFF", None)
    assert len(selected) == 11_037
    assert selected[0] == 0
    assert selected[-1] == 11_036
