from ipv8.messaging.lazy_payload import VariablePayload, vp_compile


@vp_compile
class RegisterBlockchainPayload(VariablePayload):
    msg_id = 1
    names = ["group_id", "community_id"]
    format_list = ["varlenHutf8", "varlenH"]


@vp_compile
class RegisterBlockchainResponsePayload(VariablePayload):
    msg_id = 2
    names = ["success", "message"]
    format_list = ["?", "varlenHutf8"]


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
    names = [
        "height",
        "prev_hash",
        "txs_hash",
        "timestamp",
        "difficulty",
        "nonce",
        "block_hash",
        "tx_hashes",
    ]
    format_list = ["q", "varlenH", "varlenH", "q", "q", "q", "varlenH", "varlenH"]

@vp_compile
class TransactionBroadcastPayload(VariablePayload):
    msg_id = 7
    names = ["sender_key", "data", "timestamp", "signature"]
    format_list = ["varlenH", "varlenH", "q", "varlenH"]

@vp_compile
class BlockResponsePayload(VariablePayload):
    msg_id = 8
    names = [
        "height",
        "prev_hash",
        "txs_hash",
        "timestamp",
        "difficulty",
        "nonce",
        "block_hash",
        "tx_hashes",
    ]
    format_list = ["q", "varlenH", "varlenH", "q", "q", "q", "varlenH", "varlenH"]
