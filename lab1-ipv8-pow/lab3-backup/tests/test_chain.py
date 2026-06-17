import unittest
from unittest.mock import patch

from lab3.chain.blockchain import Blockchain
from lab3.chain.mempool import Mempool
from lab3.chain.pow import mine_block
from lab3.chain.transaction import Transaction


def make_tx(data: bytes = b"data") -> Transaction:
    return Transaction(
        sender_key=b"sender",
        data=data,
        timestamp=1,
        signature=b"signature",
    )


class MempoolTests(unittest.TestCase):
    def test_add_deduplicates_by_transaction_hash(self) -> None:
        mempool = Mempool()
        tx = make_tx()

        tx_hash = mempool.add(tx)
        mempool.add(tx)

        self.assertEqual(len(mempool), 1)
        self.assertIs(mempool.get(tx_hash), tx)

    def test_remove_transactions_ignores_missing_transactions(self) -> None:
        mempool = Mempool()
        tx = make_tx()

        mempool.remove_transactions([tx])

        self.assertEqual(len(mempool), 0)

    def test_transactions_for_block_respects_limit(self) -> None:
        mempool = Mempool()
        tx1 = make_tx(b"one")
        tx2 = make_tx(b"two")
        mempool.add(tx1)
        mempool.add(tx2)

        self.assertEqual(mempool.transactions_for_block(limit=1), [tx1])

    def test_replace_deduplicates_by_transaction_hash(self) -> None:
        mempool = Mempool()
        tx = make_tx()

        mempool.replace([tx, tx])

        self.assertEqual(mempool.all_transactions(), [tx])


