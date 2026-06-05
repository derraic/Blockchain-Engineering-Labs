import unittest

from lab3.chain import (
    BlockHeader,
    Transaction,
    compute_txs_hash,
    count_leading_zero_bits,
    mine_block,
    sha256,
    valid_pow,
)


class UtilsTests(unittest.TestCase):
    def test_tx_hash_is_32_bytes(self) -> None:
        tx = Transaction(
            sender_key=b"a",
            data=b"hello",
            timestamp=123,
            signature=b"sig",
        )

        self.assertEqual(len(tx.tx_hash()), 32)

    def test_empty_commitment(self) -> None:
        self.assertEqual(compute_txs_hash([]), sha256(b""))

    def test_header_is_84_bytes(self) -> None:
        header = BlockHeader(
            prev_hash=b"\x00" * 32,
            txs_hash=b"\x11" * 32,
            timestamp=1,
            difficulty=8,
            nonce=0,
        )

        self.assertEqual(len(header.pack()), 84)

    def test_leading_zero_bits(self) -> None:
        self.assertEqual(count_leading_zero_bits(b"\x00"), 8)
        self.assertEqual(count_leading_zero_bits(b"\x00\x00"), 16)
        self.assertEqual(count_leading_zero_bits(b"\x0f"), 4)

    def test_mining(self) -> None:
        block = mine_block(
            prev_hash=b"\x00" * 32,
            transactions=[],
            timestamp=1,
            difficulty=12,
        )

        self.assertTrue(valid_pow(block.block_hash(), 12))


if __name__ == "__main__":
    unittest.main()
