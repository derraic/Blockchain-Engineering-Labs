from ipv8.messaging.lazy_payload import VariablePayload, vp_compile


@vp_compile
class RegisterPayload(VariablePayload):
    msg_id = 1
    format_list = ["varlenH", "varlenH", "varlenH"]
    names = ["member1_key", "member2_key", "member3_key"]


@vp_compile
class RegisterResponsePayload(VariablePayload):
    msg_id = 2
    format_list = ["?", "varlenHutf8", "varlenHutf8"]
    names = ["success", "group_id", "message"]


@vp_compile
class ChallengeRequestPayload(VariablePayload):
    msg_id = 3
    format_list = ["varlenHutf8"]
    names = ["group_id"]


@vp_compile
class ChallengeResponsePayload(VariablePayload):
    msg_id = 4
    format_list = ["varlenH", "q", "d"]
    names = ["nonce", "round_number", "deadline"]


@vp_compile
class SignatureBundlePayload(VariablePayload):
    msg_id = 5
    format_list = ["varlenHutf8", "q", "varlenH", "varlenH", "varlenH"]
    names = ["group_id", "round_number", "sig1", "sig2", "sig3"]


@vp_compile
class RoundResultPayload(VariablePayload):
    msg_id = 6
    format_list = ["?", "q", "q", "varlenHutf8"]
    names = ["success", "round_number", "rounds_completed", "message"]


@vp_compile
class NonceToSign(VariablePayload):
    msg_id = 7
    format_list = ["varlenH", "q", "varlenHutf8"]
    names = ["nonce", "round_number", "group_id"]


@vp_compile
class SignatureSubmissionPayload(VariablePayload):
    msg_id = 8
    format_list = ["q", "varlenH"]
    names = ["round_number", "signature"]
