"""
Checksum Validation for Audio Ingestion

Validates checksums at multiple levels:
1. Redis message checksum format
2. Downloaded tar.gz file checksum
3. Internal checksums.sha256 file validation

Aligned with ADR-2025-10-03-003 cross-cutting contract
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


class ChecksumValidator:
    """Validator for SHA-256 checksums at various pipeline stages"""

    # Checksum format: sha256:0123456789abcdef... (64 hex chars)
    CHECKSUM_PATTERN = re.compile(r'^sha256:[a-f0-9]{64}$')

    @staticmethod
    def validate_checksum_format(checksum: str) -> bool:
        """
        Validate checksum format from Redis message

        Args:
            checksum: Checksum string (expected format: "sha256:<64 hex chars>")

        Returns:
            True if valid format

        Raises:
            ValueError if format is invalid
        """
        if not ChecksumValidator.CHECKSUM_PATTERN.match(checksum):
            raise ValueError(
                f"Invalid checksum format: {checksum}. "
                f"Expected format: sha256:<64 lowercase hex characters>"
            )

        logger.debug(f"Checksum format validated: {checksum[:15]}...")
        return True

    @staticmethod
    def calculate_file_sha256(file_path: Path, chunk_size: int = 8192) -> str:
        """
        Calculate SHA-256 checksum of a file

        Args:
            file_path: Path to file
            chunk_size: Bytes to read per chunk (default 8KB)

        Returns:
            Checksum in format "sha256:<hash>"
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(chunk)

        checksum = f"sha256:{sha256_hash.hexdigest()}"
        logger.debug(f"Calculated checksum for {file_path.name}: {checksum[:15]}...")
        return checksum

    @staticmethod
    def verify_file_checksum(
        file_path: Path,
        expected_checksum: str,
        error_context: str = "file"
    ) -> bool:
        """
        Verify file checksum matches expected value

        Args:
            file_path: Path to file to verify
            expected_checksum: Expected checksum (format: "sha256:<hash>")
            error_context: Context string for error messages

        Returns:
            True if checksums match

        Raises:
            ValueError if checksum mismatch
        """
        # Validate expected checksum format
        ChecksumValidator.validate_checksum_format(expected_checksum)

        # Calculate actual checksum
        actual_checksum = ChecksumValidator.calculate_file_sha256(file_path)

        if actual_checksum != expected_checksum:
            raise ValueError(
                f"Checksum mismatch for {error_context} '{file_path.name}':\n"
                f"  Expected: {expected_checksum}\n"
                f"  Actual:   {actual_checksum}"
            )

        logger.info(f"✓ Checksum verified for {error_context}: {file_path.name}")
        return True

    @staticmethod
    def parse_checksums_file(checksums_file: Path) -> Dict[str, str]:
        """
        Parse checksums.sha256 file

        Format per line: <hash>  <relative_path>
        Example: a3f5b9c1...  conversation.json

        Args:
            checksums_file: Path to checksums.sha256

        Returns:
            Dict mapping relative paths to checksums (with sha256: prefix)
        """
        if not checksums_file.exists():
            raise FileNotFoundError(f"Checksums file not found: {checksums_file}")

        checksums = {}

        with open(checksums_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Expected format: <hash>  <path> (two spaces separator)
                parts = re.split(r'\s{2,}', line)
                if len(parts) != 2:
                    logger.warning(
                        f"Skipping malformed line {line_num} in {checksums_file.name}: {line}"
                    )
                    continue

                hash_value, rel_path = parts

                # Validate hash format (64 hex chars)
                if not re.match(r'^[a-f0-9]{64}$', hash_value):
                    logger.warning(
                        f"Invalid hash format on line {line_num}: {hash_value}"
                    )
                    continue

                # Add sha256: prefix for consistency
                checksums[rel_path] = f"sha256:{hash_value}"

        logger.info(f"Parsed {len(checksums)} checksums from {checksums_file.name}")
        return checksums

    @staticmethod
    def verify_archive_checksums(
        extracted_dir: Path,
        checksums_file_name: str = "checksums.sha256"
    ) -> bool:
        """
        Verify all files in extracted archive against checksums.sha256

        Args:
            extracted_dir: Root directory of extracted tar.gz
            checksums_file_name: Name of checksums file (default: "checksums.sha256")

        Returns:
            True if all checksums match

        Raises:
            FileNotFoundError if checksums.sha256 missing
            ValueError if any checksum mismatch
        """
        checksums_file = extracted_dir / checksums_file_name

        if not checksums_file.exists():
            raise FileNotFoundError(
                f"Required file '{checksums_file_name}' not found in archive"
            )

        # Parse checksums file
        expected_checksums = ChecksumValidator.parse_checksums_file(checksums_file)

        if not expected_checksums:
            raise ValueError(f"No checksums found in {checksums_file_name}")

        # Verify each file
        errors = []
        verified_count = 0

        for rel_path, expected_checksum in expected_checksums.items():
            file_path = extracted_dir / rel_path

            # Skip checksums.sha256 itself (checksum of checksum file not meaningful)
            if rel_path == checksums_file_name:
                logger.debug(f"Skipping checksum verification for {checksums_file_name}")
                continue

            if not file_path.exists():
                errors.append(f"File listed in {checksums_file_name} not found: {rel_path}")
                continue

            try:
                ChecksumValidator.verify_file_checksum(
                    file_path,
                    expected_checksum,
                    error_context=f"archive file '{rel_path}'"
                )
                verified_count += 1

            except ValueError as e:
                errors.append(str(e))

        # Report results
        if errors:
            error_msg = f"Checksum verification failed for {len(errors)} file(s):\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"✓ All {verified_count} files verified against {checksums_file_name}"
        )
        return True

    @staticmethod
    def verify_tarball(
        tarball_path: Path,
        expected_checksum: str
    ) -> bool:
        """
        Verify tar.gz archive checksum from Redis message

        Args:
            tarball_path: Path to downloaded tar.gz file
            expected_checksum: Expected checksum from Redis (format: "sha256:<hash>")

        Returns:
            True if checksum matches

        Raises:
            ValueError if checksum mismatch
        """
        return ChecksumValidator.verify_file_checksum(
            tarball_path,
            expected_checksum,
            error_context="tar.gz archive"
        )


class ChecksumError(Exception):
    """Raised when checksum validation fails"""
    pass
