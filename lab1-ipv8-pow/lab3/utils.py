import hashlib
from dataclasses import dataclass

# Naming:
# transactions  -> list[Transaction]
# tx_hashes     -> list[bytes]
# txs_hash      -> single bytes commitment -> sha256(tx1 + tx2 + ... + txn)

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def u64_be(value: int) -> bytes:
    return value.to_bytes(8, "big")

def u32_be(value: int) -> bytes:
    return value.to_bytes(4, "big")

@dataclass
class Transaction:
    sender_key: bytes
    data: bytes
    timestamp: int
    signature: bytes

    def tx_hash(self) -> bytes:
        blob = (
            self.sender_key
            + self.data
            + u64_be(self.timestamp)
            + self.signature
        )

        return sha256(blob)
    
@dataclass
class BlockHeader:
    prev_hash: bytes
    txs_hash: bytes
    timestamp: int
    difficulty: int
    nonce: int

    def pack(self) -> bytes:
        assert len(self.prev_hash) == 32
        assert len(self.txs_hash) == 32

        return (
            self.prev_hash
            + self.txs_hash
            + u64_be(self.timestamp)
            + u32_be(self.difficulty)
            + u64_be(self.nonce)
        )

    def block_hash(self) -> bytes:
        packed = self.pack()

        assert len(packed) == 84

        return sha256(packed)
    
@dataclass
class Block:
    header: BlockHeader
    transactions: list[Transaction]

    def validate(self) -> bool:
        tx_hashes = [tx.tx_hash() for tx in self.transactions]

        expected_txs_hash = compute_txs_hash(tx_hashes)

        if expected_txs_hash != self.header.txs_hash:
            return False

        block_hash = self.header.block_hash()

        if not valid_pow(block_hash, self.header.difficulty):
            return False

        return True
    
def compute_txs_hash(tx_hashes: list[bytes]) -> bytes:
    if len(tx_hashes) == 0:
        return sha256(b"")

    return sha256(b"".join(tx_hashes))

def count_leading_zero_bits(data: bytes) -> int:
    total = 0

    for byte in data:
        if byte == 0:
            total += 8
            continue

        # first nonzero byte
        for i in range(8):
            bit = (byte >> (7 - i)) & 1

            if bit == 0:
                total += 1
            else:
                return total

    return total

def valid_pow(block_hash: bytes, difficulty: int) -> bool:
    return count_leading_zero_bits(block_hash) >= difficulty

def mine_block(header: BlockHeader) -> bytes:
    nonce = 0

    while True:
        header.nonce = nonce

        h = header.block_hash()

        if valid_pow(h, header.difficulty):
            return h

        nonce += 1