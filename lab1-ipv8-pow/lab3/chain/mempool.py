from lab3.chain.transaction import Transaction


class Mempool:
    """
    Stores transactions that are known locally but not included in the best chain.
    """

    def __init__(self) -> None:
        self.transactions: dict[bytes, Transaction] = {}

    def add(self, tx: Transaction) -> bytes:
        tx_hash = tx.tx_hash()
        self.transactions[tx_hash] = tx
        return tx_hash

    def get(self, tx_hash: bytes) -> Transaction | None:
        return self.transactions.get(tx_hash)

    def contains(self, tx_hash: bytes) -> bool:
        return tx_hash in self.transactions

    def all_transactions(self) -> list[Transaction]:
        return list(self.transactions.values())

    def transactions_for_block(self, limit: int | None = None) -> list[Transaction]:
        transactions = self.all_transactions()
        if limit is None:
            return transactions
        return transactions[:limit]

    def remove(self, tx_hash: bytes) -> None:
        self.transactions.pop(tx_hash, None)

    def remove_transactions(self, transactions: list[Transaction]) -> None:
        for tx in transactions:
            self.remove(tx.tx_hash())

    def __len__(self) -> int:
        return len(self.transactions)
