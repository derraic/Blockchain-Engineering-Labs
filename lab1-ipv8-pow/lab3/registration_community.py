from time import monotonic

from ipv8.community import Community, CommunitySettings
from ipv8.lazy_community import lazy_wrapper
from ipv8.peer import Peer
from ipv8.peerdiscovery.network import PeerObserver

from lab3.config import (
    BLOCKCHAIN_COMMUNITY_ID,
    GROUP_ID,
    REGISTRATION_COMMUNITY_ID,
    SERVER_PUBLIC_KEY,
)
from lab3.payloads import (
    RegisterBlockchainPayload,
    RegisterBlockchainResponsePayload,
)


class Lab3RegistrationCommunity(Community, PeerObserver):
    community_id = REGISTRATION_COMMUNITY_ID

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)

        self.server_peer: Peer | None = None
        self.registration_sent = False
        self.last_registration_send_time = 0.0
        self.retry_interval_seconds = 2.0

        self.add_message_handler(
            RegisterBlockchainResponsePayload,
            self.on_register_blockchain_response,
        )

    def started(self) -> None:
        self.network.add_peer_observer(self)
        print("Lab 3 registration community started", flush=True)
        print(f"Group id: {GROUP_ID}", flush=True)
        print(f"Blockchain community id: {BLOCKCHAIN_COMMUNITY_ID.hex()}", flush=True)

        self.register_task(
            "try_register_blockchain",
            self.try_register_blockchain,
            interval=1.0,
            delay=0.0,
        )

    def on_peer_added(self, peer: Peer) -> None:
        if peer.public_key.key_to_bin() == SERVER_PUBLIC_KEY:
            self.server_peer = peer
            print("Found Lab 3 registration server", flush=True)
            self.try_register_blockchain()

    def on_peer_removed(self, peer: Peer) -> None:
        if peer.public_key.key_to_bin() == SERVER_PUBLIC_KEY:
            self.server_peer = None

    def try_register_blockchain(self) -> None:
        if self.server_peer is None:
            return

        now = monotonic()
        if (
            self.registration_sent
            and now - self.last_registration_send_time < self.retry_interval_seconds
        ):
            return

        self.registration_sent = True
        self.last_registration_send_time = now

        print("Registering blockchain community with Lab 3 server", flush=True)
        self.ez_send(
            self.server_peer,
            RegisterBlockchainPayload(GROUP_ID, BLOCKCHAIN_COMMUNITY_ID),
        )

    @lazy_wrapper(RegisterBlockchainResponsePayload)
    def on_register_blockchain_response(
        self,
        peer: Peer,
        payload: RegisterBlockchainResponsePayload,
    ) -> None:
        if peer.public_key.key_to_bin() != SERVER_PUBLIC_KEY:
            return

        print(
            "Registration response: "
            f"success={payload.success}, message={payload.message}",
            flush=True,
        )

        if not payload.success:
            self.registration_sent = False
