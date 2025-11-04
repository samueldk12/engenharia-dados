#!/usr/bin/env python3
"""
Netflix Clone - Storage Manager
================================

Multi-cloud storage manager com suporte a S3, GCS e CDN.

Features:
- Upload/download otimizado com multipart
- Lifecycle policies para otimização de custos
- CDN invalidation
- Metadata management
- Presigned URLs para acesso temporário
- Multi-cloud abstraction (S3, GCS)

Usage:
    from storage_manager import StorageManager

    storage = StorageManager(provider='s3')
    storage.upload('video.mp4', 'content/123/video.mp4')

Author: Data Engineering Study Project
"""

import boto3
from google.cloud import storage as gcs
import hashlib
import json
import logging
import mimetypes
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    """Storage configuration"""
    provider: str  # 's3' or 'gcs'
    bucket_name: str
    region: str = 'us-east-1'
    cdn_domain: Optional[str] = None
    cdn_distribution_id: Optional[str] = None
    enable_encryption: bool = True
    enable_versioning: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class UploadResult:
    """Upload result"""
    success: bool
    key: str
    size: int
    etag: str
    url: str
    cdn_url: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class StorageProvider(ABC):
    """Abstract storage provider interface"""

    @abstractmethod
    def upload_file(self, local_path: str, key: str,
                   metadata: Optional[Dict] = None) -> UploadResult:
        """Upload file to storage"""
        pass

    @abstractmethod
    def download_file(self, key: str, local_path: str) -> bool:
        """Download file from storage"""
        pass

    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """Delete file from storage"""
        pass

    @abstractmethod
    def list_files(self, prefix: str, max_keys: int = 1000) -> List[str]:
        """List files with prefix"""
        pass

    @abstractmethod
    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Get presigned URL for temporary access"""
        pass

    @abstractmethod
    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """Copy file within storage"""
        pass


class S3Provider(StorageProvider):
    """AWS S3 storage provider"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self.s3_client = boto3.client('s3', region_name=config.region)
        self.s3_resource = boto3.resource('s3', region_name=config.region)
        self.bucket = self.s3_resource.Bucket(config.bucket_name)

        # Configure CloudFront (if available)
        if config.cdn_distribution_id:
            self.cloudfront = boto3.client('cloudfront')
        else:
            self.cloudfront = None

        logger.info(f"S3 provider initialized: {config.bucket_name}")

    def upload_file(self, local_path: str, key: str,
                   metadata: Optional[Dict] = None) -> UploadResult:
        """
        Upload file to S3 with multipart upload for large files
        """
        local_path = Path(local_path)

        if not local_path.exists():
            return UploadResult(
                success=False,
                key=key,
                size=0,
                etag="",
                url="",
                error=f"File not found: {local_path}"
            )

        file_size = local_path.stat().st_size

        # Prepare metadata
        extra_args = {
            'Metadata': metadata or {},
            'ContentType': mimetypes.guess_type(str(local_path))[0] or 'application/octet-stream'
        }

        # Enable server-side encryption
        if self.config.enable_encryption:
            extra_args['ServerSideEncryption'] = 'AES256'

        # Set cache control for videos
        if key.endswith(('.mp4', '.m3u8', '.ts')):
            if key.endswith('.m3u8'):
                # Manifests: short cache (1 minute)
                extra_args['CacheControl'] = 'max-age=60'
            else:
                # Segments: long cache (30 days)
                extra_args['CacheControl'] = 'max-age=2592000, immutable'

        try:
            logger.info(f"Uploading {local_path.name} ({file_size / 1024**2:.2f} MB) to s3://{self.config.bucket_name}/{key}")

            # Use multipart upload for files > 100MB
            if file_size > 100 * 1024**2:
                config = boto3.s3.transfer.TransferConfig(
                    multipart_threshold=100 * 1024**2,  # 100MB
                    max_concurrency=10,
                    multipart_chunksize=10 * 1024**2,  # 10MB chunks
                    use_threads=True
                )

                self.bucket.upload_file(
                    str(local_path),
                    key,
                    ExtraArgs=extra_args,
                    Config=config
                )
            else:
                self.bucket.upload_file(
                    str(local_path),
                    key,
                    ExtraArgs=extra_args
                )

            # Get object info
            obj = self.s3_resource.Object(self.config.bucket_name, key)

            # Generate URLs
            url = f"s3://{self.config.bucket_name}/{key}"
            cdn_url = None
            if self.config.cdn_domain:
                cdn_url = f"https://{self.config.cdn_domain}/{key}"

            logger.info(f"✓ Upload complete: {key}")

            return UploadResult(
                success=True,
                key=key,
                size=file_size,
                etag=obj.e_tag.strip('"'),
                url=url,
                cdn_url=cdn_url
            )

        except Exception as e:
            logger.error(f"✗ Upload failed: {e}")
            return UploadResult(
                success=False,
                key=key,
                size=file_size,
                etag="",
                url="",
                error=str(e)
            )

    def download_file(self, key: str, local_path: str) -> bool:
        """Download file from S3"""
        try:
            logger.info(f"Downloading s3://{self.config.bucket_name}/{key} to {local_path}")

            # Create directory if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            self.bucket.download_file(key, local_path)

            logger.info(f"✓ Download complete: {local_path}")
            return True

        except Exception as e:
            logger.error(f"✗ Download failed: {e}")
            return False

    def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            logger.info(f"Deleting s3://{self.config.bucket_name}/{key}")

            obj = self.s3_resource.Object(self.config.bucket_name, key)
            obj.delete()

            logger.info(f"✓ Deleted: {key}")
            return True

        except Exception as e:
            logger.error(f"✗ Delete failed: {e}")
            return False

    def list_files(self, prefix: str, max_keys: int = 1000) -> List[str]:
        """List files with prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            keys = [obj['Key'] for obj in response['Contents']]

            logger.info(f"Found {len(keys)} objects with prefix: {prefix}")
            return keys

        except Exception as e:
            logger.error(f"List failed: {e}")
            return []

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate presigned URL for temporary access

        Use cases:
        - Direct browser uploads
        - Temporary download links
        - Third-party integrations
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.config.bucket_name,
                    'Key': key
                },
                ExpiresIn=expires_in
            )

            logger.info(f"Generated presigned URL for {key} (expires in {expires_in}s)")
            return url

        except Exception as e:
            logger.error(f"Presigned URL generation failed: {e}")
            return ""

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """Copy file within S3"""
        try:
            logger.info(f"Copying {source_key} to {dest_key}")

            copy_source = {
                'Bucket': self.config.bucket_name,
                'Key': source_key
            }

            self.bucket.copy(copy_source, dest_key)

            logger.info(f"✓ Copy complete")
            return True

        except Exception as e:
            logger.error(f"✗ Copy failed: {e}")
            return False

    def invalidate_cdn_cache(self, paths: List[str]) -> bool:
        """
        Invalidate CloudFront cache

        Use when content changes and CDN needs to refresh
        """
        if not self.cloudfront or not self.config.cdn_distribution_id:
            logger.warning("CloudFront not configured")
            return False

        try:
            logger.info(f"Invalidating CDN cache for {len(paths)} paths")

            response = self.cloudfront.create_invalidation(
                DistributionId=self.config.cdn_distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': len(paths),
                        'Items': paths
                    },
                    'CallerReference': str(datetime.utcnow().timestamp())
                }
            )

            invalidation_id = response['Invalidation']['Id']
            logger.info(f"✓ CDN invalidation created: {invalidation_id}")

            return True

        except Exception as e:
            logger.error(f"✗ CDN invalidation failed: {e}")
            return False


class GCSProvider(StorageProvider):
    """Google Cloud Storage provider"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self.client = gcs.Client()
        self.bucket = self.client.bucket(config.bucket_name)

        logger.info(f"GCS provider initialized: {config.bucket_name}")

    def upload_file(self, local_path: str, key: str,
                   metadata: Optional[Dict] = None) -> UploadResult:
        """Upload file to GCS"""
        local_path = Path(local_path)

        if not local_path.exists():
            return UploadResult(
                success=False,
                key=key,
                size=0,
                etag="",
                url="",
                error=f"File not found: {local_path}"
            )

        file_size = local_path.stat().st_size

        try:
            logger.info(f"Uploading {local_path.name} ({file_size / 1024**2:.2f} MB) to gs://{self.config.bucket_name}/{key}")

            blob = self.bucket.blob(key)

            # Set metadata
            if metadata:
                blob.metadata = metadata

            # Set content type
            content_type = mimetypes.guess_type(str(local_path))[0]
            if content_type:
                blob.content_type = content_type

            # Set cache control
            if key.endswith(('.mp4', '.m3u8', '.ts')):
                if key.endswith('.m3u8'):
                    blob.cache_control = 'max-age=60'
                else:
                    blob.cache_control = 'max-age=2592000, immutable'

            # Upload
            blob.upload_from_filename(str(local_path))

            # Generate URLs
            url = f"gs://{self.config.bucket_name}/{key}"
            cdn_url = None
            if self.config.cdn_domain:
                cdn_url = f"https://{self.config.cdn_domain}/{key}"

            logger.info(f"✓ Upload complete: {key}")

            return UploadResult(
                success=True,
                key=key,
                size=file_size,
                etag=blob.etag,
                url=url,
                cdn_url=cdn_url
            )

        except Exception as e:
            logger.error(f"✗ Upload failed: {e}")
            return UploadResult(
                success=False,
                key=key,
                size=file_size,
                etag="",
                url="",
                error=str(e)
            )

    def download_file(self, key: str, local_path: str) -> bool:
        """Download file from GCS"""
        try:
            logger.info(f"Downloading gs://{self.config.bucket_name}/{key} to {local_path}")

            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            blob = self.bucket.blob(key)
            blob.download_to_filename(local_path)

            logger.info(f"✓ Download complete: {local_path}")
            return True

        except Exception as e:
            logger.error(f"✗ Download failed: {e}")
            return False

    def delete_file(self, key: str) -> bool:
        """Delete file from GCS"""
        try:
            logger.info(f"Deleting gs://{self.config.bucket_name}/{key}")

            blob = self.bucket.blob(key)
            blob.delete()

            logger.info(f"✓ Deleted: {key}")
            return True

        except Exception as e:
            logger.error(f"✗ Delete failed: {e}")
            return False

    def list_files(self, prefix: str, max_keys: int = 1000) -> List[str]:
        """List files with prefix"""
        try:
            blobs = self.client.list_blobs(
                self.config.bucket_name,
                prefix=prefix,
                max_results=max_keys
            )

            keys = [blob.name for blob in blobs]

            logger.info(f"Found {len(keys)} objects with prefix: {prefix}")
            return keys

        except Exception as e:
            logger.error(f"List failed: {e}")
            return []

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate signed URL for temporary access"""
        try:
            blob = self.bucket.blob(key)

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_in),
                method="GET"
            )

            logger.info(f"Generated signed URL for {key} (expires in {expires_in}s)")
            return url

        except Exception as e:
            logger.error(f"Signed URL generation failed: {e}")
            return ""

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """Copy file within GCS"""
        try:
            logger.info(f"Copying {source_key} to {dest_key}")

            source_blob = self.bucket.blob(source_key)
            self.bucket.copy_blob(source_blob, self.bucket, dest_key)

            logger.info(f"✓ Copy complete")
            return True

        except Exception as e:
            logger.error(f"✗ Copy failed: {e}")
            return False


class StorageManager:
    """
    Unified storage manager supporting multiple cloud providers
    """

    def __init__(self, config: StorageConfig):
        """
        Initialize storage manager

        Args:
            config: Storage configuration
        """
        self.config = config

        # Initialize provider
        if config.provider == 's3':
            self.provider = S3Provider(config)
        elif config.provider == 'gcs':
            self.provider = GCSProvider(config)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

        logger.info(f"Storage manager initialized: {config.provider}")

    def upload(self, local_path: str, key: str,
               metadata: Optional[Dict] = None) -> UploadResult:
        """Upload file"""
        return self.provider.upload_file(local_path, key, metadata)

    def upload_directory(self, local_dir: str, prefix: str,
                        parallel: bool = True,
                        max_workers: int = 10) -> List[UploadResult]:
        """
        Upload entire directory

        Args:
            local_dir: Local directory path
            prefix: S3/GCS prefix
            parallel: Upload in parallel
            max_workers: Max parallel uploads

        Returns:
            List of upload results
        """
        local_dir = Path(local_dir)

        if not local_dir.is_dir():
            raise ValueError(f"Not a directory: {local_dir}")

        # Find all files
        files = []
        for file in local_dir.rglob('*'):
            if file.is_file():
                relative_path = file.relative_to(local_dir)
                key = f"{prefix}/{relative_path}".replace('\\', '/')
                files.append((str(file), key))

        logger.info(f"Uploading {len(files)} files from {local_dir}")

        results = []

        if parallel:
            # Parallel upload
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.upload, local_path, key): (local_path, key)
                    for local_path, key in files
                }

                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
        else:
            # Sequential upload
            for local_path, key in files:
                result = self.upload(local_path, key)
                results.append(result)

        successful = sum(1 for r in results if r.success)
        logger.info(f"Upload complete: {successful}/{len(files)} successful")

        return results

    def download(self, key: str, local_path: str) -> bool:
        """Download file"""
        return self.provider.download_file(key, local_path)

    def delete(self, key: str) -> bool:
        """Delete file"""
        return self.provider.delete_file(key)

    def delete_prefix(self, prefix: str) -> int:
        """
        Delete all files with prefix

        Returns:
            Number of files deleted
        """
        keys = self.provider.list_files(prefix)

        deleted = 0
        for key in keys:
            if self.delete(key):
                deleted += 1

        logger.info(f"Deleted {deleted}/{len(keys)} files with prefix: {prefix}")
        return deleted

    def list(self, prefix: str = "", max_keys: int = 1000) -> List[str]:
        """List files"""
        return self.provider.list_files(prefix, max_keys)

    def get_url(self, key: str, temporary: bool = False,
                expires_in: int = 3600) -> str:
        """
        Get URL for file

        Args:
            key: File key
            temporary: Use presigned/signed URL
            expires_in: URL expiration (seconds)

        Returns:
            URL string
        """
        if temporary:
            return self.provider.get_presigned_url(key, expires_in)
        else:
            if self.config.cdn_domain:
                return f"https://{self.config.cdn_domain}/{key}"
            else:
                return f"{self.config.provider}://{self.config.bucket_name}/{key}"

    def copy(self, source_key: str, dest_key: str) -> bool:
        """Copy file"""
        return self.provider.copy_file(source_key, dest_key)

    def calculate_checksum(self, local_path: str) -> str:
        """Calculate MD5 checksum"""
        md5 = hashlib.md5()

        with open(local_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)

        return md5.hexdigest()

    def verify_upload(self, local_path: str, key: str) -> bool:
        """
        Verify uploaded file matches local file

        Downloads and compares checksums
        """
        local_checksum = self.calculate_checksum(local_path)

        # Download to temp location
        temp_path = f"/tmp/{Path(local_path).name}"

        if not self.download(key, temp_path):
            return False

        remote_checksum = self.calculate_checksum(temp_path)

        # Cleanup
        Path(temp_path).unlink()

        match = local_checksum == remote_checksum

        if match:
            logger.info(f"✓ Upload verified: {key}")
        else:
            logger.error(f"✗ Upload verification failed: {key}")
            logger.error(f"  Local checksum:  {local_checksum}")
            logger.error(f"  Remote checksum: {remote_checksum}")

        return match


# Example usage
if __name__ == '__main__':
    # S3 configuration
    s3_config = StorageConfig(
        provider='s3',
        bucket_name='netflix-content-test',
        region='us-east-1',
        cdn_domain='d123456.cloudfront.net',
        cdn_distribution_id='E1234567890ABC',
        enable_encryption=True
    )

    # Create storage manager
    storage = StorageManager(s3_config)

    # Upload single file
    result = storage.upload(
        local_path='test_video.mp4',
        key='content/test/video.mp4',
        metadata={'content_id': '12345', 'quality': '1080p'}
    )

    print(f"Upload result: {result}")
    print(f"CDN URL: {result.cdn_url}")

    # Upload directory
    results = storage.upload_directory(
        local_dir='output/movie_123',
        prefix='content/movie_123',
        parallel=True
    )

    # Get temporary download URL
    url = storage.get_url('content/test/video.mp4', temporary=True, expires_in=3600)
    print(f"Temporary URL: {url}")

    # List files
    files = storage.list(prefix='content/movie_123')
    print(f"Files: {files}")
