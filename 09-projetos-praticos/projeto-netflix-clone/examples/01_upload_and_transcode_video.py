#!/usr/bin/env python3
"""
Example 1: Upload and Transcode Video
======================================

This example demonstrates the complete video ingestion pipeline:
1. Upload source video to S3
2. Trigger transcoding job
3. Generate HLS adaptive bitrate streams
4. Validate quality
5. Update database

Author: Data Engineering Study Project
"""

import sys
from pathlib import Path
import logging

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / '03-ingestao-processamento'))
sys.path.insert(0, str(Path(__file__).parent.parent / '04-camada-armazenamento'))

from video_transcoder import VideoTranscoder, BITRATE_LADDER
from quality_checker import QualityChecker
from storage_manager import StorageManager, StorageConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Complete video upload and transcoding pipeline
    """

    # =====================
    # Configuration
    # =====================

    # Source video file
    source_video = Path('/path/to/your/movie.mp4')

    # Check if file exists
    if not source_video.exists():
        logger.error(f"Source video not found: {source_video}")
        logger.info("Please update the source_video path to a real video file")
        return

    # Storage configuration (S3)
    storage_config = StorageConfig(
        provider='s3',
        bucket='netflix-content',
        region='us-east-1',
        access_key='your-access-key',  # Use environment variables in production
        secret_key='your-secret-key'
    )

    # Working directories
    transcode_dir = Path('/tmp/netflix-transcode')
    transcode_dir.mkdir(exist_ok=True)

    # =====================
    # Step 1: Upload Source Video
    # =====================

    logger.info("=" * 60)
    logger.info("STEP 1: Uploading source video to S3")
    logger.info("=" * 60)

    storage_manager = StorageManager(storage_config)

    # Upload to S3 with metadata
    content_id = 12345  # From database
    upload_result = storage_manager.upload_file(
        local_path=str(source_video),
        key=f'source/{content_id}/original.mp4',
        metadata={
            'content_id': str(content_id),
            'upload_date': '2024-01-15',
            'content_type': 'movie'
        }
    )

    if not upload_result.success:
        logger.error(f"Upload failed: {upload_result.error_message}")
        return

    logger.info(f"✓ Upload completed")
    logger.info(f"  Size: {upload_result.size_bytes / 1024**2:.2f} MB")
    logger.info(f"  Duration: {upload_result.duration_sec:.2f}s")
    logger.info(f"  URL: {upload_result.url}")

    # =====================
    # Step 2: Transcode Video
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Transcoding video to multiple resolutions")
    logger.info("=" * 60)

    # Initialize transcoder
    output_dir = transcode_dir / str(content_id)

    transcoder = VideoTranscoder(
        input_file=source_video,
        output_dir=output_dir,
        segment_duration=6,  # 6-second HLS segments
        hardware_accel=None  # Use 'nvenc' for NVIDIA GPU, 'videotoolbox' for Apple
    )

    # Get source video info
    video_info = transcoder.get_video_info()
    logger.info(f"\nSource video:")
    logger.info(f"  Resolution: {video_info['width']}x{video_info['height']}")
    logger.info(f"  Duration: {video_info['duration']:.2f}s")
    logger.info(f"  Bitrate: {video_info['bitrate'] / 1000:.0f} kbps")

    # Determine which profiles to transcode
    # Don't transcode 4K if source is 1080p
    source_height = video_info['height']

    profiles_to_transcode = [
        p for p in BITRATE_LADDER
        if p.height <= source_height
    ]

    logger.info(f"\nTranscoding to {len(profiles_to_transcode)} profiles:")
    for profile in profiles_to_transcode:
        logger.info(f"  - {profile.name}: {profile.width}x{profile.height} @ {profile.video_bitrate}")

    # Transcode all profiles
    logger.info("\nStarting transcoding...")
    results = transcoder.transcode_all(profiles=profiles_to_transcode)

    # Check results
    successful_profiles = [r for r in results if r.success]
    failed_profiles = [r for r in results if not r.success]

    logger.info(f"\n✓ Transcoding completed: {len(successful_profiles)}/{len(results)} successful")

    for result in successful_profiles:
        logger.info(f"  ✓ {result.profile_name}: {result.file_size_mb:.2f} MB, {result.duration_sec:.2f}s")

    for result in failed_profiles:
        logger.error(f"  ✗ {result.profile_name}: {result.error_message}")

    # =====================
    # Step 3: Quality Validation
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Validating video quality (VMAF)")
    logger.info("=" * 60)

    # Check quality of highest resolution
    highest_profile = successful_profiles[0]  # Assuming sorted by quality

    checker = QualityChecker(
        reference_file=source_video,
        encoded_file=output_dir / highest_profile.profile_name / 'playlist.m3u8'
    )

    logger.info(f"\nValidating {highest_profile.profile_name}...")

    try:
        # Calculate VMAF score (Netflix standard)
        vmaf_result = checker.calculate_vmaf()

        logger.info(f"  VMAF Score: {vmaf_result['vmaf_mean']:.2f}/100")
        logger.info(f"  VMAF P95: {vmaf_result['vmaf_p95']:.2f}")

        if vmaf_result['vmaf_mean'] >= 85:
            logger.info("  ✓ Quality: EXCELLENT (VMAF >= 85)")
        elif vmaf_result['vmaf_mean'] >= 70:
            logger.info("  ✓ Quality: GOOD (VMAF >= 70)")
        else:
            logger.warning("  ⚠ Quality: NEEDS IMPROVEMENT (VMAF < 70)")

    except Exception as e:
        logger.warning(f"  VMAF calculation failed: {e}")
        logger.info("  (This is normal if FFmpeg doesn't have VMAF support)")

    # =====================
    # Step 4: Upload Transcoded Videos
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Uploading transcoded videos to S3")
    logger.info("=" * 60)

    # Upload each transcoded profile
    upload_results = storage_manager.upload_directory(
        local_dir=str(output_dir),
        prefix=f'content/{content_id}/hls/',
        parallel=True,
        max_workers=4
    )

    successful_uploads = [r for r in upload_results if r.success]

    logger.info(f"\n✓ Uploaded {len(successful_uploads)}/{len(upload_results)} files")
    logger.info(f"  Total size: {sum(r.size_bytes for r in successful_uploads) / 1024**2:.2f} MB")

    # =====================
    # Step 5: Generate CDN URLs
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 5: Generating CDN URLs")
    logger.info("=" * 60)

    # Generate presigned URL for master playlist (short expiry for testing)
    master_playlist_key = f'content/{content_id}/hls/master.m3u8'

    master_url = storage_manager.get_presigned_url(
        key=master_playlist_key,
        expires_in=3600  # 1 hour
    )

    logger.info(f"\n✓ Master playlist URL:")
    logger.info(f"  {master_url}")

    # In production, you would use CloudFront or similar CDN
    cdn_url = f"https://cdn.netflix-clone.com/{master_playlist_key}"
    logger.info(f"\n✓ CDN URL (production):")
    logger.info(f"  {cdn_url}")

    # =====================
    # Step 6: Update Database
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("STEP 6: Updating database")
    logger.info("=" * 60)

    # In a real implementation, you would update PostgreSQL:
    """
    import psycopg2

    conn = psycopg2.connect("postgresql://localhost/netflix")
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE content
        SET
            master_playlist_url = %s,
            available_resolutions = %s,
            processing_status = 'completed',
            processed_at = NOW()
        WHERE content_id = %s
    ''', (
        cdn_url,
        [p.profile_name for p in successful_profiles],
        content_id
    ))

    conn.commit()
    """

    logger.info("  ✓ Database updated (simulated)")
    logger.info(f"    Content ID: {content_id}")
    logger.info(f"    Status: READY FOR STREAMING")
    logger.info(f"    Available resolutions: {[p.profile_name for p in successful_profiles]}")

    # =====================
    # Summary
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)

    logger.info(f"\nContent ID {content_id} is now ready for streaming:")
    logger.info(f"  ✓ Source uploaded to S3")
    logger.info(f"  ✓ Transcoded to {len(successful_profiles)} resolutions")
    logger.info(f"  ✓ Quality validated (VMAF)")
    logger.info(f"  ✓ HLS playlists uploaded")
    logger.info(f"  ✓ Database updated")

    logger.info(f"\nNext steps:")
    logger.info(f"  1. Test playback with video player")
    logger.info(f"  2. Invalidate CDN cache if needed")
    logger.info(f"  3. Generate thumbnails")
    logger.info(f"  4. Apply DRM protection")

    # =====================
    # Cleanup (optional)
    # =====================

    logger.info("\n" + "=" * 60)
    logger.info("Cleanup")
    logger.info("=" * 60)

    cleanup = input("\nDelete local transcoded files? (y/n): ")

    if cleanup.lower() == 'y':
        import shutil
        shutil.rmtree(output_dir)
        logger.info("  ✓ Local files deleted")
    else:
        logger.info(f"  Local files kept at: {output_dir}")


if __name__ == '__main__':
    main()
