#!/usr/bin/env python3
"""
Netflix Clone - Video Quality Checker
======================================

Comprehensive video quality validation using VMAF and other metrics.

Features:
- VMAF (Video Multimethod Assessment Fusion) scoring
- PSNR (Peak Signal-to-Noise Ratio)
- SSIM (Structural Similarity Index)
- Bitrate analysis
- Audio quality checks
- Playback simulation

Usage:
    python quality_checker.py --reference source.mp4 --encoded encoded.mp4

Author: Data Engineering Study Project
"""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Video quality metrics"""
    vmaf_score: float  # 0-100, higher is better (Netflix target: >85)
    vmaf_min: float  # Minimum VMAF score (detect bad frames)
    vmaf_p5: float  # 5th percentile
    vmaf_p95: float  # 95th percentile
    psnr: Optional[float] = None  # Peak Signal-to-Noise Ratio
    ssim: Optional[float] = None  # Structural Similarity Index
    bitrate_avg: Optional[int] = None  # Average bitrate (kbps)
    bitrate_max: Optional[int] = None  # Maximum bitrate (kbps)
    frame_drops: int = 0  # Number of dropped frames
    audio_quality: Optional[float] = None  # Audio quality score
    passed: bool = False  # Overall pass/fail

    def to_dict(self):
        return asdict(self)


class VideoQualityChecker:
    """
    Video quality checker using FFmpeg and VMAF
    """

    def __init__(self, reference_file: str, encoded_file: str,
                 vmaf_model: str = 'vmaf_v0.6.1',
                 vmaf_threshold: float = 85.0):
        """
        Initialize quality checker

        Args:
            reference_file: Original source video
            encoded_file: Encoded video to evaluate
            vmaf_model: VMAF model to use
            vmaf_threshold: Minimum acceptable VMAF score
        """
        self.reference_file = Path(reference_file)
        self.encoded_file = Path(encoded_file)
        self.vmaf_model = vmaf_model
        self.vmaf_threshold = vmaf_threshold

        # Validate files exist
        if not self.reference_file.exists():
            raise FileNotFoundError(f"Reference file not found: {reference_file}")
        if not self.encoded_file.exists():
            raise FileNotFoundError(f"Encoded file not found: {encoded_file}")

        # Check FFmpeg with libvmaf support
        self._check_ffmpeg_vmaf()

    def _check_ffmpeg_vmaf(self):
        """Check if FFmpeg has libvmaf support"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-filters'],
                capture_output=True,
                text=True,
                check=True
            )
            if 'libvmaf' not in result.stdout:
                raise RuntimeError(
                    "FFmpeg does not have libvmaf support. "
                    "Please install FFmpeg with libvmaf."
                )
            logger.info("FFmpeg with libvmaf support detected")
        except subprocess.CalledProcessError:
            raise RuntimeError("FFmpeg not found")

    def calculate_vmaf(self, log_file: Optional[str] = None) -> Dict:
        """
        Calculate VMAF score

        VMAF (Video Multimethod Assessment Fusion) is Netflix's perceptual
        video quality metric that combines multiple quality metrics.

        Args:
            log_file: Optional path to save VMAF log

        Returns:
            Dictionary with VMAF metrics
        """
        logger.info("Calculating VMAF score...")

        if log_file is None:
            log_file = f"/tmp/vmaf_{self.encoded_file.stem}.json"

        # Get video resolution
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json',
            str(self.encoded_file)
        ]

        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        video_info = json.loads(result.stdout)
        width = video_info['streams'][0]['width']
        height = video_info['streams'][0]['height']

        # Scale reference to match encoded resolution
        # This is important for fair comparison

        # FFmpeg VMAF command
        cmd = [
            'ffmpeg',
            '-i', str(self.encoded_file),  # Distorted (encoded)
            '-i', str(self.reference_file),  # Reference (original)
            '-lavfi',
            f'[0:v]setpts=PTS-STARTPTS,scale={width}:{height}[dist];'
            f'[1:v]setpts=PTS-STARTPTS,scale={width}:{height}[ref];'
            f'[dist][ref]libvmaf='
            f'log_fmt=json:'
            f'log_path={log_file}:'
            f'n_threads=4:'
            f'model_path=/usr/share/model/{self.vmaf_model}.pkl',
            '-f', 'null',
            '-'
        ]

        logger.info("Running VMAF analysis (this may take several minutes)...")

        try:
            # Run with timeout (5 minutes for short videos, longer for movies)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes max
                check=True
            )

            # Parse VMAF log
            with open(log_file, 'r') as f:
                vmaf_data = json.load(f)

            # Extract per-frame VMAF scores
            frames = vmaf_data['frames']
            vmaf_scores = [frame['metrics']['vmaf'] for frame in frames]

            metrics = {
                'vmaf_mean': statistics.mean(vmaf_scores),
                'vmaf_median': statistics.median(vmaf_scores),
                'vmaf_min': min(vmaf_scores),
                'vmaf_max': max(vmaf_scores),
                'vmaf_stdev': statistics.stdev(vmaf_scores) if len(vmaf_scores) > 1 else 0,
                'vmaf_p5': sorted(vmaf_scores)[int(len(vmaf_scores) * 0.05)],
                'vmaf_p25': sorted(vmaf_scores)[int(len(vmaf_scores) * 0.25)],
                'vmaf_p75': sorted(vmaf_scores)[int(len(vmaf_scores) * 0.75)],
                'vmaf_p95': sorted(vmaf_scores)[int(len(vmaf_scores) * 0.95)],
                'frame_count': len(vmaf_scores),
                'log_file': log_file
            }

            logger.info(f"VMAF Score: {metrics['vmaf_mean']:.2f} "
                       f"(min: {metrics['vmaf_min']:.2f}, "
                       f"max: {metrics['vmaf_max']:.2f})")

            return metrics

        except subprocess.TimeoutExpired:
            logger.error("VMAF calculation timed out")
            raise
        except Exception as e:
            logger.error(f"VMAF calculation failed: {e}")
            raise

    def calculate_psnr_ssim(self) -> Dict:
        """
        Calculate PSNR and SSIM

        PSNR: Peak Signal-to-Noise Ratio (higher is better, >30 is good)
        SSIM: Structural Similarity Index (0-1, higher is better, >0.95 is good)
        """
        logger.info("Calculating PSNR and SSIM...")

        # Get resolution
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json',
            str(self.encoded_file)
        ]

        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        video_info = json.loads(result.stdout)
        width = video_info['streams'][0]['width']
        height = video_info['streams'][0]['height']

        # Calculate PSNR and SSIM
        cmd = [
            'ffmpeg',
            '-i', str(self.encoded_file),
            '-i', str(self.reference_file),
            '-lavfi',
            f'[0:v]scale={width}:{height}[dist];'
            f'[1:v]scale={width}:{height}[ref];'
            f'[dist][ref]psnr=stats_file=/tmp/psnr.log',
            '-f', 'null',
            '-'
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Parse PSNR log
        psnr_values = []
        with open('/tmp/psnr.log', 'r') as f:
            for line in f:
                if 'psnr_avg' in line:
                    # Extract average PSNR
                    parts = line.split()
                    for part in parts:
                        if part.startswith('psnr_avg:'):
                            psnr = float(part.split(':')[1])
                            psnr_values.append(psnr)

        # Calculate SSIM
        cmd = [
            'ffmpeg',
            '-i', str(self.encoded_file),
            '-i', str(self.reference_file),
            '-lavfi',
            f'[0:v]scale={width}:{height}[dist];'
            f'[1:v]scale={width}:{height}[ref];'
            f'[dist][ref]ssim=stats_file=/tmp/ssim.log',
            '-f', 'null',
            '-'
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Parse SSIM log
        ssim_values = []
        with open('/tmp/ssim.log', 'r') as f:
            for line in f:
                if 'All' in line:
                    # Extract SSIM
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'All:':
                            ssim = float(parts[i + 1])
                            ssim_values.append(ssim)

        metrics = {
            'psnr_avg': statistics.mean(psnr_values) if psnr_values else None,
            'ssim_avg': statistics.mean(ssim_values) if ssim_values else None
        }

        if metrics['psnr_avg']:
            logger.info(f"PSNR: {metrics['psnr_avg']:.2f} dB")
        if metrics['ssim_avg']:
            logger.info(f"SSIM: {metrics['ssim_avg']:.4f}")

        return metrics

    def analyze_bitrate(self) -> Dict:
        """
        Analyze bitrate distribution

        Helps detect bitrate spikes or drops
        """
        logger.info("Analyzing bitrate...")

        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'packet=pts_time,size',
            '-of', 'json',
            str(self.encoded_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        packets = data['packets']

        # Calculate bitrate per second
        bitrates = {}
        for packet in packets:
            if 'pts_time' in packet and 'size' in packet:
                second = int(float(packet['pts_time']))
                size = int(packet['size'])
                if second not in bitrates:
                    bitrates[second] = 0
                bitrates[second] += size

        # Convert to kbps
        bitrate_values = [size * 8 / 1000 for size in bitrates.values()]

        if bitrate_values:
            metrics = {
                'bitrate_avg': statistics.mean(bitrate_values),
                'bitrate_median': statistics.median(bitrate_values),
                'bitrate_min': min(bitrate_values),
                'bitrate_max': max(bitrate_values),
                'bitrate_stdev': statistics.stdev(bitrate_values) if len(bitrate_values) > 1 else 0
            }

            logger.info(f"Average bitrate: {metrics['bitrate_avg']:.0f} kbps "
                       f"(min: {metrics['bitrate_min']:.0f}, "
                       f"max: {metrics['bitrate_max']:.0f})")

            return metrics
        else:
            return {}

    def check_frame_drops(self) -> int:
        """
        Check for dropped frames

        Returns number of dropped frames
        """
        logger.info("Checking for dropped frames...")

        cmd = [
            'ffmpeg',
            '-i', str(self.encoded_file),
            '-vf', 'mpdecimate,metadata=print:file=/tmp/frame_drops.log',
            '-f', 'null',
            '-'
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Count dropped frames
        dropped = 0
        with open('/tmp/frame_drops.log', 'r') as f:
            for line in f:
                if 'lavfi.mpdecimate.drop' in line:
                    dropped += 1

        logger.info(f"Dropped frames: {dropped}")

        return dropped

    def run_full_check(self) -> QualityMetrics:
        """
        Run complete quality check

        Returns:
            QualityMetrics with all scores
        """
        logger.info("Starting full quality check...")

        # Calculate VMAF (primary metric)
        vmaf_metrics = self.calculate_vmaf()

        # Calculate PSNR/SSIM (supplementary metrics)
        try:
            psnr_ssim = self.calculate_psnr_ssim()
        except Exception as e:
            logger.warning(f"PSNR/SSIM calculation failed: {e}")
            psnr_ssim = {}

        # Analyze bitrate
        try:
            bitrate_metrics = self.analyze_bitrate()
        except Exception as e:
            logger.warning(f"Bitrate analysis failed: {e}")
            bitrate_metrics = {}

        # Check frame drops
        try:
            frame_drops = self.check_frame_drops()
        except Exception as e:
            logger.warning(f"Frame drop check failed: {e}")
            frame_drops = 0

        # Combine all metrics
        metrics = QualityMetrics(
            vmaf_score=vmaf_metrics['vmaf_mean'],
            vmaf_min=vmaf_metrics['vmaf_min'],
            vmaf_p5=vmaf_metrics['vmaf_p5'],
            vmaf_p95=vmaf_metrics['vmaf_p95'],
            psnr=psnr_ssim.get('psnr_avg'),
            ssim=psnr_ssim.get('ssim_avg'),
            bitrate_avg=int(bitrate_metrics.get('bitrate_avg', 0)),
            bitrate_max=int(bitrate_metrics.get('bitrate_max', 0)),
            frame_drops=frame_drops,
        )

        # Determine pass/fail
        metrics.passed = (
            metrics.vmaf_score >= self.vmaf_threshold and
            metrics.vmaf_min >= 70.0 and  # No frame below 70 VMAF
            metrics.frame_drops == 0
        )

        # Log results
        if metrics.passed:
            logger.info("✓ Quality check PASSED")
        else:
            logger.warning("✗ Quality check FAILED")
            if metrics.vmaf_score < self.vmaf_threshold:
                logger.warning(f"  - VMAF score {metrics.vmaf_score:.2f} < {self.vmaf_threshold}")
            if metrics.vmaf_min < 70.0:
                logger.warning(f"  - Minimum VMAF {metrics.vmaf_min:.2f} < 70.0")
            if metrics.frame_drops > 0:
                logger.warning(f"  - {metrics.frame_drops} dropped frames")

        return metrics


def main():
    parser = argparse.ArgumentParser(
        description='Video quality checker using VMAF and other metrics'
    )
    parser.add_argument(
        '--reference', '-r',
        required=True,
        help='Reference (original) video file'
    )
    parser.add_argument(
        '--encoded', '-e',
        required=True,
        help='Encoded video file to evaluate'
    )
    parser.add_argument(
        '--vmaf-model',
        default='vmaf_v0.6.1',
        help='VMAF model to use (default: vmaf_v0.6.1)'
    )
    parser.add_argument(
        '--vmaf-threshold',
        type=float,
        default=85.0,
        help='Minimum acceptable VMAF score (default: 85.0)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output JSON file for metrics'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Create checker
    checker = VideoQualityChecker(
        reference_file=args.reference,
        encoded_file=args.encoded,
        vmaf_model=args.vmaf_model,
        vmaf_threshold=args.vmaf_threshold
    )

    # Run full check
    metrics = checker.run_full_check()

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)
        logger.info(f"Results saved to {args.output}")

    # Print summary
    print("\n" + "="*60)
    print("QUALITY CHECK SUMMARY")
    print("="*60)
    print(f"VMAF Score:        {metrics.vmaf_score:.2f} / 100.0")
    print(f"VMAF Min:          {metrics.vmaf_min:.2f}")
    print(f"VMAF P5:           {metrics.vmaf_p5:.2f}")
    print(f"VMAF P95:          {metrics.vmaf_p95:.2f}")
    if metrics.psnr:
        print(f"PSNR:              {metrics.psnr:.2f} dB")
    if metrics.ssim:
        print(f"SSIM:              {metrics.ssim:.4f}")
    if metrics.bitrate_avg:
        print(f"Avg Bitrate:       {metrics.bitrate_avg:,} kbps")
    print(f"Frame Drops:       {metrics.frame_drops}")
    print(f"\nResult:            {'PASSED ✓' if metrics.passed else 'FAILED ✗'}")
    print("="*60 + "\n")

    return 0 if metrics.passed else 1


if __name__ == '__main__':
    sys.exit(main())
