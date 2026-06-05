from ipv8.community import Community, CommunitySettings
from ipv8.lazy_community import lazy_wrapper
from ipv8.peer import Peer
from ipv8.peerdiscovery.network import PeerObserver

from lab3.chain.blockchain import Blockchain
from lab3.chain.transaction import Transaction
from lab3.config import (
    BLOCKCHAIN_COMMUNITY_ID,
    ENABLE_SERVER_HANDLERS,
    GROUP_ID,
    KEY_NAMES,
    MEMBER_KEYS,
    MY_KEY,
    MY_NAME,
    SERVER_PUBLIC_KEY,
    TEAMMATE_KEYS,
)
from lab3.payloads import (
    BlockResponsePayload,
    ChainHeightResponsePayload,
    GetBlockPayload,
    GetChainHeightPayload,
    SubmitTransactionPayload,
    SubmitTransactionResponsePayload,
    TransactionBroadcastPayload,
)


class BlockchainCommunity(Community, PeerObserver):
    community_id = BLOCKCHAIN_COMMUNITY_ID

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)

        self.group_id = GROUP_ID
        self.member_keys = tuple(MEMBER_KEYS)
        self.expected_teammates = tuple(key for key in self.member_keys if key != MY_KEY)
        self.member_key_set = set(self.member_keys)
        self.server_peer: Peer | None = None
        self.teammate_peers: dict[bytes, Peer] = {}
        self.all_teammates_found_logged = False
        self.blockchain = Blockchain()

        if ENABLE_SERVER_HANDLERS:
            self.add_message_handler(SubmitTransactionPayload, self.on_submit_transaction)
            self.add_message_handler(GetChainHeightPayload, self.on_get_chain_height)
            self.add_message_handler(GetBlockPayload, self.on_get_block)
        self.add_message_handler(
            TransactionBroadcastPayload,
            self.on_transaction_broadcast,
        )

    def started(self) -> None:
        self.network.add_peer_observer(self)
        print(f"Blockchain community started for {MY_NAME}", flush=True)
        if not ENABLE_SERVER_HANDLERS:
            print("Server blockchain handlers disabled for peer discovery test", flush=True)
        print(
            "Looking for teammates in blockchain community: "
            f"{', '.join(KEY_NAMES[key] for key in self.expected_teammates)}",
            flush=True,
        )

        actual_key = self.my_peer.public_key.key_to_bin()
        if actual_key != MY_KEY:
            print(
                "Lab 3 key mismatch: running key does not match configured MY_KEY",
                flush=True,
            )
            return

        self.register_task(
            "report_peer_discovery_status",
            self.report_peer_discovery_status,
            interval=5.0,
            delay=1.0,
        )

    def on_peer_added(self, peer: Peer) -> None:
        key = peer.public_key.key_to_bin()

        if key == SERVER_PUBLIC_KEY:
            self.server_peer = peer
            print("Found server in blockchain community", flush=True)
            return

        if key in TEAMMATE_KEYS:
            already_known = key in self.teammate_peers
            self.teammate_peers[key] = peer

            if not already_known:
                print(
                    "Found teammate in blockchain community: "
                    f"{KEY_NAMES[key]} ({key.hex()})",
                    flush=True,
                )

            self.report_peer_discovery_status()
            return

        if key not in self.member_key_set:
            print(f"Ignoring non-group peer: {key.hex()}", flush=True)

    def on_peer_removed(self, peer: Peer) -> None:
        key = peer.public_key.key_to_bin()

        if key == SERVER_PUBLIC_KEY:
            self.server_peer = None
        elif key in self.teammate_peers:
            del self.teammate_peers[key]
            self.all_teammates_found_logged = False
            print(
                f"Lost teammate in blockchain community: {KEY_NAMES[key]}",
                flush=True,
            )
            self.report_peer_discovery_status()

    def is_server_peer(self, peer: Peer) -> bool:
        return peer.public_key.key_to_bin() == SERVER_PUBLIC_KEY

    def is_teammate_peer(self, peer: Peer) -> bool:
        return peer.public_key.key_to_bin() in TEAMMATE_KEYS

    def all_teammates_ready(self) -> bool:
        return all(key in self.teammate_peers for key in self.expected_teammates)

    def missing_teammate_names(self) -> list[str]:
        return [
            KEY_NAMES[key]
            for key in self.expected_teammates
            if key not in self.teammate_peers
        ]

    def report_peer_discovery_status(self) -> None:
        found_names = [
            KEY_NAMES[key]
            for key in self.expected_teammates
            if key in self.teammate_peers
        ]
        missing_names = self.missing_teammate_names()

        if self.all_teammates_ready():
            if not self.all_teammates_found_logged:
                print(
                    "All teammates found in blockchain community: "
                    f"{', '.join(found_names)}",
                    flush=True,
                )
                self.all_teammates_found_logged = True
            return

        print(
            "Peer discovery status: "
            f"found={found_names or ['none']}, "
            f"missing={missing_names or ['none']}",
            flush=True,
        )

    def transaction_from_payload(
        self,
        payload: SubmitTransactionPayload | TransactionBroadcastPayload,
    ) -> Transaction:
        return Transaction(
            sender_key=payload.sender_key,
            data=payload.data,
            timestamp=payload.timestamp,
            signature=payload.signature,
        )

    def transaction_broadcast_payload(
        self,
        tx: Transaction,
    ) -> TransactionBroadcastPayload:
        return TransactionBroadcastPayload(
            tx.sender_key,
            tx.data,
            tx.timestamp,
            tx.signature,
        )

    def broadcast_transaction_to_teammates(
        self,
        tx: Transaction,
        exclude_peer: Peer | None = None,
    ) -> None:
        excluded_key = (
            exclude_peer.public_key.key_to_bin()
            if exclude_peer is not None
            else None
        )
        payload = self.transaction_broadcast_payload(tx)
        sent_count = 0

        for teammate_key, teammate_peer in self.teammate_peers.items():
            if teammate_key == excluded_key:
                continue

            self.ez_send(teammate_peer, payload)
            sent_count += 1

        print(
            f"Broadcast transaction {tx.tx_hash().hex()} "
            f"to {sent_count} teammate(s)",
            flush=True,
        )

    @lazy_wrapper(SubmitTransactionPayload)
    def on_submit_transaction(self, peer: Peer, payload: SubmitTransactionPayload) -> None:
        if not self.is_server_peer(peer):
            print("Ignoring SubmitTransaction from non-server peer", flush=True)
            return

        tx = self.transaction_from_payload(payload)
        was_known = self.blockchain.has_transaction_in_mempool(tx.tx_hash())
        success, tx_hash, message = self.blockchain.accept_transaction(tx)

        self.ez_send(
            peer,
            SubmitTransactionResponsePayload(
                success,
                tx_hash,
                message,
            ),
        )

        if success:
            print(f"Accepted transaction: {tx_hash.hex()}", flush=True)
            print(f"Mempool size: {self.blockchain.mempool_size()}", flush=True)
            if not was_known:
                self.broadcast_transaction_to_teammates(tx)
        else:
            print(f"Rejected transaction: {message}", flush=True)

    @lazy_wrapper(TransactionBroadcastPayload)
    def on_transaction_broadcast(
        self,
        peer: Peer,
        payload: TransactionBroadcastPayload,
    ) -> None:
        if not self.is_teammate_peer(peer):
            print("Ignoring transaction broadcast from non-teammate peer", flush=True)
            return

        tx = self.transaction_from_payload(payload)
        tx_hash = tx.tx_hash()
        was_known = self.blockchain.has_transaction_in_mempool(tx_hash)
        success, _, message = self.blockchain.accept_transaction(tx)

        if not success:
            print(
                f"Rejected teammate transaction {tx_hash.hex()}: {message}",
                flush=True,
            )
            return

        if was_known:
            print(f"Ignoring already known transaction: {tx_hash.hex()}", flush=True)
            return

        print(
            f"Accepted teammate transaction: {tx_hash.hex()}",
            flush=True,
        )
        print(f"Mempool size: {self.blockchain.mempool_size()}", flush=True)
        self.broadcast_transaction_to_teammates(tx, exclude_peer=peer)

    @lazy_wrapper(GetChainHeightPayload)
    def on_get_chain_height(self, peer: Peer, payload: GetChainHeightPayload) -> None:
        if not self.is_server_peer(peer):
            return

        self.ez_send(
            peer,
            ChainHeightResponsePayload(
                payload.request_id,
                self.blockchain.height(),
                self.blockchain.tip_hash(),
            ),
        )

    @lazy_wrapper(GetBlockPayload)
    def on_get_block(self, peer: Peer, payload: GetBlockPayload) -> None:
        if not self.is_server_peer(peer):
            return

        block = self.blockchain.get_block(payload.height)
        if block is None:
            return

        self.ez_send(
            peer,
            BlockResponsePayload(
                payload.height,
                block.header.prev_hash,
                block.header.txs_hash,
                block.header.timestamp,
                block.header.difficulty,
                block.header.nonce,
                block.block_hash(),
                block.tx_hashes_bytes(),
            ),
        )
