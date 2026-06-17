import unittest

from lab3.chain.blockchain import Blockchain
from lab3.chain.miner import Miner
from lab3.chain.transaction import Transaction


def make_tx(data: bytes = b"data") -> Transaction:
    return Transaction(
        sender_key=b"sender",
        data=data,
        timestamp=1,
        signature=b"signature",
    )


class MinerTests(unittest.TestCase):
    def test_mines_empty_block_on_current_tip(self) -> None:
        blockchain = Blockchain()
        miner = Miner(blockchain, difficulty=4)
        previous_tip_hash = blockchain.tip_hash()

        result = miner.mine_next_block(timestamp=1)

        self.assertTrue(result.appended)
        self.assertEqual(result.previous_height, 0)
        self.assertEqual(result.new_height, 1)
        self.assertEqual(result.transaction_count, 0)
        self.assertEqual(result.block.header.prev_hash, previous_tip_hash)
        self.assertEqual(blockchain.tip(), result.block)

    def test_mines_mempool_transactions_and_removes_included_transactions(self) -> None:
        blockchain = Blockchain()
        included_tx = make_tx(b"included")
        blockchain.add_transaction(included_tx)
        miner = Miner(blockchain, difficulty=4)

        result = miner.mine_next_block(timestamp=1)

        self.assertTrue(result.appended)
        self.assertEqual(result.transaction_count, 1)
        self.assertEqual(result.block.transactions, [included_tx])
        self.assertEqual(blockchain.mempool_size(), 0)

    def test_mines_all_mempool_transactions(self) -> None:
        blockchain = Blockchain()
        tx1 = make_tx(b"one")
        tx2 = make_tx(b"two")
        blockchain.add_transaction(tx1)
        blockchain.add_transaction(tx2)
        miner = Miner(blockchain, difficulty=4)

        result = miner.mine_next_block(timestamp=1)

        self.assertTrue(result.appended)
        self.assertEqual(result.block.transactions, [tx1, tx2])
        self.assertEqual(blockchain.mempool_size(), 0)

    def test_job_can_be_mined_then_appended_separately(self) -> None:
        blockchain = Blockchain()
        miner = Miner(blockchain, difficulty=4)

        job = miner.create_job(timestamp=1)
        block = miner.mine_job(job)
        result = miner.append_mined_block(job, block)

        self.assertTrue(result.appended)
        self.assertEqual(result.new_height, 1)
        self.assertEqual(blockchain.tip(), block)

    def test_append_rejects_job_if_tip_changed_while_mining(self) -> None:
        blockchain = Blockchain()
        miner = Miner(blockchain, difficulty=4)

        stale_job = miner.create_job(timestamp=1)
        competing_result = miner.mine_next_block(timestamp=2)
        stale_block = miner.mine_job(stale_job)
        stale_result = miner.append_mined_block(stale_job, stale_block)

        self.assertTrue(competing_result.appended)
        self.assertFalse(stale_result.appended)
        self.assertEqual(blockchain.height(), 1)


class AsyncMinerTests(unittest.IsolatedAsyncioTestCase):
    async def test_threaded_mining_appends_block(self) -> None:
        blockchain = Blockchain()
        miner = Miner(blockchain, difficulty=4)

        result = await miner.mine_next_block_threaded(timestamp=1)

        self.assertIsNotNone(result)
        self.assertTrue(result.appended)
        self.assertEqual(blockchain.height(), 1)


if __name__ == "__main__":
    unittest.main()
