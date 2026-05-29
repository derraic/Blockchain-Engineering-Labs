from asyncio import run
from pathlib import Path
import sys
from time import monotonic

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ipv8.community import Community, CommunitySettings
from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.lazy_community import lazy_wrapper
from ipv8.peer import Peer
from ipv8.peerdiscovery.network import PeerObserver
from ipv8.util import run_forever
from ipv8_service import IPv8

from lab2.config import (
    COMMUNITY_ID,
    SERVER_PUBLIC_KEY,
    MY_KEY,
    MEMBER_KEYS,
    TEAMMATE_KEYS,
)
from lab2.payloads import (
    ChallengeRequestPayload,
    ChallengeResponsePayload,
    RegisterPayload,
    RegisterResponsePayload,
    NonceToSign,
    SignatureSubmissionPayload,
    SignatureBundlePayload,
    RoundResultPayload,
)


KEY_FILE = REPO_ROOT / "lab_identity.pem"


class Lab2Community(Community, PeerObserver):
    community_id = COMMUNITY_ID

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)

        self.member_keys = tuple(MEMBER_KEYS)
        self.expected_teammates = tuple(key for key in self.member_keys if key != MY_KEY)
        self.member_key_set = set(self.member_keys)
        self.my_coordinator_round = self.member_keys.index(MY_KEY) + 1

        self.server_peer: Peer | None = None
        self.teammate_peers: dict[bytes, Peer] = {}

        self.registration_sent = False
        self.group_id: str | None = None

        self.current_round: int | None = None
        self.current_nonce: bytes | None = None
        self.challenge_deadline: float | None = None

        self.signatures_by_round: dict[int, dict[bytes, bytes]] = {}
        self.nonce_by_round: dict[int, bytes] = {}
        self.protocol_done = False

        self.retry_interval_seconds = 0.15
        self.last_registration_send_time: float = 0.0
        self.last_challenge_request_time: float = 0.0
        self.last_nonce_send_time_by_round: dict[int, float] = {}
        self.last_bundle_send_time_by_round: dict[int, float] = {}

        self.completed_rounds: set[int] = set()

        self.add_message_handler(RegisterResponsePayload, self.on_register_response)
        self.add_message_handler(ChallengeResponsePayload, self.on_challenge_response)
        self.add_message_handler(NonceToSign, self.on_nonce_to_sign)
        self.add_message_handler(SignatureSubmissionPayload, self.on_signature_submission)
        self.add_message_handler(RoundResultPayload, self.on_round_result)

    def started(self) -> None:
        self.network.add_peer_observer(self)

        my_actual_key = self.my_peer.public_key.key_to_bin()

        if my_actual_key != MY_KEY:
            return

        self.register_task("try_register_group", self.try_register_group, interval=0.2, delay=0.0)
        self.register_task("try_start_round", self.try_start_round, interval=0.2, delay=0.0)
        self.register_task("retry_active_round", self.retry_active_round, interval=0.15, delay=0.0)

    def on_peer_added(self, peer: Peer) -> None:
        key = peer.public_key.key_to_bin()

        if key == SERVER_PUBLIC_KEY:
            self.server_peer = peer
            self.try_register_group()
            self.try_start_round()

        elif key in TEAMMATE_KEYS:
            self.teammate_peers[key] = peer
            self.try_register_group()
            self.try_start_round()

    def on_peer_removed(self, peer: Peer) -> None:
        key = peer.public_key.key_to_bin()

        if key == SERVER_PUBLIC_KEY:
            self.server_peer = None

        elif key in self.teammate_peers:
            del self.teammate_peers[key]

    def all_peers_ready(self) -> bool:
        return (
            self.server_peer is not None
            and all(key in self.teammate_peers for key in self.expected_teammates)
        )

    def coordinator_for_round(self, round_number: int) -> bytes:
        return self.member_keys[round_number - 1]

    def am_i_coordinator_for_round(self, round_number: int) -> bool:
        return MY_KEY == self.coordinator_for_round(round_number)

    def try_register_group(self) -> None:
        if self.protocol_done:
            return

        if self.server_peer is None:
            return

        if self.group_id is not None:
            return

        now = monotonic()

        if (
            self.registration_sent
            and now - self.last_registration_send_time < self.retry_interval_seconds
        ):
            return

        self.registration_sent = True
        self.last_registration_send_time = now

        self.ez_send(
            self.server_peer,
            RegisterPayload(
                self.member_keys[0],
                self.member_keys[1],
                self.member_keys[2],
            )
        )

    @lazy_wrapper(RegisterResponsePayload)
    def on_register_response(self, peer: Peer, payload: RegisterResponsePayload) -> None:
        if peer.public_key.key_to_bin() != SERVER_PUBLIC_KEY:
            return

        if payload.success:
            self.group_id = payload.group_id
            self.try_start_round()
        else:
            self.registration_sent = False

    def try_start_round(self) -> None:
        if self.protocol_done:
            return

        if self.server_peer is None:
            return

        if self.group_id is None:
            return

        if not self.all_peers_ready():
            return

        if self.my_coordinator_round in self.completed_rounds:
            return

        if self.current_round is not None:
            return

        if self.challenge_deadline is not None and monotonic() >= self.challenge_deadline:
            return

        now = monotonic()

        if now - self.last_challenge_request_time < self.retry_interval_seconds:
            return

        self.last_challenge_request_time = now

        self.ez_send(
            self.server_peer,
            ChallengeRequestPayload(self.group_id)
        )

    @lazy_wrapper(ChallengeResponsePayload)
    def on_challenge_response(self, peer: Peer, payload: ChallengeResponsePayload) -> None:
        if peer.public_key.key_to_bin() != SERVER_PUBLIC_KEY:
            return

        if self.protocol_done:
            return

        nonce = payload.nonce
        round_number = payload.round_number

        if round_number in self.completed_rounds:
            return

        if round_number != self.my_coordinator_round:
            return

        if not self.am_i_coordinator_for_round(round_number):
            return

        previous_nonce = self.nonce_by_round.get(round_number)
        if previous_nonce == nonce and self.current_round == round_number:
            self.try_submit_signature_bundle(round_number)
            return

        self.challenge_deadline = payload.deadline
        self.current_round = round_number
        self.current_nonce = nonce
        self.nonce_by_round[round_number] = nonce

        my_signature = self.sign_nonce(nonce)
        self.signatures_by_round[round_number] = {MY_KEY: my_signature}

        self.send_nonce_to_teammates(nonce, round_number)

        self.try_submit_signature_bundle(round_number)

    def send_nonce_to_teammates(self, nonce: bytes, round_number: int) -> None:
        self.last_nonce_send_time_by_round[round_number] = monotonic()

        for teammate_key in self.expected_teammates:
            teammate_peer = self.teammate_peers.get(teammate_key)

            if teammate_peer is None:
                continue

            self.ez_send(
                teammate_peer,
                NonceToSign(
                    nonce,
                    round_number,
                    self.group_id,
                )
            )

    def resend_nonce_to_missing_teammates(self, nonce: bytes, round_number: int) -> None:
        signatures = self.signatures_by_round.get(round_number, {})

        missing_teammates = [
            key for key in self.expected_teammates
            if key not in signatures
        ]

        if not missing_teammates:
            return

        now = monotonic()
        last_send = self.last_nonce_send_time_by_round.get(round_number, 0.0)

        if now - last_send < self.retry_interval_seconds:
            return

        self.last_nonce_send_time_by_round[round_number] = now

        for teammate_key in missing_teammates:
            teammate_peer = self.teammate_peers.get(teammate_key)

            if teammate_peer is None:
                continue

            self.ez_send(
                teammate_peer,
                NonceToSign(
                    nonce,
                    round_number,
                    self.group_id,
                )
            )

    def retry_active_round(self) -> None:
        if self.protocol_done:
            return

        if self.current_round is None:
            return

        if self.current_nonce is None:
            return

        if self.challenge_deadline is not None and monotonic() >= self.challenge_deadline:
            return

        if self.current_round != self.my_coordinator_round:
            return

        if self.current_round in self.completed_rounds:
            return

        self.resend_nonce_to_missing_teammates(
            self.current_nonce,
            self.current_round,
        )

        self.try_submit_signature_bundle(self.current_round)

    @lazy_wrapper(NonceToSign)
    def on_nonce_to_sign(self, peer: Peer, payload: NonceToSign) -> None:
        sender_key = peer.public_key.key_to_bin()

        if sender_key not in self.member_key_set:
            return

        nonce = payload.nonce
        round_number = payload.round_number
        group_id = payload.group_id

        if round_number in self.completed_rounds:
            return

        if self.group_id is not None and group_id != self.group_id:
            return

        if self.am_i_coordinator_for_round(round_number):
            return

        signature = self.sign_nonce(nonce)

        self.ez_send(
            peer,
            SignatureSubmissionPayload(
                round_number,
                signature,
            )
        )

    @lazy_wrapper(SignatureSubmissionPayload)
    def on_signature_submission(self, peer: Peer, payload: SignatureSubmissionPayload) -> None:
        signer_key = peer.public_key.key_to_bin()
        round_number = payload.round_number
        signature = payload.signature

        if signer_key not in self.member_key_set:
            return

        if round_number != self.my_coordinator_round:
            return

        if not self.am_i_coordinator_for_round(round_number):
            return

        if round_number in self.completed_rounds:
            return

        self.signatures_by_round.setdefault(round_number, {})
        self.signatures_by_round[round_number][signer_key] = signature

        self.try_submit_signature_bundle(round_number)

    def try_submit_signature_bundle(self, round_number: int) -> None:
        if round_number in self.completed_rounds:
            return

        if round_number != self.my_coordinator_round:
            return

        if not self.am_i_coordinator_for_round(round_number):
            return

        if self.server_peer is None or self.group_id is None:
            return

        signatures = self.signatures_by_round.get(round_number, {})

        if self.challenge_deadline is not None and monotonic() >= self.challenge_deadline:
            return

        if any(key not in signatures for key in self.member_keys):
            return

        now = monotonic()
        last_send = self.last_bundle_send_time_by_round.get(round_number, 0.0)

        if now - last_send < self.retry_interval_seconds:
            return

        self.last_bundle_send_time_by_round[round_number] = now

        sig1 = signatures[self.member_keys[0]]
        sig2 = signatures[self.member_keys[1]]
        sig3 = signatures[self.member_keys[2]]

        self.ez_send(
            self.server_peer,
            SignatureBundlePayload(
                self.group_id,
                round_number,
                sig1,
                sig2,
                sig3,
            )
        )

    @lazy_wrapper(RoundResultPayload)
    def on_round_result(self, peer: Peer, payload: RoundResultPayload) -> None:
        if peer.public_key.key_to_bin() != SERVER_PUBLIC_KEY:
            return

        if payload.success and payload.round_number > 0:
            self.completed_rounds.add(payload.round_number)
            self.nonce_by_round.pop(payload.round_number, None)
            self.signatures_by_round.pop(payload.round_number, None)

        if payload.success and payload.round_number == self.current_round:
            self.current_round = None
            self.current_nonce = None

        if payload.rounds_completed >= 3:
            self.protocol_done = True
            return

        if not payload.success:
            message = payload.message.lower()
            if (
                "already completed" in message
                or "budget exceeded" in message
                or "no active challenge" in message
            ):
                self.protocol_done = True
            return

        if payload.round_number == self.my_coordinator_round:
            self.try_start_round()

    def sign_nonce(self, nonce: bytes) -> bytes:
        return self.crypto.create_signature(self.my_peer.key, nonce)


async def main() -> None:
    builder = ConfigBuilder().clear_keys().clear_overlays()

    builder.add_key("lab_key", "curve25519", str(KEY_FILE))

    builder.add_overlay(
        "Lab2Community",
        "lab_key",
        [WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 3.0})],
        default_bootstrap_defs,
        {},
        [("started",)]
    )

    ipv8 = IPv8(
        builder.finalize(),
        extra_communities={"Lab2Community": Lab2Community},
    )

    await ipv8.start()
    await run_forever()


if __name__ == "__main__":
    run(main())
