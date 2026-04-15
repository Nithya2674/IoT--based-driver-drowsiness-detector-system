"""
Tests for the Drowsiness Detection ML Module
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

from utils import calculate_ear, calculate_mar


class TestEARCalculation:
    """Test Eye Aspect Ratio calculations."""

    def test_ear_open_eye(self):
        """EAR for an open eye should be above threshold."""
        # Simulating an open eye (wide vertical, normal horizontal)
        landmarks = np.array([
            [0, 5],    # p1 (left corner)
            [1, 8],    # p2 (upper-left)
            [3, 8],    # p3 (upper-right)
            [4, 5],    # p4 (right corner)
            [3, 2],    # p5 (lower-right)
            [1, 2],    # p6 (lower-left)
        ], dtype=np.float64)

        ear = calculate_ear(landmarks)
        assert ear > 0.2, f"Open eye EAR should be > 0.2, got {ear}"

    def test_ear_closed_eye(self):
        """EAR for a closed eye should be below threshold."""
        # Simulating a closed eye (minimal vertical distance)
        landmarks = np.array([
            [0, 5],    # p1
            [1, 5.2],  # p2 (barely above center)
            [3, 5.2],  # p3
            [4, 5],    # p4
            [3, 4.8],  # p5 (barely below center)
            [1, 4.8],  # p6
        ], dtype=np.float64)

        ear = calculate_ear(landmarks)
        assert ear < 0.2, f"Closed eye EAR should be < 0.2, got {ear}"

    def test_ear_zero_horizontal(self):
        """EAR should handle zero horizontal distance."""
        landmarks = np.array([
            [5, 5], [5, 8], [5, 8], [5, 5], [5, 2], [5, 2]
        ], dtype=np.float64)

        ear = calculate_ear(landmarks)
        assert ear == 0.0, "EAR should be 0 when horizontal distance is 0"

    def test_ear_symmetry(self):
        """EAR should be the same for symmetric eye shapes."""
        landmarks1 = np.array([
            [0, 5], [1, 8], [3, 8], [4, 5], [3, 2], [1, 2]
        ], dtype=np.float64)

        # Mirror
        landmarks2 = np.array([
            [4, 5], [3, 8], [1, 8], [0, 5], [1, 2], [3, 2]
        ], dtype=np.float64)

        ear1 = calculate_ear(landmarks1)
        ear2 = calculate_ear(landmarks2)
        assert abs(ear1 - ear2) < 0.01, f"Symmetric eyes should have similar EAR: {ear1} vs {ear2}"


class TestMARCalculation:
    """Test Mouth Aspect Ratio calculations."""

    def test_mar_closed_mouth(self):
        """MAR for a closed mouth should be low."""
        landmarks = np.array([
            [0, 5],    # left corner
            [1, 5.5],
            [2, 5.3],
            [3, 5.1],
            [4, 5],    # right corner
            [3, 4.9],
            [2, 4.7],
            [1, 4.5]
        ], dtype=np.float64)

        mar = calculate_mar(landmarks)
        assert mar < 0.5, f"Closed mouth MAR should be < 0.5, got {mar}"

    def test_mar_yawning(self):
        """MAR for yawning should be high."""
        landmarks = np.array([
            [0, 5],    # left corner
            [1, 9],    # wide open top
            [2, 10],
            [3, 9],
            [4, 5],    # right corner
            [3, 1],    # wide open bottom
            [2, 0],
            [1, 1]
        ], dtype=np.float64)

        mar = calculate_mar(landmarks)
        assert mar > 0.7, f"Yawning MAR should be > 0.7, got {mar}"

    def test_mar_zero_horizontal(self):
        """MAR should handle zero horizontal distance."""
        landmarks = np.array([
            [5, 5], [5, 8], [5, 8], [5, 8], [5, 5], [5, 2], [5, 2], [5, 2]
        ], dtype=np.float64)

        mar = calculate_mar(landmarks)
        assert mar == 0.0, "MAR should be 0 when horizontal distance is 0"


class TestEdgeCases:
    """Test edge cases and input validation."""

    def test_ear_with_integers(self):
        """EAR should work with integer coordinates."""
        landmarks = np.array([
            [0, 5], [1, 8], [3, 8], [4, 5], [3, 2], [1, 2]
        ])
        ear = calculate_ear(landmarks)
        assert isinstance(ear, float)

    def test_ear_returns_positive(self):
        """EAR should always return a positive value."""
        for _ in range(10):
            landmarks = np.random.rand(6, 2) * 100
            ear = calculate_ear(landmarks)
            assert ear >= 0, f"EAR should be non-negative, got {ear}"

    def test_mar_returns_positive(self):
        """MAR should always return a positive value."""
        for _ in range(10):
            landmarks = np.random.rand(8, 2) * 100
            mar = calculate_mar(landmarks)
            assert mar >= 0, f"MAR should be non-negative, got {mar}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
