from dataclasses import dataclass

from lab3.chain.bytes import sha256, u64_be


@dataclass
class Transaction:
    """
    A transaction received from the Lab 3 server.

    tx_hash = SHA256(sender_key || data || timestamp_8byte_be || signature)
    """

    sender_key: bytes
    data: bytes
    timestamp: int
    signature: bytes

    def tx_hash(self) -> bytes:
        blob = self.sender_key + self.data + u64_be(self.timestamp) + self.signature
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
