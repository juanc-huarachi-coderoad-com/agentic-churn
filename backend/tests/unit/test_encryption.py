"""REQ-M1-P4 — encrypt/decrypt round-trips, and the ciphertext never contains the
plaintext as a substring."""

from cryptography.fernet import Fernet

from app.ingestion.adapters.encryption import FernetEncryption


def _write_key(tmp_path):
    key_path = tmp_path / "data.key"
    key_path.write_text(Fernet.generate_key().decode())
    return str(key_path)


def test_round_trip_returns_original_plaintext(tmp_path):
    encryption = FernetEncryption(_write_key(tmp_path))
    plaintext = "Please advise on the timeline."

    ciphertext = encryption.encrypt(plaintext)

    assert encryption.decrypt(ciphertext) == plaintext


def test_ciphertext_never_contains_plaintext_substring(tmp_path):
    encryption = FernetEncryption(_write_key(tmp_path))
    plaintext = "the-contract-dispute-thread"

    ciphertext = encryption.encrypt(plaintext)

    assert plaintext.encode() not in ciphertext
