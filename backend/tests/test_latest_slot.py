from argus.pipeline.latest_slot import LatestSlot


def test_get_returns_put_item():
    slot: LatestSlot[int] = LatestSlot()
    slot.put(1)
    assert slot.get(timeout=0.1) == 1


def test_drop_oldest_keeps_only_latest_and_counts_drops():
    slot: LatestSlot[int] = LatestSlot()
    slot.put(1)
    slot.put(2)
    slot.put(3)
    assert slot.get(timeout=0.1) == 3  # freshest wins
    assert slot.dropped == 2  # two were overwritten


def test_get_times_out_when_empty():
    slot: LatestSlot[int] = LatestSlot()
    assert slot.get(timeout=0.01) is None


def test_get_after_consume_is_empty():
    slot: LatestSlot[int] = LatestSlot()
    slot.put(7)
    assert slot.get(timeout=0.1) == 7
    assert slot.get(timeout=0.01) is None


def test_close_unblocks_and_returns_none():
    slot: LatestSlot[int] = LatestSlot()
    slot.close()
    assert slot.get(timeout=0.01) is None
    slot.put(1)  # puts after close are ignored
    assert slot.get(timeout=0.01) is None
