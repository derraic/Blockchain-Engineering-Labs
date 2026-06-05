import hashlib
from dataclasses import dataclass

# =============================================================================
# Basic byte/hash helpers
# =============================================================================

BLOCK_DIFFICULTY = 8
HASH_SIZE = 32
HEADER_SIZE = 84


def sha256(data: bytes) -> bytes:
    """
    Return SHA-256(data) as raw 32 bytes.
    """
    return hashlib.sha256(data).digest()


def u64_be(value: int) -> bytes:
    """
    Encode an integer as an unsigned 64-bit big-endian value.

    Used for:
    - transaction timestamp
    - block timestamp
    - block nonce
    """
    if value < 0 or value >= 2**64:
        raise ValueError("value does not fit in uint64")

    return value.to_bytes(8, "big")


def u32_be(value: int) -> bytes:
    """
    Encode an integer as an unsigned 32-bit big-endian value.

    Used for:
    - block difficulty
    """
    if value < 0 or value >= 2**32:
        raise ValueError("value does not fit in uint32")

    return value.to_bytes(4, "big")


# =============================================================================
# Transaction
# =============================================================================


@dataclass
class Transaction:
    """
    A transaction received from the Lab 3 server.

    The transaction hash must be:

        SHA256(sender_key || data || timestamp_8byte_be || signature)
    """

    sender_key: bytes
    data: bytes
    timestamp: int
    signature: bytes

    def tx_hash(self) -> bytes:
        """
        Compute the 32-byte transaction hash
        """
        blob = (self.sender_key + self.data + u64_be(self.timestamp) +
                self.signature)

        return sha256(blob)


def verify_transaction_signature(tx: Transaction) -> bool:
    """
    Verify the server transaction signature.

    Signature message:
        sender_key || data || timestamp_8byte_be
    """
    try:
        from ipv8.keyvault.crypto import ECCrypto

        crypto = ECCrypto()
        public_key = crypto.key_from_public_bin(tx.sender_key)
        signed_data = tx.sender_key + tx.data + u64_be(tx.timestamp)

        return crypto.is_valid_signature(
            public_key,
            signed_data,
            tx.signature,
        )
    except Exception as e:
        print(f"Signature verification failed: {e}", flush=True)
        return False


# =============================================================================
# Block header
# =============================================================================


