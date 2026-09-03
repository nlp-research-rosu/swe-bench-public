import pytest

from fvkbench import batches


def test_verified500_batches_partition_sorted_ids():
    ids = tuple(f"repo__repo-{index:03d}" for index in range(500))
    names = batches.verified_batch_names()
    assert len(names) == 50
    assert names[0] == "verified001"
    assert names[-1] == "verified050"
    flattened = tuple(
        instance
        for name in names
        for instance in batches.batch_instances(name, instance_ids=ids)
    )
    assert flattened == ids


def test_batch_rejects_invalid_name_or_count():
    with pytest.raises(KeyError, match="valid"):
        batches.batch_instances("batch1", instance_ids=tuple(range(500)))
    with pytest.raises(KeyError, match="exactly 500"):
        batches.batch_instances("verified001", instance_ids=("one",))


def test_only_verified_scheme_is_supported():
    assert batches.batch_names_for_scheme("verified_sorted10") == batches.verified_batch_names()
    with pytest.raises(KeyError):
        batches.batch_names_for_scheme("multilingual_sorted10")