class BlockchainTests(unittest.TestCase):
    def test_starts_with_genesis_block(self) -> None:
        blockchain = Blockchain()

        self.assertEqual(blockchain.height(), 0)
        self.assertEqual(blockchain.tip().header.prev_hash, b"\x00" * 32)

    def test_accept_transaction_rejects_invalid_signature(self) -> None:
        blockchain = Blockchain()
        tx = make_tx()

        with patch("lab3.chain.blockchain.verify_transaction_signature", return_value=False):
            success, tx_hash, message = blockchain.accept_transaction(tx)

        self.assertFalse(success)
        self.assertEqual(tx_hash, tx.tx_hash())
        self.assertEqual(message, "Invalid transaction signature")
        self.assertEqual(blockchain.mempool_size(), 0)

    def test_accept_transaction_deduplicates_valid_transaction(self) -> None:
        blockchain = Blockchain()
        tx = make_tx()

        with patch("lab3.chain.blockchain.verify_transaction_signature", return_value=True):
            first = blockchain.accept_transaction(tx)
            second = blockchain.accept_transaction(tx)

        self.assertTrue(first[0])
        self.assertEqual(first[2], "Transaction accepted into mempool")
        self.assertTrue(second[0])
        self.assertEqual(second[2], "Transaction already in mempool")
        self.assertEqual(blockchain.mempool_size(), 1)

    def test_append_block_removes_included_transactions_from_mempool(self) -> None:
        blockchain = Blockchain()
        included_tx = make_tx(b"included")
        pending_tx = make_tx(b"pending")
        blockchain.add_transaction(included_tx)
        blockchain.add_transaction(pending_tx)

        block = mine_block(
            prev_hash=blockchain.tip_hash(),
            transactions=[included_tx],
            timestamp=1,
            difficulty=4,
        )

        self.assertTrue(blockchain.append_block(block))
        self.assertEqual(blockchain.height(), 1)
        self.assertFalse(blockchain.has_transaction_in_mempool(included_tx.tx_hash()))
        self.assertTrue(blockchain.has_transaction_in_mempool(pending_tx.tx_hash()))
        self.assertTrue(blockchain.has_transaction_in_chain(included_tx.tx_hash()))

    def test_get_transactions_for_block_excludes_confirmed_transactions(self) -> None:
        blockchain = Blockchain()
        confirmed_tx = make_tx(b"confirmed")
        pending_tx = make_tx(b"pending")
        blockchain.add_transaction(confirmed_tx)
        blockchain.add_transaction(pending_tx)

        block = mine_block(
            prev_hash=blockchain.tip_hash(),
            transactions=[confirmed_tx],
            timestamp=1,
            difficulty=4,
        )
        self.assertTrue(blockchain.append_block(block))

        blockchain.add_transaction(confirmed_tx)

        self.assertEqual(blockchain.get_transactions_for_block(), [pending_tx])

    def test_rejects_block_that_does_not_extend_tip(self) -> None:
        blockchain = Blockchain()
        block = mine_block(
            prev_hash=b"\x11" * 32,
            transactions=[],
            timestamp=1,
            difficulty=0,
        )

        self.assertFalse(blockchain.append_block(block))
        self.assertEqual(blockchain.height(), 0)

    def test_replaces_chain_only_with_complete_valid_longer_chain(self) -> None:
        blockchain = Blockchain()
        first = mine_block(
            prev_hash=blockchain.tip_hash(),
            transactions=[],
            timestamp=1,
            difficulty=0,
        )
        second = mine_block(
            prev_hash=first.block_hash(),
            transactions=[],
            timestamp=2,
            difficulty=0,
        )

        self.assertFalse(blockchain.replace_chain_if_longer([blockchain.chain[0], second]))
        self.assertEqual(blockchain.height(), 0)

        self.assertTrue(
            blockchain.replace_chain_if_longer(
                [blockchain.chain[0], first, second],
            )
        )
        self.assertEqual(blockchain.height(), 2)

    def test_reorg_restores_orphaned_transactions_to_mempool(self) -> None:
        blockchain = Blockchain()
        orphaned_tx = make_tx(b"orphaned")
        still_confirmed_tx = make_tx(b"still-confirmed")
        pending_tx = make_tx(b"pending")
        blockchain.add_transaction(orphaned_tx)
        blockchain.add_transaction(still_confirmed_tx)
        blockchain.add_transaction(pending_tx)

        local_block = mine_block(
            prev_hash=blockchain.tip_hash(),
            transactions=[orphaned_tx, still_confirmed_tx],
            timestamp=1,
            difficulty=0,
        )
        self.assertTrue(blockchain.append_block(local_block))

        genesis = blockchain.chain[0]
        replacement_one = mine_block(
            prev_hash=genesis.block_hash(),
            transactions=[still_confirmed_tx],
            timestamp=2,
            difficulty=0,
        )
        replacement_two = mine_block(
            prev_hash=replacement_one.block_hash(),
            transactions=[],
            timestamp=3,
            difficulty=0,
        )

        self.assertTrue(
            blockchain.replace_chain_if_longer(
                [genesis, replacement_one, replacement_two],
            )
        )
        self.assertTrue(blockchain.has_transaction_in_mempool(orphaned_tx.tx_hash()))
        self.assertTrue(blockchain.has_transaction_in_mempool(pending_tx.tx_hash()))
        self.assertFalse(
            blockchain.has_transaction_in_mempool(still_confirmed_tx.tx_hash())
        )

    def test_does_not_replace_with_equal_length_fork(self) -> None:
        blockchain = Blockchain()
        local_block = mine_block(
            prev_hash=blockchain.tip_hash(),
            transactions=[],
            timestamp=1,
            difficulty=0,
        )
        self.assertTrue(blockchain.append_block(local_block))

        competing_block = mine_block(
            prev_hash=blockchain.chain[0].block_hash(),
            transactions=[],
            timestamp=2,
            difficulty=0,
        )

        self.assertFalse(
            blockchain.replace_chain_if_longer(
                [blockchain.chain[0], competing_block],
            )
        )
        self.assertEqual(blockchain.tip(), local_block)


if __name__ == "__main__":
    unittest.main()