@dataclass
class BlockHeader:
    """
    Block header format.

    The packed header must be exactly 84 bytes:

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
        """
        Pack the block header into its exact binary format.
        """
        if len(self.prev_hash) != HASH_SIZE:
            raise ValueError("prev_hash must be exactly 32 bytes")

        if len(self.txs_hash) != HASH_SIZE:
            raise ValueError("txs_hash must be exactly 32 bytes")

        packed = (self.prev_hash + self.txs_hash + u64_be(self.timestamp) +
                  u32_be(self.difficulty) + u64_be(self.nonce))

        if len(packed) != HEADER_SIZE:
            raise ValueError("block header must be exactly 84 bytes")

        return packed

    def block_hash(self) -> bytes:
        """
        Compute the 32-byte hash of this block header.
        """
        return sha256(self.pack())


# =============================================================================
# Block
# =============================================================================


@dataclass
class Block:
    """
    A block consists of:
    - a header
    - the transactions included in the block

    Internally we keep full Transaction objects because that makes validation easy.
    When responding to the server, we only send concatenated transaction hashes.
    """

    header: BlockHeader
    transactions: list[Transaction]

    def block_hash(self) -> bytes:
        """
        Return the SHA-256 hash of the block header.
        """
        return self.header.block_hash()

    def tx_hashes(self) -> list[bytes]:
        """
        Return the list of transaction hashes in block order.
        """
        return [tx.tx_hash() for tx in self.transactions]

    def tx_hashes_bytes(self) -> bytes:
        """
        Return concatenated transaction hashes.

        This is exactly what the server expects in BlockResponsePayload.tx_hashes.
        Empty block => b"".
        """
        return b"".join(self.tx_hashes())

    def validate(self) -> bool:
        """
        Validate this block by checking:
        - prev_hash has correct size
        - txs_hash has correct size
        - txs_hash matches the included transactions
        - block hash satisfies declared PoW difficulty

        This does NOT check whether the block links to a previous block.
        Chain-link validation should be done when appending to the chain.
        """
        if len(self.header.prev_hash) != HASH_SIZE:
            return False

        if len(self.header.txs_hash) != HASH_SIZE:
            return False

        expected_txs_hash = compute_txs_hash(self.tx_hashes())

        if expected_txs_hash != self.header.txs_hash:
            return False

        if not valid_pow(self.block_hash(), self.header.difficulty):
            return False

        return True


# =============================================================================
# Transaction commitment
# =============================================================================


def compute_txs_hash(tx_hashes: list[bytes]) -> bytes:
    """
    Compute the block body commitment.

    The lab requires:

        txs_hash = SHA256(tx_hash_1 || tx_hash_2 || ... || tx_hash_n)

    For an empty block:

        txs_hash = SHA256(b"")

    Since b"".join([]) is b"", this works for both normal and empty blocks.
    """
    for tx_hash in tx_hashes:
        if len(tx_hash) != HASH_SIZE:
            raise ValueError("every transaction hash must be exactly 32 bytes")

    return sha256(b"".join(tx_hashes))


# =============================================================================
# Proof of Work
# =============================================================================


def count_leading_zero_bits(data: bytes) -> int:
    """
    Count the number of leading zero bits in a byte string.

    Example:
        b"\\x00\\x7f..." starts with:
        - 8 zero bits from 0x00
        - then 1 zero bit from 0x7f = 01111111
        => total 9 leading zero bits
    """
    total = 0

    for byte in data:
        if byte == 0:
            total += 8
            continue

        # First non-zero byte.
        # Check bits from most significant to least significant.
        for i in range(8):
            bit = (byte >> (7 - i)) & 1

            if bit == 0:
                total += 1
            else:
                return total

    return total


def valid_pow(block_hash: bytes, difficulty: int) -> bool:
    """
    Check whether block_hash satisfies the declared difficulty.

    Difficulty means:
        required number of leading zero bits in block_hash
    """
    if len(block_hash) != HASH_SIZE:
        return False

    if difficulty < 0:
        return False

    # SHA-256 only has 256 bits, so difficulty above 256 is impossible.
    if difficulty > 256:
        return False

    return count_leading_zero_bits(block_hash) >= difficulty


# =============================================================================
# Genesis block
# =============================================================================


def create_genesis_block() -> Block:
    """
    Create the fixed genesis block.

    All 3 teammates must create EXACTLY the same genesis block.
    Otherwise your chains already disagree at height 0.

    We use:
    - prev_hash = 32 zero bytes
    - no transactions
    - txs_hash = SHA256(b"")
    - timestamp = 0
    - difficulty = 0
    - nonce = 0

    difficulty = 0 means the genesis block is always valid.
    """
    header = BlockHeader(
        prev_hash=b"\x00" * HASH_SIZE,
        txs_hash=compute_txs_hash([]),
        timestamp=0,
        difficulty=0,
        nonce=0,
    )

    return Block(
        header=header,
        transactions=[],
    )


# =============================================================================
# Mining
# =============================================================================


def mine_block(
    prev_hash: bytes,
    transactions: list[Transaction],
    timestamp: int,
    difficulty: int = BLOCK_DIFFICULTY,
) -> Block:
    """
    Mine a new block.

    Mining means:
    - choose the transactions for the block
    - compute txs_hash
    - build a block header pointing to prev_hash
    - try nonce values until the block hash satisfies the difficulty

    This function returns a full valid Block.
    """
    if len(prev_hash) != HASH_SIZE:
        raise ValueError("prev_hash must be exactly 32 bytes")

    tx_hashes = [tx.tx_hash() for tx in transactions]
    txs_hash = compute_txs_hash(tx_hashes)

    nonce = 0

    while True:
        header = BlockHeader(
            prev_hash=prev_hash,
            txs_hash=txs_hash,
            timestamp=timestamp,
            difficulty=difficulty,
            nonce=nonce,
        )

        block = Block(
            header=header,
            transactions=transactions,
        )

        if block.validate():
            return block

        nonce += 1


# =============================================================================
# Chain helpers
# =============================================================================


def block_links_to_previous(block: Block, previous_block: Block) -> bool:
    """
    Check whether block correctly points to previous_block.
    """
    return block.header.prev_hash == previous_block.block_hash()


def can_append_block(chain: list[Block], block: Block) -> bool:
    """
    Check whether a block can be appended to the current chain tip.

    This checks:
    - the block itself is valid
    - the block's prev_hash matches the current tip hash
    """
    if len(chain) == 0:
        return False

    if not block.validate():
        return False

    current_tip = chain[-1]

    return block_links_to_previous(block, current_tip)


def append_block_if_valid(chain: list[Block], block: Block) -> bool:
    """
    Append block to chain if it validly extends the current tip.

    Returns:
        True  if appended
        False otherwise
    """
    if not can_append_block(chain, block):
        return False

    chain.append(block)
    return True
