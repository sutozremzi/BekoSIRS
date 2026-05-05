"""
Unit tests for products/liveness_detection.py

Tests frame subtraction, entropy calculation, pair diff analysis,
LivenessResult logic, and multiframe processing pipeline.
"""

import numpy as np
import cv2
import pytest
from unittest.mock import patch, MagicMock

from products.liveness_detection import (
    _preprocess,
    _entropy,
    _pair_diff,
    PairDiffResult,
    LivenessResult,
    compute_liveness_score,
    decode_image_bytes,
    run_liveness_check_multiframe,
    LIVENESS_SCORE_THRESHOLD,
    ENTROPY_THRESHOLD,
    ACTIVE_PIXEL_RATIO_MIN,
)


# ---------------------------------------------------------------------------
# Helpers — Create synthetic test frames
# ---------------------------------------------------------------------------

def _make_bgr_frame(width=320, height=240, color=(128, 128, 128)):
    """Create a solid-colour BGR frame."""
    frame = np.full((height, width, 3), color, dtype=np.uint8)
    return frame


def _make_frame_with_shift(base_frame, shift_x=20, shift_y=0):
    """Shift a frame horizontally/vertically to simulate head movement."""
    M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
    shifted = cv2.warpAffine(base_frame, M, (base_frame.shape[1], base_frame.shape[0]))
    return shifted


def _make_noisy_frame(width=320, height=240, seed=42):
    """Create a random-noise BGR frame (simulates real camera input)."""
    rng = np.random.RandomState(seed)
    return rng.randint(0, 256, (height, width, 3), dtype=np.uint8)


def _encode_frame_to_jpeg(frame_bgr):
    """Encode a BGR frame as JPEG bytes (for multiframe tests)."""
    success, buf = cv2.imencode('.jpg', frame_bgr)
    assert success, "Failed to encode JPEG"
    return buf.tobytes()


# ===========================================================================
# 1. _preprocess tests
# ===========================================================================

class TestPreprocess:
    def test_output_is_grayscale(self):
        """_preprocess must return a single-channel (grayscale) image."""
        bgr = _make_bgr_frame()
        result = _preprocess(bgr)
        assert len(result.shape) == 2, "Expected 2D grayscale array"

    def test_output_size_matches_default(self):
        """Default resize target is (320, 240)."""
        bgr = _make_bgr_frame(640, 480)
        result = _preprocess(bgr)
        assert result.shape == (240, 320)

    def test_custom_size(self):
        """Custom size parameter should be respected."""
        bgr = _make_bgr_frame(640, 480)
        result = _preprocess(bgr, size=(160, 120))
        assert result.shape == (120, 160)


# ===========================================================================
# 2. _entropy tests
# ===========================================================================

class TestEntropy:
    def test_uniform_histogram_max_entropy(self):
        """A perfectly uniform histogram should have high entropy."""
        hist = np.ones(256, dtype=np.float64)
        e = _entropy(hist)
        assert abs(e - 8.0) < 0.01, f"Expected 8.0 bits, got {e}"

    def test_single_bin_zero_entropy(self):
        """A histogram with all values in one bin has entropy 0."""
        hist = np.zeros(256, dtype=np.float64)
        hist[100] = 1000
        e = _entropy(hist)
        assert e == 0.0

    def test_empty_histogram(self):
        """All-zero histogram should return 0."""
        hist = np.zeros(256, dtype=np.float64)
        e = _entropy(hist)
        assert e == 0.0

    def test_two_equal_bins(self):
        """Two equal bins → entropy = 1.0 bit."""
        hist = np.zeros(256, dtype=np.float64)
        hist[0] = 50
        hist[255] = 50
        e = _entropy(hist)
        assert abs(e - 1.0) < 0.01


# ===========================================================================
# 3. _pair_diff tests
# ===========================================================================

class TestPairDiff:
    def test_identical_frames_zero_diff(self):
        """Two identical frames should produce near-zero diff metrics."""
        frame = _preprocess(_make_bgr_frame())
        result = _pair_diff(frame, frame)
        assert isinstance(result, PairDiffResult)
        assert result.mean_diff == 0.0
        assert result.active_ratio == 0.0

    def test_different_frames_nonzero_diff(self):
        """Two visually different frames should have positive diff values."""
        a = _preprocess(_make_noisy_frame(seed=1))
        b = _preprocess(_make_noisy_frame(seed=2))
        result = _pair_diff(a, b)
        assert result.mean_diff > 0
        assert result.active_ratio > 0
        assert result.entropy > 0

    def test_diff_map_shape(self):
        """diff_map should have the same shape as input frames."""
        a = _preprocess(_make_bgr_frame())
        b = _preprocess(_make_noisy_frame())
        result = _pair_diff(a, b)
        assert result.diff_map.shape == a.shape

    def test_shifted_frame_produces_motion(self):
        """Horizontally shifted frame should show motion in diff."""
        base = _make_noisy_frame(seed=10)
        shifted = _make_frame_with_shift(base, shift_x=30)
        a = _preprocess(base)
        b = _preprocess(shifted)
        result = _pair_diff(a, b)
        assert result.mean_diff > 5.0, "Shifted frame should have noticeable diff"


