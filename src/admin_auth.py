"""
src/admin_auth.py
-----------------
Phase 0: password storage + admin authentication for the Human Review gate.

No plaintext password is stored anywhere:

* ``data/admin_credentials.csv`` keeps account *metadata* only
  (``admin_id, full_name, username, department``) — the ``password``
  column has been removed.
* Per-account salted scrypt hashes live in the git-ignored sidecar
  ``data/.admin_hashes.csv`` (columns ``username,password_hash``).

Hashes are self-describing and versioned so parameters can change later
without breaking old entries::

    scrypt$<n>$<r>$<p>$<salt_hex>$<hash_hex>

scrypt (stdlib ``hashlib``) is used instead of bcrypt so no extra
dependency is needed and Python 3.14 is fully supported. Verification is
constant-time via ``hmac.compare_digest``.

CLI
---
    python -m src.admin_auth rotate          # fresh random password per account; prints them ONCE
    python -m src.admin_auth check           # validates layout: no plaintext, every account has a hash
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import string
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_PATH = PROJECT_ROOT / "data" / "admin_credentials.csv"
HASHES_PATH = PROJECT_ROOT / "data" / ".admin_hashes.csv"

# Metadata columns allowed in the accounts file (no password column).
ACCOUNT_COLUMNS = ["admin_id", "full_name", "username", "department"]

# scrypt parameters. N=2**14 @ r=8 uses ~16 MiB, comfortably inside
# CPython/OpenSSL's default maxmem, while being far too slow to brute-force.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SALT_BYTES = 16

# Password charset without lookalike characters (0/O, 1/l/I).
_PASSWORD_ALPHABET = string.ascii_uppercase.replace("I", "").replace("O", "") \
    + string.ascii_lowercase.replace("l", "").replace("o", "") \
    + string.digits.replace("0", "").replace("1", "")


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str, *, n: int = SCRYPT_N, r: int = SCRYPT_R,
                  p: int = SCRYPT_P) -> str:
    """Return a self-describing ``scrypt$n$r$p$salt_hex$hash_hex`` string."""
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=SCRYPT_DKLEN
    )
    return f"scrypt${n}${r}${p}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check of ``password`` against an encoded hash string."""
    try:
        scheme, n_s, r_s, p_s, salt_hex, hash_hex = encoded.split("$")
        if scheme != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_s),
            r=int(r_s),
            p=int(p_s),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# --------------------------------------------------------------------------- #
