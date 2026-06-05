import asyncio
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.util import run_forever
from ipv8_service import IPv8

from lab3.blockchain_community import BlockchainCommunity
from lab3.config import KEY_FILE
from lab3.registration_community import Lab3RegistrationCommunity


KEY_ALIAS = "my_peer"


async def main() -> None:
    builder = ConfigBuilder().clear_keys().clear_overlays().set_port(0)

    builder.add_key(KEY_ALIAS, "curve25519", str(KEY_FILE))

    builder.add_overlay(
        "Lab3RegistrationCommunity",
        KEY_ALIAS,
        [WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 2.0})],
        default_bootstrap_defs,
        {},
        [("started",)],
    )

    builder.add_overlay(
        "BlockchainCommunity",
        KEY_ALIAS,
        [WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 2.0})],
        default_bootstrap_defs,
        {},
        [("started",)],
    )

    ipv8 = IPv8(
        builder.finalize(),
        extra_communities={
            "Lab3RegistrationCommunity": Lab3RegistrationCommunity,
            "BlockchainCommunity": BlockchainCommunity,
        },
    )

    await ipv8.start()

    register_community: Lab3RegistrationCommunity | None = ipv8.get_overlay(
        Lab3RegistrationCommunity,
    )
    blockchain_community: BlockchainCommunity | None = ipv8.get_overlay(
        BlockchainCommunity,
    )

    if register_community is None or blockchain_community is None:
        raise RuntimeError("Lab 3 overlays failed to start")

    print("IPv8 started for Lab 3", flush=True)
    print(
        "Connecting with public key: "
        f"{blockchain_community.my_peer.public_key.key_to_bin().hex()}",
        flush=True,
    )

    await run_forever()


if __name__ == "__main__":
    asyncio.run(main())
