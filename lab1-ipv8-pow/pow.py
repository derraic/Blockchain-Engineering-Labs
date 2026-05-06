import hashlib
import json
import os
import time

email = "dajsamsoedien@tudelft.nl"
utf8_email = email.encode("utf-8")
utf8_newLine = "\n".encode("utf-8")
repo_link = "https://github.com/derraic/Blockchain-Engineering-Labs"
utf8_repo_link = repo_link.encode("utf-8")

STATE_FILE = "pow_state.json"
SAVE_EVERY = 100_000

combination = utf8_email + utf8_newLine + utf8_repo_link + utf8_newLine

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def is_valid_pow(digest):
    return (
        digest[0] == 0
        and digest[1] == 0
        and digest[2] == 0
        and digest[3] < 16
    )

def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "next_nonce": 0,
            "found": False,
            "nonce": None,
            "hash": None,
        }

    with open(STATE_FILE, "r") as f:
        return json.load(f)

#persist and longer range maybe do a time limit and keep track of the last nonce tried and start from there if the time limit is reached

state = load_state()

if state["found"]:
    print("Already found:")
    print("Nonce:", state["nonce"])
    print("Hash:", state["hash"])
    exit()

nonce = state["next_nonce"]
start_time = time.time()

while nonce <= 2**63 - 1:
    nonce_bytes = nonce.to_bytes(8, byteorder="big", signed=False)
    hash_input = combination + nonce_bytes
    hash_output = hashlib.sha256(hash_input).digest()
    if is_valid_pow(hash_output):
        state = {
            "next_nonce": nonce + 1,
            "found": True,
            "nonce": nonce,
            "hash": hash_output.hex(),
            "email": email,
            "repo_url": repo_link,
        }
        save_state(state)

        print("Found!")
        print("Nonce:", nonce)
        print("Hash:", hash_output.hex())
        break

    if nonce % SAVE_EVERY == 0:
        state["next_nonce"] = nonce + 1
        save_state(state)

        elapsed = time.time() - start_time
        print(f"Tried up to nonce {nonce}, elapsed {elapsed:.1f}s")
    nonce += 1