# ===========================================================================
# 4. compute_liveness_score tests
# ===========================================================================

class TestComputeLivenessScore:
    def test_identical_frames_fail_liveness(self):
        """Three identical frames (static image attack) should fail liveness."""
        frame = _make_bgr_frame()
        result = compute_liveness_score(frame, frame, frame, verify_pose=False)
        assert isinstance(result, LivenessResult)
        assert result.is_live is False
        assert result.score < 0.5

    def test_different_frames_pass_liveness(self):
        """Three visibly different noisy frames should pass liveness."""
        f1 = _make_noisy_frame(seed=1)
        f2 = _make_noisy_frame(seed=2)
        f3 = _make_noisy_frame(seed=3)
        result = compute_liveness_score(f1, f2, f3, verify_pose=False)
        assert result.is_live is True
        assert result.score > 0.5

    def test_liveness_result_has_details(self):
        """LivenessResult.details should contain diff metrics."""
        f1 = _make_noisy_frame(seed=10)
        f2 = _make_noisy_frame(seed=20)
        f3 = _make_noisy_frame(seed=30)
        result = compute_liveness_score(f1, f2, f3, verify_pose=False)
        assert 'pairs' in result.details
        assert 'combined' in result.details

    def test_custom_threshold(self):
        """Setting a very high threshold should cause failure."""
        f1 = _make_noisy_frame(seed=1)
        f2 = _make_noisy_frame(seed=2)
        f3 = _make_noisy_frame(seed=3)
        result = compute_liveness_score(
            f1, f2, f3, score_threshold=999.0, verify_pose=False
        )
        assert result.is_live is False


# ===========================================================================
# 5. decode_image_bytes tests
# ===========================================================================

class TestDecodeImageBytes:
    def test_valid_jpeg_decoded(self):
        """Valid JPEG bytes should decode to a BGR numpy array."""
        frame = _make_bgr_frame()
        jpg_bytes = _encode_frame_to_jpeg(frame)
        decoded = decode_image_bytes(jpg_bytes)
        assert decoded is not None
        assert len(decoded.shape) == 3
        assert decoded.shape[2] == 3  # BGR

    def test_invalid_bytes_returns_none(self):
        """Invalid/corrupt bytes should return None, not crash."""
        result = decode_image_bytes(b"this_is_not_an_image")
        assert result is None

    def test_empty_bytes_returns_none(self):
        """Empty bytes should return None."""
        result = decode_image_bytes(b"")
        assert result is None


# ===========================================================================
# 6. run_liveness_check_multiframe tests
# ===========================================================================

class TestRunLivenessCheckMultiframe:
    def test_insufficient_frames_fails(self):
        """Fewer than 3 frames should fail with appropriate message."""
        f1 = _encode_frame_to_jpeg(_make_bgr_frame())
        result = run_liveness_check_multiframe([f1])
        assert result.is_live is False
        assert 'yetersiz' in result.reason.lower() or 'az' in result.reason.lower()

    def test_identical_frames_fail(self):
        """Multiple identical JPEG frames should fail liveness (static attack)."""
        frame = _make_bgr_frame(color=(100, 150, 200))
        jpg = _encode_frame_to_jpeg(frame)
        frames = [jpg] * 5
        result = run_liveness_check_multiframe(frames)
        assert result.is_live is False

    def test_different_frames_pass(self):
        """Multiple noisy frames simulating real movement should pass."""
        frames = []
        for i in range(6):
            f = _make_noisy_frame(seed=i * 10 + 1)
            frames.append(_encode_frame_to_jpeg(f))
        result = run_liveness_check_multiframe(frames)
        assert result.is_live is True
        assert result.score > 0

    def test_corrupt_frame_handled_gracefully(self):
        """If a frame is corrupt, function should not crash."""
        good = _encode_frame_to_jpeg(_make_noisy_frame(seed=1))
        corrupt = b"NOT_A_JPEG"
        frames = [good, corrupt, good, good]
        # Should not raise — either fails gracefully or skips bad frame
        result = run_liveness_check_multiframe(frames)
        assert isinstance(result, LivenessResult)

    def test_returns_liveness_result(self):
        """Return type must be LivenessResult."""
        frames = [_encode_frame_to_jpeg(_make_noisy_frame(seed=s)) for s in range(4)]
        result = run_liveness_check_multiframe(frames)
        assert isinstance(result, LivenessResult)
        assert isinstance(result.is_live, bool)
        assert isinstance(result.score, float)
        assert isinstance(result.reason, str)


# ===========================================================================
# 7. Threshold constants sanity checks
# ===========================================================================

class TestThresholdConstants:
    def test_liveness_threshold_positive(self):
        assert LIVENESS_SCORE_THRESHOLD > 0

    def test_entropy_threshold_positive(self):
        assert ENTROPY_THRESHOLD > 0

    def test_active_pixel_ratio_in_range(self):
        assert 0 < ACTIVE_PIXEL_RATIO_MIN < 1
