from asyncio import run
from ipv8.community import Community, CommunitySettings
from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.lazy_community import lazy_wrapper
from ipv8.messaging.lazy_payload import VariablePayload, vp_compile
from ipv8.peer import Peer
from ipv8.peerdiscovery.network import PeerObserver
from ipv8.util import run_forever
from ipv8_service import IPv8


EMAIL = "dajsamsoedien@tudelft.nl"
GITHUB_URL = "https://github.com/derraic/Blockchain-Engineering-Labs"
NONCE = 45573537

COMMUNITY_ID = bytes.fromhex("2c1cc6e35ff484f99ebdfb6108477783c0102881")

server_public_key = bytes.fromhex("4c69624e61434c504b3a86b23934a28d669c390e2d1fc0b0870706c4591cc0cb178bc5a811da6d87d27ef319b2638ef60cc8d119724f4c53a1ebfad919c3ac4136c501ce5c09364e0ebb")

@vp_compile
class SubmissionPayload(VariablePayload):
    msg_id = 1
    format_list = ["varlenHutf8", "varlenHutf8", "q"]
    names = ["email", "github_url", "nonce"]


@vp_compile
class ResponsePayload(VariablePayload):
    msg_id = 2
    format_list = ["?", "varlenHutf8"]
    names = ["success", "message"]


class LabCommunity(Community, PeerObserver):
    community_id = COMMUNITY_ID

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)

        self.submitted = False

        self.add_message_handler(ResponsePayload, self.on_response)

    def started(self) -> None:
        self.network.add_peer_observer(self)

        self.register_task("try_submit", self.try_submit, interval=5.0, delay=1.0)

    def on_peer_added(self, peer: Peer) -> None:
        if self.is_server(peer):
            print("Found server peer")
            self.send_submission(peer)

    def on_peer_removed(self, peer: Peer) -> None:
        pass

    def try_submit(self) -> None:
        if self.submitted:
            return

        for peer in self.get_peers():
            if self.is_server(peer):
                print("Found server peer")
                self.send_submission(peer)
                return

        print("Serve not foud yet. Known peers:", len(self.get_peers()))

    def is_server(self, peer: Peer) -> bool:
        return peer.public_key.key_to_bin() == server_public_key

    def send_submission(self, peer: Peer) -> None:
        if self.submitted:
            return

        self.submitted = True

        print("Sending submission")
        print("Email:", EMAIL)
        print("GitHub URL:", GITHUB_URL)
        print("Nonce:", NONCE)

        self.ez_send(peer, SubmissionPayload(EMAIL, GITHUB_URL, NONCE))

    @lazy_wrapper(ResponsePayload)
    def on_response(self, peer: Peer, payload: ResponsePayload) -> None:
        if not self.is_server(peer):
            print("Ignoring response frm non server peer:", peer)
            return

        print("Server response:")
        print("success =", payload.success)
        print("message =", payload.message)

async def main() -> None:
    builder = ConfigBuilder().clear_keys().clear_overlays()

    builder.add_key("lab_key", "curve25519", "lab_identity.pem")

    builder.add_overlay(
        "LabCommunity",
        "lab_key",
        [WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 3.0})],
        default_bootstrap_defs,
        {},
        [("started",)]
    )

    ipv8 = IPv8(
        builder.finalize(),
        extra_communities={"LabCommunity": LabCommunity},
    )

    await ipv8.start()

    overlay = ipv8.get_overlay(LabCommunity)
    print("IPv8 started.")

    my_peer = overlay.my_peer
    public_bytes = my_peer.public_key.key_to_bin()
    print(f"Connecting With Public Key: {public_bytes.hex()}")

    await run_forever()



if __name__ == "__main__":
    run(main())


        