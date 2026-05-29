import hashlib
import json
import time
from pathlib import Path

EMAIL = "dajsamsoedien@tudelft.nl"
REPO_URL = "https://github.com/derraic/Blockchain-Engineering-Labs"

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = REPO_ROOT / "pow_state.json"
SAVE_EVERY = 100_000
MAX_NONCE = 2**63 - 1

POW_STRING = f"{EMAIL}\n{REPO_URL}\n".encode("utf-8")


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_valid_pow(string: bytes) -> bool:
    if string[0] != 0:
        return False
    if string[1] != 0:
        return False
    if string[2] != 0:
        return False
    if string[3] >= 16:
        return False
    return True


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {
            "next_nonce": 0,
            "found": False,
            "nonce": None,
            "hash": None,
        }

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def check_nonce(nonce: int) -> bytes:
    nonce_bytes = nonce.to_bytes(8, byteorder="big", signed=False)
    return hashlib.sha256(POW_STRING + nonce_bytes).digest()


def main() -> None:
    state = load_state()

    if state["found"]:
        print("already found")
        print("nonce:", state["nonce"])
        print("hash:", state["hash"])
        return

    nonce = state["next_nonce"]
    start_time = time.time()

    while nonce <= MAX_NONCE:
        hash_string = check_nonce(nonce)

        if is_valid_pow(hash_string):
            state = {
                "next_nonce": nonce + 1,
                "found": True,
                "nonce": nonce,
                "hash": hash_string.hex(),
                "email": EMAIL,
                "repo_url": REPO_URL,
            }
            save_state(state)

            print("found")
            print("nonce:", nonce)
            print("hash:", hash_string.hex())
            return

        if nonce % SAVE_EVERY == 0:
            state["next_nonce"] = nonce + 1
            save_state(state)

            elapsed = time.time() - start_time
            print(f"tried {nonce}, {elapsed:.1f}s")

        nonce += 1


if __name__ == "__main__":
    main()
