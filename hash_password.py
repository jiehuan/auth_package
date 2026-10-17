#!/usr/bin/env python3
"""Print an APP_USERS entry ("username:scrypt$...") for one account.

Python alternative to `npm run hash-password`, for machines without Node.
Uses only the standard library. Produces exactly the same format and scrypt
parameters as src/server/auth.server.ts, so either tool can be used.

    python3 scripts/hash_password.py hr1
    python3 scripts/hash_password.py hr2

The password is typed without echo. Join the two printed lines with ";" and
store the result as the APP_USERS secret.
"""
import base64
import getpass
import hashlib
import os
import re
import sys

# Must match src/server/auth.server.ts
N, R, P, KEYLEN = 16384, 8, 1, 32


def scrypt(password: bytes, salt: bytes) -> bytes:
    if hasattr(hashlib, "scrypt"):
        return hashlib.scrypt(password, salt=salt, n=N, r=R, p=P, dklen=KEYLEN)
    # Apple's /usr/bin/python3 is built against LibreSSL, which has no scrypt.
    try:
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    except ImportError:
        sys.exit(
            "This Python has no scrypt support (Apple's built-in python3).\n"
            "Use Homebrew/python.org Python, or run: python3 -m pip install --user cryptography"
        )
    return Scrypt(salt=salt, length=KEYLEN, n=N, r=R, p=P).derive(password)


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"[A-Za-z0-9._@-]{1,100}", sys.argv[1]):
        sys.exit("Usage: python3 scripts/hash_password.py <username>   (letters, digits, . _ @ -)")
    username = sys.argv[1]

    if sys.stdin.isatty():
        password = getpass.getpass(f"Password for {username}: ")
        if getpass.getpass("Repeat password: ") != password:
            sys.exit("Passwords don't match.")
    else:  # piped: echo "secret" | python3 scripts/hash_password.py hr1
        password = sys.stdin.readline().rstrip("\r\n")

    if len(password) < 10:
        sys.exit("Use at least 10 characters.")

    salt = os.urandom(16)
    key = scrypt(password.encode("utf-8"), salt)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    print(f"{username}:scrypt${N}${R}${P}${b64(salt)}${b64(key)}")


if __name__ == "__main__":
    main()
