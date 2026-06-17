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

    def has_transaction_in_mempool(self, tx_hash: bytes) -> bool:
        return self.mempool.contains(tx_hash)

    def has_transaction_in_chain(self, tx_hash: bytes) -> bool:
        for block in self.chain:
            for tx in block.transactions:
                if tx.tx_hash() == tx_hash:
                    return True

        return False

    def accept_transaction(self, tx: Transaction) -> tuple[bool, bytes, str]:
        tx_hash = tx.tx_hash()

        if not verify_transaction_signature(tx):
            return False, tx_hash, "Invalid transaction signature"

        if self.mempool.contains(tx_hash):
            return True, tx_hash, "Transaction already in mempool"

        self.mempool.add(tx)
        return True, tx_hash, "Transaction accepted into mempool"

    def get_mempool_transactions(self) -> list[Transaction]:
        return self.mempool.all_transactions()

    def get_transactions_for_block(self) -> list[Transaction]:
        return [
            tx
            for tx in self.mempool.all_transactions()
            if not self.has_transaction_in_chain(tx.tx_hash())
        ]

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

    def validate_chain(self, candidate_chain: list[Block]) -> bool:
        if not candidate_chain:
            return False

        if candidate_chain[0].block_hash() != create_genesis_block().block_hash():
            return False

        for height, block in enumerate(candidate_chain):
            if not block.validate():
                return False

            if height == 0:
                continue

            if not self.block_links_to_previous(block, candidate_chain[height - 1]):
                return False

        return True

    def replace_chain_if_longer(self, candidate_chain: list[Block]) -> bool:
        """
        Atomically adopt a complete, validated longer chain.

        Transactions from orphaned local blocks return to the mempool unless
        they are also confirmed by the new canonical chain.
        """
        if len(candidate_chain) <= len(self.chain):
            return False

        if not self.validate_chain(candidate_chain):
            return False

        new_chain_tx_hashes = {
            tx.tx_hash()
            for block in candidate_chain
            for tx in block.transactions
        }
        pending_transactions = {
            tx.tx_hash(): tx
            for tx in self.mempool.all_transactions()
            if tx.tx_hash() not in new_chain_tx_hashes
        }

        for block in self.chain[1:]:
            for tx in block.transactions:
                tx_hash = tx.tx_hash()
                if tx_hash not in new_chain_tx_hashes:
                    pending_transactions[tx_hash] = tx

        self.chain = list(candidate_chain)
        self.mempool.replace(list(pending_transactions.values()))
        return True
