"""Password hashing and short-code generation.

Passwords are hashed with PBKDF2-SHA256 from Python's standard library.
That is the same algorithm Django uses by default, so there is nothing
home-made here and nothing extra to install.
"""

import base64
import hashlib
import hmac
import os
import secrets
import string

ITERATIONS = 240_000

# No look-alike characters (0/O, 1/l/I) so codes are easy to read aloud.
ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")


def hash_password(password: str) -> str:
    """Returns a single string holding the algorithm, salt and hash."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return "$".join([
        "pbkdf2_sha256",
        str(ITERATIONS),
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    ])


def verify_password(password: str, stored: str) -> bool:
    """Re-hashes the typed password with the stored salt and compares."""
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    expected = base64.b64decode(digest_b64)
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), base64.b64decode(salt_b64), int(iterations)
    )
    # compare_digest avoids leaking information through how long the check takes.
    return hmac.compare_digest(actual, expected)


def generate_code(length: int = 6) -> str:
    """A random short code. 'secrets' is the random module made for security,
    so codes can't be guessed in order."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
