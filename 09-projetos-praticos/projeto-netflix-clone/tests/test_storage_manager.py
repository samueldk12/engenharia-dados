#!/usr/bin/env python3
"""
Netflix Clone - Storage Manager Tests
=====================================

Unit tests for multi-cloud storage management.

Author: Data Engineering Study Project
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / '04-camada-armazenamento'))

from storage_manager import (
    StorageConfig,
    UploadResult,
    StorageProvider,
    S3Provider,
    StorageManager
)


class TestStorageConfig:
    """Test StorageConfig dataclass"""

    def test_s3_config_creation(self):
        """Test creating S3 configuration"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1',
            access_key='test-key',
            secret_key='test-secret'
        )

        assert config.provider == 's3'
        assert config.bucket == 'test-bucket'
        assert config.region == 'us-east-1'

    def test_gcs_config_creation(self):
        """Test creating GCS configuration"""
        config = StorageConfig(
            provider='gcs',
            bucket='test-bucket',
            project_id='test-project',
            credentials_path='/path/to/credentials.json'
        )

        assert config.provider == 'gcs'
        assert config.project_id == 'test-project'


class TestUploadResult:
    """Test UploadResult dataclass"""

    def test_successful_upload_result(self):
        """Test creating a successful upload result"""
        result = UploadResult(
            success=True,
            key='video/test.mp4',
            size_bytes=1024 * 1024,
            duration_sec=2.5,
            url='https://cdn.example.com/video/test.mp4',
            error_message=None
        )

        assert result.success
        assert result.size_bytes == 1024 * 1024
        assert result.duration_sec == 2.5
        assert result.error_message is None

    def test_failed_upload_result(self):
        """Test creating a failed upload result"""
        result = UploadResult(
            success=False,
            key='video/test.mp4',
            size_bytes=0,
            duration_sec=0,
            url=None,
            error_message='Connection timeout'
        )

        assert not result.success
        assert result.error_message == 'Connection timeout'


class TestS3Provider:
    """Test S3Provider class"""

    @patch('boto3.client')
    def test_s3_provider_initialization(self, mock_boto_client):
        """Test S3 provider initialization"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1',
            access_key='test-key',
            secret_key='test-secret'
        )

        provider = S3Provider(config)

        assert provider.bucket == 'test-bucket'
        mock_boto_client.assert_called_once_with(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret'
        )

    @patch('boto3.client')
    def test_upload_small_file(self, mock_boto_client, test_data_dir):
        """Test uploading a small file (<100MB)"""
        # Create test file
        test_file = test_data_dir / 'test.txt'
        test_file.write_text('Hello, World!')

        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        provider = S3Provider(config)
        result = provider.upload_file(str(test_file), 'test/test.txt')

        # Verify upload was called
        mock_s3.upload_file.assert_called_once()
        call_args = mock_s3.upload_file.call_args

        assert call_args[0][0] == str(test_file)
        assert call_args[0][1] == 'test-bucket'
        assert call_args[0][2] == 'test/test.txt'

        assert result.success
        assert result.key == 'test/test.txt'

    @patch('boto3.client')
    def test_upload_with_metadata(self, mock_boto_client, test_data_dir):
        """Test uploading with custom metadata"""
        test_file = test_data_dir / 'video.mp4'
        test_file.write_bytes(b'fake video data')

        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        provider = S3Provider(config)

        metadata = {
            'content_id': '12345',
            'resolution': '1080p',
            'duration': '120'
        }

        result = provider.upload_file(
            str(test_file),
            'videos/test.mp4',
            metadata=metadata
        )

        # Verify metadata was passed
        call_args = mock_s3.upload_file.call_args
        extra_args = call_args[1]['ExtraArgs']

        assert extra_args['Metadata'] == metadata

    @patch('boto3.client')
    def test_get_presigned_url(self, mock_boto_client):
        """Test generating presigned URLs"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/test-bucket/test.mp4?signature=xyz'
        mock_boto_client.return_value = mock_s3

        provider = S3Provider(config)
        url = provider.get_presigned_url('videos/test.mp4', expires_in=3600)

        assert url.startswith('https://')
        assert 'test-bucket' in url
        assert 'test.mp4' in url

        mock_s3.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': 'test-bucket', 'Key': 'videos/test.mp4'},
            ExpiresIn=3600
        )

    @patch('boto3.client')
    def test_delete_file(self, mock_boto_client):
        """Test deleting a file"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        provider = S3Provider(config)
        result = provider.delete_file('videos/test.mp4')

        mock_s3.delete_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='videos/test.mp4'
        )

        assert result is True

    @patch('boto3.client')
    def test_list_files(self, mock_boto_client):
        """Test listing files with prefix"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'videos/video1.mp4', 'Size': 1024},
                {'Key': 'videos/video2.mp4', 'Size': 2048}
            ]
        }
        mock_boto_client.return_value = mock_s3

        provider = S3Provider(config)
        files = provider.list_files(prefix='videos/')

        assert len(files) == 2
        assert files[0]['key'] == 'videos/video1.mp4'
        assert files[1]['key'] == 'videos/video2.mp4'

    @patch('boto3.client')
    def test_file_exists(self, mock_boto_client):
        """Test checking if file exists"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        provider = S3Provider(config)

        # File exists
        mock_s3.head_object.return_value = {'ContentLength': 1024}
        assert provider.file_exists('videos/test.mp4') is True

        # File does not exist
        from botocore.exceptions import ClientError
        mock_s3.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}},
            'HeadObject'
        )
        assert provider.file_exists('videos/nonexistent.mp4') is False

    @patch('boto3.client')
    def test_get_file_metadata(self, mock_boto_client):
        """Test getting file metadata"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {
            'ContentLength': 1024 * 1024,
            'LastModified': datetime(2023, 1, 1),
            'ContentType': 'video/mp4',
            'Metadata': {'resolution': '1080p'}
        }
        mock_boto_client.return_value = mock_s3

        provider = S3Provider(config)
        metadata = provider.get_file_metadata('videos/test.mp4')

        assert metadata['size_bytes'] == 1024 * 1024
        assert metadata['content_type'] == 'video/mp4'
        assert metadata['custom_metadata']['resolution'] == '1080p'


