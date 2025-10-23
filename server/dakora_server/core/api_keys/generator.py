"""API key generation utilities."""

import secrets
import bcrypt
import base58


class APIKeyGenerator:
    """Generates and manages API keys with dkr_ prefix."""

    PREFIX = "dkr"
    KEY_LENGTH = 32  # 32 bytes = 256 bits

    @staticmethod
    def generate() -> tuple[str, str]:
        """
        Generate API key and hash.

        Returns:
            tuple[str, str]: (full_key, key_hash)
                - full_key: Full key to show user once (e.g., "dkr_...")
                - key_hash: Bcrypt hash to store in database
        """
        # Generate random bytes
        random_bytes = secrets.token_bytes(APIKeyGenerator.KEY_LENGTH)

        # Encode with base58 (no ambiguous characters)
        key_body = base58.b58encode(random_bytes).decode()

        # Create full key with prefix
        full_key = f"{APIKeyGenerator.PREFIX}_{key_body}"

        # Hash with bcrypt (cost factor 12 as per security requirements)
        key_hash = bcrypt.hashpw(full_key.encode(), bcrypt.gensalt(rounds=12))

        return full_key, key_hash.decode()

    @staticmethod
    def get_prefix(key: str) -> str:
        """
        Extract display prefix from full key.

        Args:
            key: Full API key (e.g., "dkr_1a2b3c4d...")

        Returns:
            str: First 8 characters (e.g., "dkr_1a2b")
        """
        if len(key) < 8:
            return key
        return key[:8]

    @staticmethod
    def get_suffix(key: str) -> str:
        """
        Extract display suffix from full key.

        Args:
            key: Full API key (e.g., "dkr_1a2b3c4d...")

        Returns:
            str: Last 4 characters (e.g., "3c4d")
        """
        if len(key) < 4:
            return key
        return key[-4:]

    @staticmethod
    def mask_key(prefix: str, suffix: str) -> str:
        """
        Create masked display for key preview.

        Args:
            prefix: Key prefix (first 8 chars)
            suffix: Key suffix (last 4 chars)

        Returns:
            str: Masked key display (e.g., "dkr_1a2b...3c4d")
        """
        return f"{prefix}...{suffix}"

    @staticmethod
    def verify_key(key: str, key_hash: str) -> bool:
        """
        Verify API key against stored hash.

        Uses constant-time comparison via bcrypt to prevent timing attacks.

        Args:
            key: Full API key to verify
            key_hash: Stored bcrypt hash

        Returns:
            bool: True if key matches hash
        """
        return bcrypt.checkpw(key.encode(), key_hash.encode())