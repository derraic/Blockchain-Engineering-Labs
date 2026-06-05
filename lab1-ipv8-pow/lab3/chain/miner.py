import asyncio
from dataclasses import dataclass
from time import time

from lab3.chain.block import Block
from lab3.chain.blockchain import Blockchain
from lab3.chain.pow import BLOCK_DIFFICULTY, mine_block
from lab3.chain.transaction import Transaction


@dataclass
class MiningJob:
    previous_height: int
    prev_hash: bytes
    transactions: list[Transaction]
    timestamp: int


@dataclass
class MiningResult:
    block: Block
    appended: bool
    previous_height: int
    new_height: int
    transaction_count: int


class Miner:
    """
    Coordinates single-node mining against the local Blockchain state.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        difficulty: int = BLOCK_DIFFICULTY,
    ) -> None:
        self.blockchain = blockchain
        self.difficulty = difficulty
        self.is_mining = False

    def mine_next_block(self, timestamp: int | None = None) -> MiningResult:
        job = self.create_job(timestamp)
        block = self.mine_job(job)
        return self.append_mined_block(job, block)

    async def mine_next_block_threaded(
        self,
        timestamp: int | None = None,
    ) -> MiningResult | None:
        if self.is_mining:
            return None

        self.is_mining = True

        try:
            job = self.create_job(timestamp)
            block = await asyncio.to_thread(self.mine_job, job)
            return self.append_mined_block(job, block)
        finally:
            self.is_mining = False

    def create_job(self, timestamp: int | None = None) -> MiningJob:
        previous_height = self.blockchain.height()
        return MiningJob(
            previous_height=previous_height,
            prev_hash=self.blockchain.tip_hash(),
            transactions=self.blockchain.get_transactions_for_block(),
            timestamp=timestamp if timestamp is not None else int(time()),
        )

    def mine_job(self, job: MiningJob) -> Block:
        return mine_block(
            prev_hash=job.prev_hash,
            transactions=job.transactions,
            timestamp=job.timestamp,
            difficulty=self.difficulty,
        )

    def append_mined_block(self, job: MiningJob, block: Block) -> MiningResult:
        appended = self.blockchain.append_block(block)

        return MiningResult(
            block=block,
            appended=appended,
            previous_height=job.previous_height,
            new_height=self.blockchain.height(),
            transaction_count=len(job.transactions),
        )
