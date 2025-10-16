"""
Tests for checksum_validator module

Tests triple-level checksum validation:
1. Redis message checksum format validation
2. Tar.gz file checksum verification
3. Internal archive checksums.sha256 validation
"""

import pytest
import hashlib
import tempfile
from pathlib import Path
from src.ingestion.checksum_validator import ChecksumValidator


class TestChecksumValidator:
    """Test suite for ChecksumValidator"""

    def test_validate_checksum_format_valid(self):
        """Test valid checksum format"""
        valid_checksums = [
            'sha256:' + 'a' * 64,
            'sha256:' + 'f' * 64,
            'sha256:0123456789abcdef' * 4
        ]

        for checksum in valid_checksums:
            # Should not raise
            ChecksumValidator.validate_checksum_format(checksum)

    def test_validate_checksum_format_invalid(self):
        """Test invalid checksum formats raise ValueError"""
        invalid_checksums = [
            'sha256:abc123',  # Too short
            'sha256:' + 'g' * 64,  # Invalid hex character
            'md5:' + 'a' * 32,  # Wrong algorithm
            'a' * 64,  # Missing prefix
            'sha256:' + 'a' * 63,  # 63 chars instead of 64
            'sha256:' + 'a' * 65,  # 65 chars instead of 64
        ]

        for checksum in invalid_checksums:
            with pytest.raises(ValueError, match="Invalid checksum format"):
                ChecksumValidator.validate_checksum_format(checksum)

    def test_calculate_file_sha256(self):
        """Test SHA-256 calculation for a file"""
        # Create temporary file with known content
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            content = b'Hello, World!'
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Calculate expected checksum
            expected = hashlib.sha256(content).hexdigest()

            # Test calculation
            actual = ChecksumValidator.calculate_file_sha256(temp_path)

            assert actual == expected
        finally:
            temp_path.unlink()

    def test_calculate_file_sha256_nonexistent(self):
        """Test that nonexistent file raises FileNotFoundError"""
        nonexistent = Path('/tmp/nonexistent_file_xyz123.txt')

        with pytest.raises(FileNotFoundError):
            ChecksumValidator.calculate_file_sha256(nonexistent)

    def test_verify_file_checksum_match(self):
        """Test successful checksum verification"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            content = b'Test content for checksum'
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Calculate checksum
            actual_hash = hashlib.sha256(content).hexdigest()
            expected_checksum = f'sha256:{actual_hash}'

            # Verify (should not raise)
            result = ChecksumValidator.verify_file_checksum(
                temp_path,
                expected_checksum
            )

            assert result is True
        finally:
            temp_path.unlink()

    def test_verify_file_checksum_mismatch(self):
        """Test checksum mismatch raises ValueError"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            f.write(b'Actual content')
            temp_path = Path(f.name)

        try:
            # Wrong checksum
            wrong_checksum = 'sha256:' + 'a' * 64

            with pytest.raises(ValueError, match="Checksum mismatch"):
                ChecksumValidator.verify_file_checksum(temp_path, wrong_checksum)
        finally:
            temp_path.unlink()

    def test_verify_tarball_success(self):
        """Test tarball verification with correct checksum"""
        # Create temporary tarball
        with tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix='.tar.gz') as f:
            content = b'Tarball content'
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Calculate correct checksum
            actual_hash = hashlib.sha256(content).hexdigest()
            expected_checksum = f'sha256:{actual_hash}'

            # Verify (should not raise)
            result = ChecksumValidator.verify_tarball(temp_path, expected_checksum)

            assert result is True
        finally:
            temp_path.unlink()

    def test_verify_tarball_mismatch(self):
        """Test tarball verification with wrong checksum"""
        with tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix='.tar.gz') as f:
            f.write(b'Tarball content')
            temp_path = Path(f.name)

        try:
            wrong_checksum = 'sha256:' + 'f' * 64

            with pytest.raises(ValueError, match="Checksum mismatch"):
                ChecksumValidator.verify_tarball(temp_path, wrong_checksum)
        finally:
            temp_path.unlink()

    def test_parse_checksums_file_valid(self):
        """Test parsing valid checksums.sha256 file"""
        # Create temporary checksums file
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.sha256') as f:
            f.write('abc123def456  conversation.json\n')
            f.write('789fedcba987  metadata.json\n')
            f.write('111222333444  audio.wav\n')
            temp_path = Path(f.name)

        try:
            checksums = ChecksumValidator.parse_checksums_file(temp_path)

            assert len(checksums) == 3
            assert checksums['conversation.json'] == 'abc123def456'
            assert checksums['metadata.json'] == '789fedcba987'
            assert checksums['audio.wav'] == '111222333444'
        finally:
            temp_path.unlink()

    def test_parse_checksums_file_empty(self):
        """Test parsing empty checksums file"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.sha256') as f:
            f.write('')
            temp_path = Path(f.name)

        try:
            checksums = ChecksumValidator.parse_checksums_file(temp_path)
            assert checksums == {}
        finally:
            temp_path.unlink()

    def test_parse_checksums_file_with_comments(self):
        """Test parsing checksums file with blank lines and comments"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.sha256') as f:
            f.write('# This is a comment\n')
            f.write('\n')
            f.write('abc123  file1.txt\n')
            f.write('   \n')  # Blank line with spaces
            f.write('def456  file2.txt\n')
            temp_path = Path(f.name)

        try:
            checksums = ChecksumValidator.parse_checksums_file(temp_path)

            assert len(checksums) == 2
            assert checksums['file1.txt'] == 'abc123'
            assert checksums['file2.txt'] == 'def456'
        finally:
            temp_path.unlink()

    def test_verify_archive_checksums_success(self):
        """Test full archive checksum verification"""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / 'archive'
            archive_dir.mkdir()

            # Create test files
            file1 = archive_dir / 'conversation.json'
            file1.write_text('{"test": "data"}')

            file2 = archive_dir / 'metadata.json'
            file2.write_text('{"meta": "info"}')

            # Calculate checksums
            hash1 = hashlib.sha256(b'{"test": "data"}').hexdigest()
            hash2 = hashlib.sha256(b'{"meta": "info"}').hexdigest()

            # Create checksums file
            checksums_file = archive_dir / 'checksums.sha256'
            checksums_file.write_text(
                f'{hash1}  conversation.json\n'
                f'{hash2}  metadata.json\n'
            )

            # Verify (should not raise)
            result = ChecksumValidator.verify_archive_checksums(archive_dir)

            assert result is True

    def test_verify_archive_checksums_file_missing(self):
        """Test archive verification when checksums.sha256 is missing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / 'archive'
            archive_dir.mkdir()

            # Create file but no checksums.sha256
            (archive_dir / 'conversation.json').write_text('{"test": "data"}')

            with pytest.raises(FileNotFoundError, match="checksums.sha256 not found"):
                ChecksumValidator.verify_archive_checksums(archive_dir)

    def test_verify_archive_checksums_mismatch(self):
        """Test archive verification with checksum mismatch"""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / 'archive'
            archive_dir.mkdir()

            # Create file
            file1 = archive_dir / 'conversation.json'
            file1.write_text('{"test": "data"}')

            # Create checksums file with WRONG hash
            checksums_file = archive_dir / 'checksums.sha256'
            checksums_file.write_text('ffffffffffffffff  conversation.json\n')

            with pytest.raises(ValueError, match="Checksum mismatch for 'conversation.json'"):
                ChecksumValidator.verify_archive_checksums(archive_dir)

    def test_verify_archive_checksums_missing_file(self):
        """Test archive verification when listed file doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / 'archive'
            archive_dir.mkdir()

            # Create checksums file referencing non-existent file
            checksums_file = archive_dir / 'checksums.sha256'
            checksums_file.write_text('abc123  nonexistent.json\n')

            with pytest.raises(FileNotFoundError, match="File 'nonexistent.json' listed in checksums"):
                ChecksumValidator.verify_archive_checksums(archive_dir)

    def test_verify_archive_checksums_empty_checksums(self):
        """Test archive with empty checksums file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / 'archive'
            archive_dir.mkdir()

            # Create empty checksums file
            (archive_dir / 'checksums.sha256').write_text('')

            # Should succeed (no files to verify)
            result = ChecksumValidator.verify_archive_checksums(archive_dir)
            assert result is True

    def test_verify_archive_checksums_with_subdirectories(self):
        """Test archive verification with files in subdirectories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / 'archive'
            archive_dir.mkdir()

            # Create subdirectory structure
            subdir = archive_dir / 'data'
            subdir.mkdir()

            file1 = subdir / 'file.json'
            file1.write_text('{"nested": "data"}')

            # Calculate checksum
            hash1 = hashlib.sha256(b'{"nested": "data"}').hexdigest()

            # Create checksums file with relative path
            checksums_file = archive_dir / 'checksums.sha256'
            checksums_file.write_text(f'{hash1}  data/file.json\n')

            # Verify
            result = ChecksumValidator.verify_archive_checksums(archive_dir)
            assert result is True


