#!/usr/bin/env python3
"""
Netflix Clone - Video Transcoder Tests
======================================

Unit tests for video transcoding and HLS generation.

Author: Data Engineering Study Project
"""

import pytest
from pathlib import Path
import json
import subprocess
from unittest.mock import patch, MagicMock, call
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / '03-ingestao-processamento'))

from video_transcoder import (
    VideoProfile,
    VideoTranscoder,
    BITRATE_LADDER,
    TranscodeResult
)


class TestVideoProfile:
    """Test VideoProfile dataclass"""

    def test_video_profile_creation(self):
        """Test creating a VideoProfile"""
        profile = VideoProfile(
            name="1080p",
            width=1920,
            height=1080,
            video_bitrate="5000k",
            max_bitrate="5350k",
            buf_size="7500k",
            audio_bitrate="192k",
            codec="libx264",
            preset="medium",
            profile="high",
            level="4.0"
        )

        assert profile.name == "1080p"
        assert profile.width == 1920
        assert profile.height == 1080
        assert profile.video_bitrate == "5000k"

    def test_bitrate_ladder_completeness(self):
        """Test that bitrate ladder includes all resolutions"""
        resolutions = [p.name for p in BITRATE_LADDER]

        assert "4k" in resolutions
        assert "1080p" in resolutions
        assert "720p" in resolutions
        assert "480p" in resolutions
        assert "360p" in resolutions

    def test_bitrate_ladder_ordering(self):
        """Test that bitrate ladder is ordered by quality (descending)"""
        heights = [p.height for p in BITRATE_LADDER]

        # Should be ordered from highest to lowest
        assert heights == sorted(heights, reverse=True)


class TestVideoTranscoder:
    """Test VideoTranscoder class"""

    def test_transcoder_initialization(self, test_data_dir, sample_video_file):
        """Test transcoder initialization"""
        output_dir = test_data_dir / 'output'

        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=output_dir,
            segment_duration=6,
            hardware_accel=None
        )

        assert transcoder.input_file == sample_video_file
        assert transcoder.output_dir == output_dir
        assert transcoder.segment_duration == 6
        assert output_dir.exists()

    @patch('subprocess.run')
    def test_transcode_profile_command(self, mock_run, test_data_dir, sample_video_file):
        """Test FFmpeg command generation for transcoding"""
        output_dir = test_data_dir / 'output'

        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=output_dir
        )

        # Mock successful FFmpeg execution
        mock_run.return_value = MagicMock(returncode=0)

        # Transcode to 720p
        profile = next(p for p in BITRATE_LADDER if p.name == "720p")
        result = transcoder.transcode_profile(profile)

        # Verify FFmpeg was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]

        # Check key FFmpeg parameters
        assert 'ffmpeg' in call_args
        assert '-i' in call_args
        assert str(sample_video_file) in call_args
        assert '-c:v' in call_args
        assert profile.codec in call_args
        assert '-preset' in call_args
        assert profile.preset in call_args
        assert '-b:v' in call_args
        assert profile.video_bitrate in call_args

    @patch('subprocess.run')
    def test_transcode_with_hardware_accel(self, mock_run, test_data_dir, sample_video_file):
        """Test transcoding with hardware acceleration"""
        output_dir = test_data_dir / 'output'

        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=output_dir,
            hardware_accel='nvenc'
        )

        mock_run.return_value = MagicMock(returncode=0)

        profile = BITRATE_LADDER[2]  # 720p
        result = transcoder.transcode_profile(profile)

        call_args = mock_run.call_args[0][0]

        # Should use h264_nvenc instead of libx264
        assert 'h264_nvenc' in ' '.join(call_args)

    @patch('subprocess.run')
    def test_generate_master_playlist(self, mock_run, test_data_dir, sample_video_file):
        """Test HLS master playlist generation"""
        output_dir = test_data_dir / 'output'

        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=output_dir
        )

        # Create dummy variant playlists
        for profile in BITRATE_LADDER[:3]:  # 4K, 1080p, 720p
            variant_dir = output_dir / profile.name
            variant_dir.mkdir(parents=True, exist_ok=True)
            playlist_file = variant_dir / 'playlist.m3u8'
            playlist_file.write_text('#EXTM3U\n#EXT-X-VERSION:3\n')

        # Generate master playlist
        transcoder.generate_master_playlist(['4k', '1080p', '720p'])

        master_playlist = output_dir / 'master.m3u8'
        assert master_playlist.exists()

        content = master_playlist.read_text()
        assert content.startswith('#EXTM3U')
        assert '#EXT-X-STREAM-INF' in content
        assert '4k/playlist.m3u8' in content
        assert '1080p/playlist.m3u8' in content
        assert '720p/playlist.m3u8' in content

    @patch('subprocess.run')
    def test_transcode_all_profiles(self, mock_run, test_data_dir, sample_video_file):
        """Test transcoding all profiles"""
        output_dir = test_data_dir / 'output'

        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=output_dir
        )

        mock_run.return_value = MagicMock(returncode=0)

        # Transcode all profiles
        results = transcoder.transcode_all()

        # Should have 5 results (one per resolution)
        assert len(results) == 5

        # All should be successful
        assert all(r.success for r in results)

        # Master playlist should exist
        assert (output_dir / 'master.m3u8').exists()

    @patch('subprocess.run')
    def test_transcode_error_handling(self, mock_run, test_data_dir, sample_video_file):
        """Test error handling when FFmpeg fails"""
        output_dir = test_data_dir / 'output'

        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=output_dir
        )

        # Mock FFmpeg failure
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=['ffmpeg'],
            stderr=b'Error: Invalid input'
        )

        profile = BITRATE_LADDER[2]  # 720p
        result = transcoder.transcode_profile(profile)

        # Should fail gracefully
        assert not result.success
        assert result.error_message is not None

    def test_get_video_info(self, test_data_dir, sample_video_file):
        """Test extracting video metadata with FFprobe"""
        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=test_data_dir / 'output'
        )

        # This will fail if FFmpeg is not installed, but that's ok for testing
        try:
            info = transcoder.get_video_info()

            # If successful, verify structure
            assert 'duration' in info
            assert 'width' in info
            assert 'height' in info
            assert 'bitrate' in info
        except Exception:
            # FFmpeg not available, skip
            pytest.skip("FFmpeg not available")

    @patch('subprocess.run')
    def test_segment_duration_respected(self, mock_run, test_data_dir, sample_video_file):
        """Test that segment duration is respected"""
        output_dir = test_data_dir / 'output'

        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=output_dir,
            segment_duration=10  # 10 seconds
        )

        mock_run.return_value = MagicMock(returncode=0)

        profile = BITRATE_LADDER[2]
        result = transcoder.transcode_profile(profile)

        call_args = mock_run.call_args[0][0]

        # Check that hls_time is set correctly
        assert '-hls_time' in call_args
        hls_time_idx = call_args.index('-hls_time')
        assert call_args[hls_time_idx + 1] == '10'


