import hashlib


HASH_SIZE = 32
HEADER_SIZE = 84


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def u64_be(value: int) -> bytes:
    if value < 0 or value >= 2**64:
        raise ValueError("value does not fit in uint64")

    return value.to_bytes(8, "big")


def u32_be(value: int) -> bytes:
    if value < 0 or value >= 2**32:
        raise ValueError("value does not fit in uint32")

    return value.to_bytes(4, "big")
