from dataclasses import dataclass

from lab3.chain.bytes import HASH_SIZE, HEADER_SIZE, sha256, u32_be, u64_be
from lab3.chain.transaction import Transaction


@dataclass
class BlockHeader:
    """
    Packed block header:
        prev_hash   32 bytes
        txs_hash    32 bytes
        timestamp    8 bytes, uint64 big-endian
        difficulty   4 bytes, uint32 big-endian
        nonce        8 bytes, uint64 big-endian
    """

    prev_hash: bytes
    txs_hash: bytes
    timestamp: int
    difficulty: int
    nonce: int

    def pack(self) -> bytes:
        if len(self.prev_hash) != HASH_SIZE:
            raise ValueError("prev_hash must be exactly 32 bytes")

        if len(self.txs_hash) != HASH_SIZE:
            raise ValueError("txs_hash must be exactly 32 bytes")

        packed = (
            self.prev_hash
            + self.txs_hash
            + u64_be(self.timestamp)
            + u32_be(self.difficulty)
            + u64_be(self.nonce)
        )

        if len(packed) != HEADER_SIZE:
            raise ValueError("block header must be exactly 84 bytes")

        return packed

    def block_hash(self) -> bytes:
        return sha256(self.pack())


@dataclass
class Block:
    header: BlockHeader
    transactions: list[Transaction]

    def block_hash(self) -> bytes:
        return self.header.block_hash()

    def tx_hashes(self) -> list[bytes]:
        return [tx.tx_hash() for tx in self.transactions]

    def tx_hashes_bytes(self) -> bytes:
        return b"".join(self.tx_hashes())

    def validate(self) -> bool:
        from lab3.chain.pow import valid_pow

        if len(self.header.prev_hash) != HASH_SIZE:
            return False

        if len(self.header.txs_hash) != HASH_SIZE:
            return False

        expected_txs_hash = compute_txs_hash(self.tx_hashes())
        if expected_txs_hash != self.header.txs_hash:
            return False

        return valid_pow(self.block_hash(), self.header.difficulty)


def compute_txs_hash(tx_hashes: list[bytes]) -> bytes:
    for tx_hash in tx_hashes:
        if len(tx_hash) != HASH_SIZE:
            raise ValueError("every transaction hash must be exactly 32 bytes")

    return sha256(b"".join(tx_hashes))


def create_genesis_block() -> Block:
    header = BlockHeader(
        prev_hash=b"\x00" * HASH_SIZE,
        txs_hash=compute_txs_hash([]),
        timestamp=0,
        difficulty=0,
        nonce=0,
    )

    return Block(header=header, transactions=[])
