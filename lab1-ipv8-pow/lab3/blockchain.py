from lab3.utils import (
    Block,
    Transaction,
    create_genesis_block,
    verify_transaction_signature,
)


class Blockchain:
    """
    Holds the local blockchain state for one node.

    This class is responsible for:
    - storing the chain
    - storing the mempool
    - appending valid blocks
    - exposing height/tip/block helpers
    """

    def __init__(self):
        # Chain starts with the fixed genesis block at height 0.
        self.chain: list[Block] = [create_genesis_block()]

        # Mempool stores transactions not yet included in a block.
        # Key: tx_hash
        # Value: Transaction
        self.mempool: dict[bytes, Transaction] = {}

    # -------------------------------------------------------------------------
    # Basic chain info
    # -------------------------------------------------------------------------

    def height(self) -> int:
        """
        Return current chain height.

        Genesis block has height 0.
        """
        return len(self.chain) - 1

    def tip(self) -> Block:
        """
        Return latest block.
        """
        return self.chain[-1]

    def tip_hash(self) -> bytes:
        """
        Return hash of latest block.
        """
        return self.tip().block_hash()

    def get_block(self, height: int) -> Block | None:
        """
        Return block at height, or None if height is invalid.
        """
        if height < 0 or height >= len(self.chain):
            return None

        return self.chain[height]

    # -------------------------------------------------------------------------
    # Mempool
    # -------------------------------------------------------------------------

    def add_transaction(self, tx: Transaction) -> bytes:
        """
        Add transaction to mempool.

        Returns the transaction hash.
        """
        tx_hash = tx.tx_hash()
        self.mempool[tx_hash] = tx
        return tx_hash

    def accept_transaction(self, tx: Transaction) -> tuple[bool, bytes, str]:
        """
        Validate and add a submitted transaction to the mempool.

        Network handlers should call this instead of mutating mempool directly.
        """
        tx_hash = tx.tx_hash()

        if not verify_transaction_signature(tx):
            return False, tx_hash, "Invalid transaction signature"

        self.mempool[tx_hash] = tx
        return True, tx_hash, "Transaction accepted into mempool"

    def get_mempool_transactions(self) -> list[Transaction]:
        """
        Return current mempool transactions as a list.
        """
        return list(self.mempool.values())

    def remove_transactions_from_mempool(self, transactions: list[Transaction]) -> None:
        """
        Remove transactions that were included in a mined/appended block.
        """
        for tx in transactions:
            self.mempool.pop(tx.tx_hash(), None)

    # -------------------------------------------------------------------------
    # Block validation / appending
    # -------------------------------------------------------------------------

    def block_links_to_previous(self, block: Block, previous_block: Block) -> bool:
        """
        Check whether block correctly points to previous_block.
        """
        return block.header.prev_hash == previous_block.block_hash()

    def can_append_block(self, block: Block) -> bool:
        """
        Check whether a block can be appended to the current chain tip.

        This checks:
        - the block itself is valid
        - the block's prev_hash matches the current tip hash
        """
        if not block.validate():
            return False

        return self.block_links_to_previous(block, self.tip())

    def append_block(self, block: Block) -> bool:
        """
        Append block to the chain if it validly extends the current tip.

        Returns:
            True if appended
            False otherwise
        """
        if not self.can_append_block(block):
            return False

        self.chain.append(block)

        # Remove included transactions from mempool, if we had them.
        self.remove_transactions_from_mempool(block.transactions)

        return True
