from lab3.chain.block import Block, BlockHeader, compute_txs_hash
from lab3.chain.bytes import HASH_SIZE
from lab3.chain.transaction import Transaction


BLOCK_DIFFICULTY = 8


def count_leading_zero_bits(data: bytes) -> int:
    total = 0

    for byte in data:
        if byte == 0:
            total += 8
            continue

        for i in range(8):
            bit = (byte >> (7 - i)) & 1
            if bit == 0:
                total += 1
            else:
                return total

    return total


def valid_pow(block_hash: bytes, difficulty: int) -> bool:
    if len(block_hash) != HASH_SIZE:
        return False

    if difficulty < 0 or difficulty > 256:
        return False

    return count_leading_zero_bits(block_hash) >= difficulty


def mine_block(
    prev_hash: bytes,
    transactions: list[Transaction],
    timestamp: int,
    difficulty: int = BLOCK_DIFFICULTY,
) -> Block:
    if len(prev_hash) != HASH_SIZE:
        raise ValueError("prev_hash must be exactly 32 bytes")

    txs_hash = compute_txs_hash([tx.tx_hash() for tx in transactions])
    nonce = 0

    while True:
        header = BlockHeader(
            prev_hash=prev_hash,
            txs_hash=txs_hash,
            timestamp=timestamp,
            difficulty=difficulty,
            nonce=nonce,
        )
        block = Block(header=header, transactions=transactions)

        if block.validate():
            return block

        nonce += 1