class TestChecksumValidatorEdgeCases:
    """Test edge cases and error conditions"""

    def test_large_file_checksum(self):
        """Test checksum calculation for large file (streaming)"""
        # Create 10MB file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            chunk = b'x' * (1024 * 1024)  # 1MB chunk
            for _ in range(10):
                f.write(chunk)
            temp_path = Path(f.name)

        try:
            # Calculate checksum (should handle streaming)
            result = ChecksumValidator.calculate_file_sha256(temp_path)

            # Verify it's a valid hex string
            assert len(result) == 64
            assert all(c in '0123456789abcdef' for c in result)
        finally:
            temp_path.unlink()

    def test_unicode_filenames(self):
        """Test checksum validation with Unicode filenames"""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir)

            # Create file with Unicode name
            file1 = archive_dir / 'données_français.json'
            file1.write_text('{"test": "unicode"}')

            # Calculate checksum
            hash1 = hashlib.sha256(b'{"test": "unicode"}').hexdigest()

            # Create checksums file
            checksums_file = archive_dir / 'checksums.sha256'
            checksums_file.write_text(f'{hash1}  données_français.json\n')

            # Verify
            result = ChecksumValidator.verify_archive_checksums(archive_dir)
            assert result is True

    def test_checksum_case_insensitive(self):
        """Test that checksum comparison is case-insensitive"""
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            content = b'Test'
            f.write(content)
            temp_path = Path(f.name)

        try:
            hash_lower = hashlib.sha256(content).hexdigest().lower()
            hash_upper = hash_lower.upper()

            # Both should work
            ChecksumValidator.verify_file_checksum(
                temp_path,
                f'sha256:{hash_lower}'
            )
            ChecksumValidator.verify_file_checksum(
                temp_path,
                f'sha256:{hash_upper}'
            )
        finally:
            temp_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