# Account store
# --------------------------------------------------------------------------- #
def load_accounts() -> pd.DataFrame:
    """Account metadata (no password column). Empty frame if file missing."""
    if not ACCOUNTS_PATH.exists():
        return pd.DataFrame(columns=ACCOUNT_COLUMNS)
    df = pd.read_csv(ACCOUNTS_PATH, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_hashes() -> dict[str, str]:
    """Map username -> encoded hash from the sidecar. Empty if missing."""
    secret_json = os.environ.get("ADMIN_HASHES_JSON", "").strip()
    if secret_json:
        try:
            values = json.loads(secret_json)
            if not isinstance(values, dict):
                raise ValueError("ADMIN_HASHES_JSON must be a JSON object")
            return {str(username): str(password_hash) for username, password_hash in values.items()}
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("ADMIN_HASHES_JSON is not valid JSON") from exc
    if not HASHES_PATH.exists():
        return {}
    df = pd.read_csv(HASHES_PATH, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    if "username" not in df.columns or "password_hash" not in df.columns:
        raise ValueError(
            f"{HASHES_PATH.name} must have columns 'username,password_hash'."
        )
    return dict(zip(df["username"], df["password_hash"]))


def authenticate(username: str, password: str) -> dict | None:
    """Validate credentials; return the account row dict or None.

    Mirrors the previous contract used by the login form: the returned
    dict has keys ``username``, ``full_name``, ``department`` (and the
    rest of the metadata columns).
    """
    accounts = load_accounts()
    if accounts.empty:
        return None
    hashes = load_hashes()
    match = accounts[accounts["username"] == username]
    if match.empty:
        return None
    encoded = hashes.get(username)
    if not encoded or not verify_password(password, encoded):
        return None
    return match.iloc[0].to_dict()


# --------------------------------------------------------------------------- #
# Rotation
# --------------------------------------------------------------------------- #
def _random_password(length: int = 14) -> str:
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


def rotate_passwords(length: int = 14) -> list[dict[str, str]]:
    """Regenerate every account's password; persist only hashes.

    Returns one dict per account: ``{username, full_name, password}`` —
    the plaintext values are printed once by the CLI and never stored.
    """
    accounts = load_accounts()
    if accounts.empty:
        raise SystemExit(
            f"No accounts found in {ACCOUNTS_PATH}. Create it first with columns "
            f"{ACCOUNT_COLUMNS}."
        )
    if "username" not in accounts.columns or "full_name" not in accounts.columns:
        raise SystemExit(
            f"{ACCOUNTS_PATH} must contain 'username' and 'full_name' columns."
        )

    rows = []
    result = []
    for _, account in accounts.iterrows():
        username = str(account["username"])
        plain = _random_password(length)
        rows.append({"username": username, "password_hash": hash_password(plain)})
        result.append(
            {"username": username, "full_name": str(account["full_name"]),
             "password": plain}
        )

    # Strip any plaintext password column from the accounts file (metadata
    # only from here on) and persist the hashes sidecar.
    meta_cols = [c for c in ACCOUNT_COLUMNS if c in accounts.columns]
    accounts[meta_cols].to_csv(ACCOUNTS_PATH, index=False)

    HASHES_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(HASHES_PATH, index=False)
    # Ensure hashes are not world-readable.
    try:
        os.chmod(HASHES_PATH, 0o600)
    except OSError:
        pass  # Windows: chmod is a no-op for this purpose
    return result


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_check() -> int:
    problems: list[str] = []

    accounts = load_accounts()
    if accounts.empty:
        problems.append(f"{ACCOUNTS_PATH} is missing or empty")
    else:
        if "password" in accounts.columns:
            problems.append(
                f"{ACCOUNTS_PATH} still has a 'password' column — remove it."
            )
        for col in ACCOUNT_COLUMNS:
            if col not in accounts.columns:
                problems.append(f"{ACCOUNTS_PATH} missing column '{col}'")
        dupes = accounts["username"].duplicated()
        if dupes.any():
            problems.append("Duplicate usernames in accounts file")

    hashes = load_hashes()
    if accounts is not None and not accounts.empty and "username" in accounts.columns:
        missing = set(accounts["username"]) - set(hashes)
        if missing:
            problems.append(
                f"No hash for {len(missing)} account(s); run "
                "'python -m src.admin_auth rotate'."
            )

    # Round-trip sanity check on a throwaway value (never touches real hashes).
    probe = "phase0-probe"
    if not verify_password(probe, hash_password(probe)):
        problems.append("Hash round-trip failed — verifier is broken")

    if problems:
        for msg in problems:
            print(f"  FAIL  {msg}")
        return 1
    print(f"OK  {len(accounts)} account(s), {len(hashes)} hash(es), "
          f"no plaintext, round-trip passes.")
    return 0


def _cmd_rotate(length: int) -> int:
    fresh = rotate_passwords(length=length)
    print("Rotated admin passwords. Plaintext shown ONCE — save them now:")
    print()
    for item in fresh:
        print(f"  {item['username']:<12} {item['full_name']:<22} {item['password']}")
    print()
    print(f"Hashes written to {HASHES_PATH} (git-ignored, no plaintext stored).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.admin_auth",
        description="Phase 0 admin auth: rotate per-account passwords or check layout.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Validate that no plaintext is stored and every account has a hash.")
    rotate = sub.add_parser("rotate", help="Generate a fresh random password per account (prints them once).")
    rotate.add_argument("--length", type=int, default=14, help="Password length (default 14).")
    args = parser.parse_args(argv)
    if args.command == "check":
        return _cmd_check()
    return _cmd_rotate(args.length)


if __name__ == "__main__":
    sys.exit(main())