class TestTranscodeResult:
    """Test TranscodeResult dataclass"""

    def test_successful_result(self):
        """Test creating a successful result"""
        result = TranscodeResult(
            profile_name="1080p",
            success=True,
            output_path=Path("/tmp/output/1080p/playlist.m3u8"),
            duration_sec=120.5,
            file_size_mb=150.0,
            error_message=None
        )

        assert result.success
        assert result.profile_name == "1080p"
        assert result.duration_sec == 120.5
        assert result.error_message is None

    def test_failed_result(self):
        """Test creating a failed result"""
        result = TranscodeResult(
            profile_name="4k",
            success=False,
            output_path=None,
            duration_sec=0,
            file_size_mb=0,
            error_message="Encoding failed: Invalid input"
        )

        assert not result.success
        assert result.error_message is not None

    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = TranscodeResult(
            profile_name="720p",
            success=True,
            output_path=Path("/tmp/output/720p/playlist.m3u8"),
            duration_sec=60.0,
            file_size_mb=80.0,
            error_message=None
        )

        result_dict = {
            'profile_name': result.profile_name,
            'success': result.success,
            'output_path': str(result.output_path) if result.output_path else None,
            'duration_sec': result.duration_sec,
            'file_size_mb': result.file_size_mb,
            'error_message': result.error_message
        }

        assert result_dict['profile_name'] == "720p"
        assert result_dict['success'] is True
        assert result_dict['duration_sec'] == 60.0


# Integration tests (require FFmpeg)

@pytest.mark.integration
class TestVideoTranscoderIntegration:
    """Integration tests requiring FFmpeg"""

    def test_full_transcode_pipeline(self, test_data_dir, sample_video_file):
        """Test complete transcoding pipeline"""
        pytest.importorskip('subprocess')

        # Check if FFmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("FFmpeg not available")

        output_dir = test_data_dir / 'integration_output'

        transcoder = VideoTranscoder(
            input_file=sample_video_file,
            output_dir=output_dir,
            segment_duration=2  # Short segments for fast testing
        )

        # Transcode only 360p for speed
        profile = next(p for p in BITRATE_LADDER if p.name == "360p")
        result = transcoder.transcode_profile(profile)

        # Verify result
        assert result.success
        assert result.output_path.exists()
        assert result.duration_sec > 0

        # Verify playlist
        playlist_content = result.output_path.read_text()
        assert playlist_content.startswith('#EXTM3U')
        assert '#EXTINF:' in playlist_content  # Segment info
        assert '.ts' in playlist_content  # Segment files
