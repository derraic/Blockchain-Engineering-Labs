from ipv8.community import Community, CommunitySettings
from ipv8.lazy_community import lazy_wrapper
from ipv8.peer import Peer
from ipv8.peerdiscovery.network import PeerObserver

from lab3.blockchain import Blockchain
from lab3.config import (
    BLOCKCHAIN_COMMUNITY_ID,
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
)
from lab3.utils import Transaction


class BlockchainCommunity(Community, PeerObserver):
    community_id = BLOCKCHAIN_COMMUNITY_ID

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)

        self.group_id = GROUP_ID
        self.member_keys = tuple(MEMBER_KEYS)
        self.member_key_set = set(self.member_keys)
        self.server_peer: Peer | None = None
        self.teammate_peers: dict[bytes, Peer] = {}
        self.blockchain = Blockchain()

        self.add_message_handler(SubmitTransactionPayload, self.on_submit_transaction)
        self.add_message_handler(GetChainHeightPayload, self.on_get_chain_height)
        self.add_message_handler(GetBlockPayload, self.on_get_block)

    def started(self) -> None:
        self.network.add_peer_observer(self)
        print(f"Blockchain community started for {MY_NAME}", flush=True)

        actual_key = self.my_peer.public_key.key_to_bin()
        if actual_key != MY_KEY:
            print(
                "Lab 3 key mismatch: running key does not match configured MY_KEY",
                flush=True,
            )

    def on_peer_added(self, peer: Peer) -> None:
        key = peer.public_key.key_to_bin()

        if key == SERVER_PUBLIC_KEY:
            self.server_peer = peer
            print("Found server in blockchain community", flush=True)
        elif key in TEAMMATE_KEYS:
            self.teammate_peers[key] = peer
            print(f"Found teammate in blockchain community: {KEY_NAMES[key]}", flush=True)

    def on_peer_removed(self, peer: Peer) -> None:
        key = peer.public_key.key_to_bin()

        if key == SERVER_PUBLIC_KEY:
            self.server_peer = None
        elif key in self.teammate_peers:
            del self.teammate_peers[key]

    def is_server_peer(self, peer: Peer) -> bool:
        return peer.public_key.key_to_bin() == SERVER_PUBLIC_KEY

    @lazy_wrapper(SubmitTransactionPayload)
    def on_submit_transaction(self, peer: Peer, payload: SubmitTransactionPayload) -> None:
        if not self.is_server_peer(peer):
            print("Ignoring SubmitTransaction from non-server peer", flush=True)
            return

        tx = Transaction(
            sender_key=payload.sender_key,
            data=payload.data,
            timestamp=payload.timestamp,
            signature=payload.signature,
        )

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
            print(f"Mempool size: {len(self.blockchain.mempool)}", flush=True)
        else:
            print(f"Rejected transaction: {message}", flush=True)

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
