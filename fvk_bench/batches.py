"""Ten-instance batches for the full SWE-bench Verified set."""

VERIFIED_BATCH_SIZE = 10
VERIFIED_BATCH_COUNT = 50


def verified_batch_names() -> tuple[str, ...]:
    return tuple(f"verified{i:03d}" for i in range(1, VERIFIED_BATCH_COUNT + 1))


def batch_names_for_scheme(scheme: str) -> tuple[str, ...]:
    if scheme == "verified_sorted10":
        return verified_batch_names()
    raise KeyError(f"unknown batch scheme {scheme!r}")


def batch_instances(
    name: str, *, instance_ids: tuple[str, ...] | None = None
) -> tuple[str, ...]:
    if name not in verified_batch_names():
        raise KeyError("unknown batch {!r}; valid: verified001..verified050".format(name))
    ids = tuple(instance_ids or ())
    required = VERIFIED_BATCH_SIZE * VERIFIED_BATCH_COUNT
    if len(ids) != required:
        raise KeyError(
            f"{name} requires exactly {required} ordered verified500 instance ids; "
            f"got {len(ids)}"
        )
    index = int(name.removeprefix("verified")) - 1
    start = index * VERIFIED_BATCH_SIZE
    return ids[start:start + VERIFIED_BATCH_SIZE]
