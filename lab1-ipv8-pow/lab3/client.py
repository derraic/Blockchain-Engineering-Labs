import asyncio
import logging

logging.getLogger("LabCommunity").setLevel(logging.CRITICAL)

from ipv8.community import *
from ipv8.lazy_community import lazy_wrapper
from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.messaging.lazy_payload import VariablePayload, vp_compile
from ipv8_service import IPv8

COMMUNITY_ID = bytes.fromhex("4c616233426c6f636b636861696e323032365057")
SERVER_PUBLIC_KEY_HEX = "4c69624e61434c504b3ae3fc099fb56ca3b5e1de9a1c843387f2acdbb78b1bd4350ffde518068a0d246344b10d0d8c355fd0d76873e7d7f7838f3715e025af08f791324495e083331ce6"
MEMBER_1_PUBLIC_KEY_HEX = "4c69624e61434c504b3adc31a700de7e0d53fc6c3cfc52e2b8122f35d74def4aaf55b9ccdf81116f5f4f7d8c15de980916c0e953a4f23423ad1ff6abb34dbae4ac3c12bfdb76c0f4e81c" #Darian(ME)
MEMBER_2_PUBLIC_KEY_HEX = "4c69624e61434c504b3a70597fc8337cce9c703a98ae454aef1ba9a0e9ab61a3b84933a606d1ec44466197b54b27c07d167ddfc134d03247b8290a6013d0b4ccc07817272e846aa51e50" # Jayran
MEMBER_3_PUBLIC_KEY_HEX = "4c69624e61434c504b3aea1ebe2bb45bbaef6fd358df15349cf7494ea4c3079bd09876d867e0cd339d5c341269531ea65b0f99daf123b585ebcef5c21d9e17c54d755e5cc5916c024ce4" # Yves

@vp_compile
class SubmitTransactionPayload(VariablePayload):
    msg_id = 1
    names = ["sender_key", "data", "timestamp", "signature"]
    format_list = ["varlenH", "varlenH", "q", "varlenH"]

@vp_compile
class SubmitTransactionResponsePayload(VariablePayload):
    msg_id = 2
    names = ["success", "tx_hash", "message"]
    format_list = ["?", "varlenH", "varlenHutf8"]

@vp_compile
class GetChainHeightPayload(VariablePayload):
    msg_id = 3
    names = ["request_id"]
    format_list = ["q"]

@vp_compile
class ChainHeightResponsePayload(VariablePayload):
    msg_id = 4
    names = ["request_id", "height", "tip_hash"]
    format_list = ["q", "q", "varlenH"]

@vp_compile
class GetBlockPayload(VariablePayload):
    msg_id = 5
    names = ["height"]
    format_list = ["q"]

@vp_compile
class BlockResponsePayload(VariablePayload):
    msg_id = 6
    names = ["height", "prev_hash", "txs_hash", "timestamp", "difficulty", "nonce", "block_hash", "tx_hashes"]
    format_list = ["q", "varlenH", "varlenH", "q", "q", "q", "varlenH", "varlenH"]

class LabCommunity(Community):
    community_id = COMMUNITY_ID

    def started(self):
        print("Lab community started!")
        print("Looking for peers...")

    def __init__(self, settings):
        super().__init__(settings)
        self.add_message_handler(SubmitTransactionResponsePayload, self.on_submit_transaction_response)
        self.add_message_handler(ChainHeightResponsePayload, self.on_chain_height_response)
        self.add_message_handler(BlockResponsePayload, self.on_block_response)

        self.server_peer = None
        self.darian_peer = None
        self.jayran_peer = None
        self.success = False

    @lazy_wrapper(SubmitTransactionResponsePayload)
    def on_submit_transaction_response(self, peer, payload):
        if peer != self.server_peer:
            print("Ignoring response from non-server peer")
            return

        print("SERVER RESPONSE:")
        print(payload)

    @lazy_wrapper(ChainHeightResponsePayload)
    def on_chain_height_response(self, peer, payload):
        # if peer != self.server_peer:
        #     print("Ignoring CHAIN_HEIGHT_RESPONSE from non-server peer")
        #     return
        
        # self.round_number = payload.round_number

        # if self.round_number != 3 or self.success:
        #     print("Not round number 3: ignoring challenge response from round: ", payload.round_number)
        #     return

        # self.signatures[2] = self.sign_nonce(payload.nonce) # Put my own signature last (member 3)
        # # payload = NonceToSign(payload.nonce, payload.round_number, self.group_id)
        # self.ez_send(self.jayran_peer, payload)
        # self.ez_send(self.darian_peer, payload)
        # print("Sent NONCE_TO_SIGN to teammates.")
        return

    @lazy_wrapper(BlockResponsePayload)
    def on_block_response(self, peer, payload):
        # if peer != self.server_peer:
        #     print("Ignoring BLOCK_RESPONSE from non-server peer")
        #     return

        # print("BLOCK RESPONSE:")
        # print(payload)
        # if (payload.success and payload.rounds_completed == 3):
        #     print("Challenge completed successfully!")
        #     self.success = True
        return

    async def find_teammates_and_server(self):
        found_jayran, found_darian, found_server = False, False, False
        while not (found_jayran and found_darian and found_server):
            peers = self.get_peers()
            print(f"Discovered {len(peers)} peer(s)")

            for peer in peers:
                peer_key = peer.public_key.key_to_bin().hex()

                if peer_key == SERVER_PUBLIC_KEY_HEX:
                    print("FOUND THE SERVER!")
                    self.server_peer = peer
                    found_server = True

                elif peer_key == MEMBER_1_PUBLIC_KEY_HEX:   
                    print("Found Darian's node!")
                    self.darian_peer = peer
                    found_darian = True

                elif peer_key == MEMBER_2_PUBLIC_KEY_HEX:
                    print("Found Jayran's node!")
                    self.jayran_peer = peer
                    found_jayran = True

                else:
                    print("Other peer found, skipping ..")

            await asyncio.sleep(1)

        print("Found all required peers!")

async def main():
    builder = ConfigBuilder()

    builder.clear_keys()
    builder.clear_overlays()

    builder.add_key(
        "mynode",
        "curve25519",
        "key.pem"
    )

    builder.add_overlay(
        "LabCommunity",
        "mynode",
        [
            WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 3.0})
        ],
        default_bootstrap_defs,
        {},
        []
    )

    ipv8 = IPv8(
        builder.finalize(),
        extra_communities={
            "LabCommunity": LabCommunity
        }
    )

    await ipv8.start()
 
    overlay = ipv8.get_overlay(LabCommunity)
    print("IPv8 started.")

    my_peer = overlay.my_peer
    public_bytes = my_peer.public_key.key_to_bin()
    print(f"Connecting With Public Key: {public_bytes.hex()}") 
    
    await overlay.find_teammates_and_server()

    try:   
        # while overlay.success == False:
        #     if overlay.group_id != 0:
        #         payload = ChallengeRequestPayload(overlay.group_id)
        #         overlay.ez_send(overlay.server_peer, payload)
        #         print("Sent challenge request to server with group ID:", overlay.group_id)

        #     await asyncio.sleep(0.05)
        await asyncio.sleep(0.1)
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Interrupted by user.\n")
    finally:
        await ipv8.stop()
        print("IPV8 Stopped.")

if __name__ == "__main__":
    asyncio.run(main())