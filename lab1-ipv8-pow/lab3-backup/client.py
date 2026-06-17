import argparse
import asyncio
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.util import run_forever
from ipv8_service import IPv8

from lab3.communities.blockchain_community import BlockchainCommunity
from lab3.communities.registration import Lab3RegistrationCommunity
from lab3.config import KEY_FILE


KEY_ALIAS = "my_peer"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Lab 3 blockchain node")
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register this blockchain community with the Lab 3 server",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    builder = ConfigBuilder().clear_keys().clear_overlays().set_port(0)

    builder.add_key(KEY_ALIAS, "curve25519", str(KEY_FILE))

    extra_communities = {
        "BlockchainCommunity": BlockchainCommunity,
    }

    if args.register:
        builder.add_overlay(
            "Lab3RegistrationCommunity",
            KEY_ALIAS,
            [WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 2.0})],
            default_bootstrap_defs,
            {},
            [("started",)],
        )
        extra_communities["Lab3RegistrationCommunity"] = Lab3RegistrationCommunity

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
        extra_communities=extra_communities,
    )

    await ipv8.start()

    blockchain_community: BlockchainCommunity | None = ipv8.get_overlay(
        BlockchainCommunity,
    )

    if blockchain_community is None:
        raise RuntimeError("Lab 3 overlays failed to start")

    if args.register and ipv8.get_overlay(Lab3RegistrationCommunity) is None:
        raise RuntimeError("Lab 3 registration overlay failed to start")

    if args.register:
        register_community: Lab3RegistrationCommunity | None = ipv8.get_overlay(
            Lab3RegistrationCommunity,
        )
        if register_community is not None:
            register_community.set_registration_gate(
                blockchain_community.all_teammates_ready,
            )

    print("IPv8 started for Lab 3", flush=True)
    print(f"Registration enabled: {args.register}", flush=True)
    print(
        "Connecting with public key: "
        f"{blockchain_community.my_peer.public_key.key_to_bin().hex()}",
        flush=True,
    )

    await run_forever()


if __name__ == "__main__":
    asyncio.run(main())