class TestStorageManager:
    """Test StorageManager unified interface"""

    @patch('boto3.client')
    def test_manager_initialization(self, mock_boto_client):
        """Test storage manager initialization"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        manager = StorageManager(config)

        assert manager.config == config
        assert manager.provider is not None

    @patch('boto3.client')
    def test_upload_via_manager(self, mock_boto_client, test_data_dir):
        """Test uploading through manager"""
        test_file = test_data_dir / 'test.txt'
        test_file.write_text('Test content')

        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        manager = StorageManager(config)
        result = manager.upload_file(str(test_file), 'test/test.txt')

        assert result.success
        mock_s3.upload_file.assert_called_once()

    @patch('boto3.client')
    def test_upload_directory(self, mock_boto_client, test_data_dir):
        """Test uploading entire directory"""
        # Create test directory structure
        upload_dir = test_data_dir / 'upload'
        upload_dir.mkdir(exist_ok=True)

        (upload_dir / 'file1.txt').write_text('File 1')
        (upload_dir / 'file2.txt').write_text('File 2')

        subdir = upload_dir / 'subdir'
        subdir.mkdir(exist_ok=True)
        (subdir / 'file3.txt').write_text('File 3')

        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        manager = StorageManager(config)
        results = manager.upload_directory(
            str(upload_dir),
            'uploads/',
            parallel=False  # Sequential for predictable testing
        )

        # Should upload 3 files
        assert len(results) == 3
        assert all(r.success for r in results)

        # Verify all files were uploaded
        assert mock_s3.upload_file.call_count == 3

    @patch('boto3.client')
    def test_upload_directory_parallel(self, mock_boto_client, test_data_dir):
        """Test parallel directory upload"""
        # Create multiple test files
        upload_dir = test_data_dir / 'parallel_upload'
        upload_dir.mkdir(exist_ok=True)

        for i in range(10):
            (upload_dir / f'file{i}.txt').write_text(f'File {i}')

        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        manager = StorageManager(config)
        results = manager.upload_directory(
            str(upload_dir),
            'parallel/',
            parallel=True,
            max_workers=4
        )

        # All 10 files should be uploaded
        assert len(results) == 10
        assert all(r.success for r in results)

    @patch('boto3.client')
    def test_cdn_invalidation(self, mock_boto_client):
        """Test CDN cache invalidation"""
        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1',
            cdn_distribution_id='ABCDEFG'
        )

        mock_s3 = MagicMock()
        mock_cloudfront = MagicMock()

        def mock_client(service, **kwargs):
            if service == 's3':
                return mock_s3
            elif service == 'cloudfront':
                return mock_cloudfront
            return MagicMock()

        mock_boto_client.side_effect = mock_client

        manager = StorageManager(config)

        paths = ['/videos/video1.mp4', '/videos/video2.mp4']
        manager.invalidate_cdn_cache(paths)

        # Verify CloudFront invalidation was called
        mock_cloudfront.create_invalidation.assert_called_once()
        call_args = mock_cloudfront.create_invalidation.call_args

        assert call_args[1]['DistributionId'] == 'ABCDEFG'
        assert '/videos/video1.mp4' in call_args[1]['InvalidationBatch']['Paths']['Items']

    @patch('boto3.client')
    def test_error_handling(self, mock_boto_client, test_data_dir):
        """Test error handling during upload"""
        test_file = test_data_dir / 'test.txt'
        test_file.write_text('Test')

        config = StorageConfig(
            provider='s3',
            bucket='test-bucket',
            region='us-east-1'
        )

        mock_s3 = MagicMock()
        # Simulate upload failure
        mock_s3.upload_file.side_effect = Exception('Network error')
        mock_boto_client.return_value = mock_s3

        manager = StorageManager(config)
        result = manager.upload_file(str(test_file), 'test/test.txt')

        # Should fail gracefully
        assert not result.success
        assert 'Network error' in result.error_message


# Integration tests

@pytest.mark.integration
class TestStorageManagerIntegration:
    """Integration tests with real S3 (requires AWS credentials)"""

    @pytest.mark.skip(reason="Requires AWS credentials")
    def test_real_s3_upload(self, test_data_dir):
        """Test actual S3 upload"""
        # This test requires real AWS credentials
        # Skip by default

        config = StorageConfig(
            provider='s3',
            bucket='your-test-bucket',
            region='us-east-1'
        )

        manager = StorageManager(config)

        test_file = test_data_dir / 'integration_test.txt'
        test_file.write_text('Integration test')

        result = manager.upload_file(
            str(test_file),
            'test/integration_test.txt'
        )

        assert result.success

        # Cleanup
        manager.delete_file('test/integration_test.txt')
