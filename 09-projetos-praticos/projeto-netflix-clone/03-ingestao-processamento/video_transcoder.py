#!/usr/bin/env python3
"""
Netflix Clone - Video Transcoding Pipeline
==========================================

Transcode source videos to multiple resolutions with HLS segmentation.

Features:
- Multiple bitrate ladder (360p to 4K)
- HLS/DASH output with segmentation
- VMAF quality scoring
- Hardware acceleration support (NVENC, VideoToolbox)
- Parallel transcoding
- Progress tracking

Usage:
    python video_transcoder.py --input /path/to/source.mp4 --output /path/to/output/

Author: Data Engineering Study Project
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class VideoProfile:
    """Video encoding profile for a specific resolution"""
    name: str
    width: int
    height: int
    video_bitrate: str  # e.g., "5000k"
    max_bitrate: str  # e.g., "5350k"
    buf_size: str  # e.g., "7500k"
    audio_bitrate: str  # e.g., "192k"
    codec: str  # "libx264" or "libx265"
    preset: str  # "slow", "medium", "fast", "veryfast"
    profile: str  # "baseline", "main", "high"
    level: str  # "3.1", "4.0", "4.1", etc.

    def to_dict(self):
        return asdict(self)


# Netflix-style bitrate ladder
BITRATE_LADDER = [
    VideoProfile(
        name="4k",
        width=3840,
        height=2160,
        video_bitrate="15000k",
        max_bitrate="16500k",
        buf_size="22500k",
        audio_bitrate="256k",
        codec="libx265",  # HEVC for 4K
        preset="slow",
        profile="main",
        level="5.1"
    ),
    VideoProfile(
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
    ),
    VideoProfile(
        name="720p",
        width=1280,
        height=720,
        video_bitrate="2500k",
        max_bitrate="2675k",
        buf_size="3750k",
        audio_bitrate="128k",
        codec="libx264",
        preset="medium",
        profile="high",
        level="3.1"
    ),
    VideoProfile(
        name="480p",
        width=854,
        height=480,
        video_bitrate="1000k",
        max_bitrate="1100k",
        buf_size="1500k",
        audio_bitrate="96k",
        codec="libx264",
        preset="fast",
        profile="main",
        level="3.1"
    ),
    VideoProfile(
        name="360p",
        width=640,
        height=360,
        video_bitrate="500k",
        max_bitrate="550k",
        buf_size="750k",
        audio_bitrate="64k",
        codec="libx264",
        preset="fast",
        profile="baseline",
        level="3.0"
    ),
]


class VideoTranscoder:
    """
    Handles video transcoding to multiple resolutions
    """

    def __init__(self, input_file: str, output_dir: str,
                 segment_duration: int = 6,
                 use_hardware_accel: bool = False):
        """
        Initialize transcoder

        Args:
            input_file: Path to source video
            output_dir: Output directory
            segment_duration: HLS segment duration in seconds
            use_hardware_accel: Use hardware acceleration (NVENC, VideoToolbox)
        """
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.segment_duration = segment_duration
        self.use_hardware_accel = use_hardware_accel

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Validate input
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Check FFmpeg availability
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Verify FFmpeg is installed"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"FFmpeg version: {result.stdout.split()[2]}")
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")

    def get_video_info(self) -> Dict:
        """
        Extract video metadata using ffprobe

        Returns:
            Dictionary with video information
        """
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(self.input_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Find video stream
        video_stream = next(
            (s for s in data['streams'] if s['codec_type'] == 'video'),
            None
        )

        if not video_stream:
            raise ValueError("No video stream found in input file")

        # Find audio stream
        audio_stream = next(
            (s for s in data['streams'] if s['codec_type'] == 'audio'),
            None
        )

        info = {
            'duration': float(data['format'].get('duration', 0)),
            'size': int(data['format'].get('size', 0)),
            'bitrate': int(data['format'].get('bit_rate', 0)),
            'video': {
                'codec': video_stream.get('codec_name'),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                'bitrate': int(video_stream.get('bit_rate', 0)) if 'bit_rate' in video_stream else 0,
            },
            'audio': {
                'codec': audio_stream.get('codec_name') if audio_stream else None,
                'sample_rate': int(audio_stream.get('sample_rate', 0)) if audio_stream else 0,
                'channels': int(audio_stream.get('channels', 0)) if audio_stream else 0,
            } if audio_stream else None
        }

        logger.info(f"Video info: {info['video']['width']}x{info['video']['height']} "
                   f"@ {info['video']['fps']:.2f}fps, "
                   f"duration: {info['duration']:.2f}s")

        return info

    def transcode_profile(self, profile: VideoProfile) -> Tuple[bool, str, Dict]:
        """
        Transcode video to a specific profile

        Args:
            profile: Video profile to transcode to

        Returns:
            Tuple of (success, output_path, stats)
        """
        logger.info(f"Starting transcoding: {profile.name}")
        start_time = time.time()

        # Output paths
        profile_dir = self.output_dir / profile.name
        profile_dir.mkdir(exist_ok=True)

        output_file = profile_dir / "output.m3u8"
        segment_pattern = str(profile_dir / "segment_%05d.ts")

        # Build FFmpeg command
        cmd = ['ffmpeg', '-i', str(self.input_file)]

        # Hardware acceleration (optional)
        if self.use_hardware_accel:
            # Try NVENC (NVIDIA)
            cmd.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
            codec = 'h264_nvenc' if profile.codec == 'libx264' else 'hevc_nvenc'
        else:
            codec = profile.codec

        # Video encoding settings
        cmd.extend([
            # Video codec
            '-c:v', codec,
            '-preset', profile.preset,
            '-profile:v', profile.profile,
            '-level', profile.level,

            # Resolution
            '-vf', f'scale={profile.width}:{profile.height}',

            # Bitrate settings
            '-b:v', profile.video_bitrate,
            '-maxrate', profile.max_bitrate,
            '-bufsize', profile.buf_size,

            # GOP settings (2 seconds for better seeking)
            '-g', '48',  # GOP size = fps * 2
            '-keyint_min', '48',
            '-sc_threshold', '0',  # Disable scene change detection

            # Audio encoding
            '-c:a', 'aac',
            '-b:a', profile.audio_bitrate,
            '-ar', '48000',  # Sample rate
            '-ac', '2',  # Stereo

            # HLS settings
            '-f', 'hls',
            '-hls_time', str(self.segment_duration),
            '-hls_playlist_type', 'vod',
            '-hls_segment_type', 'mpegts',
            '-hls_segment_filename', segment_pattern,

            # Output
            str(output_file),

            # Overwrite without asking
            '-y'
        ])

        # Log command (for debugging)
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        # Execute FFmpeg
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Parse progress from stderr
            for line in process.stderr:
                if 'time=' in line:
                    # Extract time (format: time=00:01:23.45)
                    try:
                        time_str = line.split('time=')[1].split()[0]
                        # Convert to seconds
                        h, m, s = time_str.split(':')
                        current_time = int(h) * 3600 + int(m) * 60 + float(s)
                        # Log progress every 30 seconds
                        if int(current_time) % 30 == 0:
                            logger.info(f"{profile.name}: {current_time:.1f}s processed")
                    except (IndexError, ValueError):
                        pass

            process.wait()

            if process.returncode != 0:
                stderr = process.stderr.read()
                logger.error(f"Transcoding failed for {profile.name}: {stderr}")
                return False, "", {}

            elapsed_time = time.time() - start_time

            # Get output file size
            total_size = sum(
                f.stat().st_size
                for f in profile_dir.glob('*')
                if f.is_file()
            )

            stats = {
                'profile': profile.name,
                'success': True,
                'elapsed_time': elapsed_time,
                'output_size': total_size,
                'output_path': str(output_file),
                'segment_count': len(list(profile_dir.glob('segment_*.ts')))
            }

            logger.info(f"Completed {profile.name}: {elapsed_time:.1f}s, "
                       f"{total_size / (1024**2):.1f} MB")

            return True, str(output_file), stats

        except Exception as e:
            logger.error(f"Exception during transcoding {profile.name}: {e}")
            return False, "", {}

    def transcode_all(self, profiles: Optional[List[VideoProfile]] = None,
                      parallel: bool = True,
                      max_workers: int = 3) -> Dict:
        """
        Transcode to all profiles

        Args:
            profiles: List of profiles (default: BITRATE_LADDER)
            parallel: Run transcoding in parallel
            max_workers: Max parallel workers

        Returns:
            Dictionary with results
        """
        if profiles is None:
            profiles = BITRATE_LADDER

        logger.info(f"Starting transcoding to {len(profiles)} profiles")
        start_time = time.time()

        results = {
            'input_file': str(self.input_file),
            'start_time': datetime.utcnow().isoformat(),
            'profiles': []
        }

        if parallel:
            # Parallel transcoding
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.transcode_profile, profile): profile
                    for profile in profiles
                }

                for future in as_completed(futures):
                    profile = futures[future]
                    try:
                        success, output_path, stats = future.result()
                        results['profiles'].append(stats)
                    except Exception as e:
                        logger.error(f"Transcoding {profile.name} raised exception: {e}")
                        results['profiles'].append({
                            'profile': profile.name,
                            'success': False,
                            'error': str(e)
                        })
        else:
            # Sequential transcoding
            for profile in profiles:
                success, output_path, stats = self.transcode_profile(profile)
                results['profiles'].append(stats)

        elapsed_time = time.time() - start_time
        results['total_time'] = elapsed_time
        results['end_time'] = datetime.utcnow().isoformat()

        # Summary
        successful = sum(1 for p in results['profiles'] if p.get('success'))
        total_size = sum(p.get('output_size', 0) for p in results['profiles'])

        logger.info(f"Transcoding complete: {successful}/{len(profiles)} successful, "
                   f"total time: {elapsed_time:.1f}s, "
                   f"total size: {total_size / (1024**3):.2f} GB")

        # Save results to JSON
        results_file = self.output_dir / 'transcode_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {results_file}")

        return results

    def generate_master_playlist(self, results: Dict) -> str:
        """
        Generate HLS master playlist (master.m3u8)

        Args:
            results: Transcoding results from transcode_all()

        Returns:
            Path to master playlist
        """
        master_playlist = self.output_dir / 'master.m3u8'

        with open(master_playlist, 'w') as f:
            f.write('#EXTM3U\n')
            f.write('#EXT-X-VERSION:3\n\n')

            for profile_result in results['profiles']:
                if not profile_result.get('success'):
                    continue

                # Find matching profile
                profile = next(
                    p for p in BITRATE_LADDER
                    if p.name == profile_result['profile']
                )

                # Extract bitrate in bits/second
                video_bitrate = int(profile.video_bitrate.replace('k', '')) * 1000
                audio_bitrate = int(profile.audio_bitrate.replace('k', '')) * 1000
                bandwidth = video_bitrate + audio_bitrate

                # Write variant stream
                f.write(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},'
                       f'RESOLUTION={profile.width}x{profile.height},'
                       f'CODECS="{"hvc1.1.6.L150.90" if profile.codec == "libx265" else "avc1.640028"},mp4a.40.2"\n')
                f.write(f'{profile.name}/output.m3u8\n\n')

        logger.info(f"Master playlist created: {master_playlist}")
        return str(master_playlist)

    def calculate_vmaf(self, profile: VideoProfile,
                       model: str = 'vmaf_v0.6.1') -> Optional[float]:
        """
        Calculate VMAF (Video Multimethod Assessment Fusion) score

        VMAF is Netflix's perceptual video quality metric (0-100, higher is better)
        Target: >85 for good quality

        Args:
            profile: Video profile to evaluate
            model: VMAF model to use

        Returns:
            VMAF score (0-100) or None on error
        """
        logger.info(f"Calculating VMAF for {profile.name}...")

        encoded_file = self.output_dir / profile.name / 'segment_00000.ts'

        if not encoded_file.exists():
            logger.error(f"Encoded file not found: {encoded_file}")
            return None

        # FFmpeg VMAF filter
        cmd = [
            'ffmpeg',
            '-i', str(encoded_file),
            '-i', str(self.input_file),
            '-lavfi', f'[0:v]scale={profile.width}:{profile.height}[ref];'
                     f'[1:v][ref]libvmaf=model_path=/usr/share/model/{model}.pkl',
            '-f', 'null',
            '-'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            # Parse VMAF score from output
            for line in result.stderr.split('\n'):
                if 'VMAF score' in line:
                    score = float(line.split('score:')[1].strip())
                    logger.info(f"VMAF score for {profile.name}: {score:.2f}")
                    return score

            logger.warning(f"Could not parse VMAF score for {profile.name}")
            return None

        except subprocess.TimeoutExpired:
            logger.error(f"VMAF calculation timed out for {profile.name}")
            return None
        except Exception as e:
            logger.error(f"VMAF calculation failed: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description='Transcode video to multiple resolutions for streaming'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input video file'
    )
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output directory'
    )
    parser.add_argument(
        '--profiles',
        nargs='+',
        choices=['4k', '1080p', '720p', '480p', '360p'],
        default=None,
        help='Profiles to transcode (default: all)'
    )
    parser.add_argument(
        '--segment-duration',
        type=int,
        default=6,
        help='HLS segment duration in seconds (default: 6)'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        default=True,
        help='Run transcoding in parallel (default: True)'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=3,
        help='Max parallel workers (default: 3)'
    )
    parser.add_argument(
        '--hardware-accel',
        action='store_true',
        help='Use hardware acceleration (NVENC, VideoToolbox)'
    )
    parser.add_argument(
        '--vmaf',
        action='store_true',
        help='Calculate VMAF quality scores'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Filter profiles
    profiles = BITRATE_LADDER
    if args.profiles:
        profiles = [p for p in BITRATE_LADDER if p.name in args.profiles]

    # Create transcoder
    transcoder = VideoTranscoder(
        input_file=args.input,
        output_dir=args.output,
        segment_duration=args.segment_duration,
        use_hardware_accel=args.hardware_accel
    )

    # Get video info
    video_info = transcoder.get_video_info()

    # Transcode
    results = transcoder.transcode_all(
        profiles=profiles,
        parallel=args.parallel,
        max_workers=args.max_workers
    )

    # Generate master playlist
    master_playlist = transcoder.generate_master_playlist(results)

    # Calculate VMAF scores (optional)
    if args.vmaf:
        for profile in profiles:
            vmaf_score = transcoder.calculate_vmaf(profile)
            if vmaf_score:
                logger.info(f"VMAF {profile.name}: {vmaf_score:.2f}/100")

    # Success summary
    successful = sum(1 for p in results['profiles'] if p.get('success'))
    if successful == len(profiles):
        logger.info("✓ All profiles transcoded successfully!")
        logger.info(f"Master playlist: {master_playlist}")
        return 0
    else:
        logger.error(f"✗ Only {successful}/{len(profiles)} profiles succeeded")
        return 1


if __name__ == '__main__':
    sys.exit(main())
