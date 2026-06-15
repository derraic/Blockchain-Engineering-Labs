from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lab3.chain.blockchain import Blockchain
from lab3.chain.miner import Miner
from lab3.chain.transaction import Transaction


def short_hex(value: bytes, length: int = 16) -> str:
    hex_value = value.hex()
    if len(hex_value) <= length:
        return hex_value
    return f"{hex_value[:length]}..."


def make_mock_tx(index: int) -> Transaction:
    return Transaction(
        sender_key=f"mock-sender-{index}".encode(),
        data=f"mock transaction {index}".encode(),
        timestamp=index,
        signature=f"mock-signature-{index}".encode(),
    )


def print_transaction(tx: Transaction, index: int) -> None:
    print(f"      tx[{index}]")
    print(f"        hash:       {tx.tx_hash().hex()}")
    print(f"        sender_key: {tx.sender_key!r}")
    print(f"        data:       {tx.data!r}")
    print(f"        timestamp:  {tx.timestamp}")
    print(f"        signature:  {tx.signature!r}")


def print_chain(blockchain: Blockchain) -> None:
    print(f"Chain height: {blockchain.height()}")
    for height, block in enumerate(blockchain.chain):
        print(f"  block[{height}]")
        print(f"    block_hash: {block.block_hash().hex()}")
        print("    header:")
        print(f"      prev_hash:  {block.header.prev_hash.hex()}")
        print(f"      txs_hash:   {block.header.txs_hash.hex()}")
        print(f"      timestamp:  {block.header.timestamp}")
        print(f"      difficulty: {block.header.difficulty}")
        print(f"      nonce:      {block.header.nonce}")
        print(f"      packed:     {short_hex(block.header.pack(), 64)}")
        print(f"    transactions: {len(block.transactions)}")

        if not block.transactions:
            print("      none")
            continue

        for tx_index, tx in enumerate(block.transactions):
            print_transaction(tx, tx_index)


def main() -> None:
    blockchain = Blockchain()
    miner = Miner(blockchain, difficulty=4)

    for i in range(1, 4):
        tx = make_mock_tx(i)
        blockchain.add_transaction(tx)
        print(f"Added mock tx {i}: {tx.tx_hash().hex()}")

    print(f"Mempool before mining: {blockchain.mempool_size()}")

    result = miner.mine_next_block(timestamp=1)
    print(
        "Mined block "
        f"height={result.new_height} "
        f"appended={result.appended} "
        f"txs={result.transaction_count}"
    )
    print(f"Mempool after mining: {blockchain.mempool_size()}")
    print_chain(blockchain)

    empty_result = miner.mine_next_block(timestamp=2)
    print(
        "Mined empty block "
        f"height={empty_result.new_height} "
        f"appended={empty_result.appended} "
        f"txs={empty_result.transaction_count}"
    )
    print_chain(blockchain)


if __name__ == "__main__":
    main()
