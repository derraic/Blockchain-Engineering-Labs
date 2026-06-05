from lab3.chain.block import Block, create_genesis_block
from lab3.chain.mempool import Mempool
from lab3.chain.transaction import Transaction, verify_transaction_signature


class Blockchain:
    """
    Holds the local blockchain state for one node.
    """

    def __init__(self) -> None:
        self.chain: list[Block] = [create_genesis_block()]
        self.mempool = Mempool()

    def height(self) -> int:
        return len(self.chain) - 1

    def tip(self) -> Block:
        return self.chain[-1]

    def tip_hash(self) -> bytes:
        return self.tip().block_hash()

    def get_block(self, height: int) -> Block | None:
        if height < 0 or height >= len(self.chain):
            return None

        return self.chain[height]

    def add_transaction(self, tx: Transaction) -> bytes:
        return self.mempool.add(tx)

    def accept_transaction(self, tx: Transaction) -> tuple[bool, bytes, str]:
        tx_hash = tx.tx_hash()

        if not verify_transaction_signature(tx):
            return False, tx_hash, "Invalid transaction signature"

        self.mempool.add(tx)
        return True, tx_hash, "Transaction accepted into mempool"

    def get_mempool_transactions(self) -> list[Transaction]:
        return self.mempool.all_transactions()

    def get_transactions_for_block(self, limit: int | None = None) -> list[Transaction]:
        return self.mempool.transactions_for_block(limit)

    def mempool_size(self) -> int:
        return len(self.mempool)

    def remove_transactions_from_mempool(self, transactions: list[Transaction]) -> None:
        self.mempool.remove_transactions(transactions)

    def block_links_to_previous(self, block: Block, previous_block: Block) -> bool:
        return block.header.prev_hash == previous_block.block_hash()

    def can_append_block(self, block: Block) -> bool:
        if not block.validate():
            return False

        return self.block_links_to_previous(block, self.tip())

    def append_block(self, block: Block) -> bool:
        if not self.can_append_block(block):
            return False

        self.chain.append(block)
        self.remove_transactions_from_mempool(block.transactions)

        return True
