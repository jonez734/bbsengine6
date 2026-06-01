# tests/test_net/test_frame_types.py
# Tests for Frame and NumpyFrame abstractions

import pytest
from bbsengine6.net import Frame, NumpyFrame, frame_from_any, frames_equal

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class TestFrame:
    """Tests for Frame (bytes) class."""

    def test_create_frame(self):
        """Create frame from bytes."""
        data = bytes(range(256)) * 3
        frame = Frame(data, 256, 1)
        assert frame.width == 256
        assert frame.height == 1
        assert len(frame) == 768

    def test_frame_size_validation(self):
        """Frame validates size matches width x height x 3."""
        data = bytes(10)  # Too small
        with pytest.raises(ValueError):
            Frame(data, 100, 100)

    def test_frame_to_bytes(self):
        """Convert frame to bytes."""
        data = bytes(range(256)) * 3
        frame = Frame(data, 256, 1)
        assert frame.to_bytes() == data

    def test_frame_copy(self):
        """Copy frame."""
        data = bytes(range(256)) * 3
        frame = Frame(data, 256, 1)
        frame_copy = frame.copy()
        assert frame_copy == frame
        assert frame_copy is not frame

    def test_frame_from_size(self):
        """Create frame filled with value."""
        frame = Frame.from_size(100, 100, fill=128)
        assert frame.width == 100
        assert frame.height == 100
        assert len(frame) == 30000
        assert frame.data[0] == 128

    def test_frame_equality(self):
        """Test frame equality."""
        data = bytes(range(256)) * 3
        frame1 = Frame(data, 256, 1)
        frame2 = Frame(data, 256, 1)
        frame3 = Frame(data, 128, 2)
        assert frame1 == frame2
        assert frame1 != frame3


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
class TestNumpyFrame:
    """Tests for NumpyFrame class (requires numpy)."""

    def test_create_numpy_frame(self):
        """Create NumpyFrame from numpy array."""
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        frame = NumpyFrame(arr)
        assert frame.width == 100
        assert frame.height == 100

    def test_numpy_frame_dtype_validation(self):
        """NumpyFrame validates dtype."""
        arr = np.zeros((100, 100, 3), dtype=np.float32)
        with pytest.raises(ValueError):
            NumpyFrame(arr)

    def test_numpy_frame_shape_validation(self):
        """NumpyFrame validates shape."""
        arr = np.zeros((100, 100), dtype=np.uint8)  # Missing channel dimension
        with pytest.raises(ValueError):
            NumpyFrame(arr)

    def test_numpy_frame_to_bytes(self):
        """Convert NumpyFrame to bytes."""
        arr = np.ones((10, 10, 3), dtype=np.uint8)
        frame = NumpyFrame(arr)
        data = frame.to_bytes()
        assert len(data) == 300

    def test_numpy_frame_to_frame(self):
        """Convert NumpyFrame to Frame."""
        arr = np.ones((10, 10, 3), dtype=np.uint8)
        nframe = NumpyFrame(arr)
        frame = nframe.to_frame()
        assert isinstance(frame, Frame)
        assert frame.width == 10
        assert frame.height == 10

    def test_numpy_frame_from_bytes(self):
        """Create NumpyFrame from bytes."""
        data = bytes(range(256)) * 117 + bytes(
            range(48)
        )  # Exactly 30000 bytes for 100x100x3
        frame = NumpyFrame.from_bytes(data, 100, 100)
        assert frame.width == 100
        assert frame.height == 100

    def test_numpy_frame_copy(self):
        """Copy NumpyFrame."""
        arr = np.ones((10, 10, 3), dtype=np.uint8)
        frame = NumpyFrame(arr)
        frame_copy = frame.copy()
        assert frame == frame_copy
        # Verify it's a copy, not same object
        assert np.shares_memory(frame.data, frame_copy.data) is False

    def test_numpy_frame_equality(self):
        """Test NumpyFrame equality."""
        arr1 = np.ones((10, 10, 3), dtype=np.uint8)
        arr2 = np.ones((10, 10, 3), dtype=np.uint8)
        arr3 = np.zeros((10, 10, 3), dtype=np.uint8)

        frame1 = NumpyFrame(arr1)
        frame2 = NumpyFrame(arr2)
        frame3 = NumpyFrame(arr3)

        assert frame1 == frame2
        assert frame1 != frame3


class TestFrameFromAny:
    """Tests for frame_from_any() helper."""

    def test_from_bytes(self):
        """Create frame from bytes."""
        data = bytes(range(256)) * 3
        frame = frame_from_any(data, width=256, height=1)
        assert isinstance(frame, Frame)

    @pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
    def test_from_numpy_array(self):
        """Create frame from numpy array."""
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        frame = frame_from_any(arr)
        assert isinstance(frame, NumpyFrame)

    def test_bytes_requires_dimensions(self):
        """Bytes require width and height."""
        data = bytes(10)
        with pytest.raises(ValueError):
            frame_from_any(data)  # Missing width and height


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")
class TestFramesEqual:
    """Tests for frames_equal() utility."""

    def test_equal_frames(self):
        """Equal frames are detected."""
        arr = np.ones((10, 10, 3), dtype=np.uint8)
        frame1 = NumpyFrame(arr.copy())
        frame2 = NumpyFrame(arr.copy())
        assert frames_equal(frame1, frame2)

    def test_different_frames(self):
        """Different frames are detected."""
        arr1 = np.ones((10, 10, 3), dtype=np.uint8)
        arr2 = np.zeros((10, 10, 3), dtype=np.uint8)
        frame1 = NumpyFrame(arr1)
        frame2 = NumpyFrame(arr2)
        assert not frames_equal(frame1, frame2)

    def test_different_sizes(self):
        """Different sizes detected."""
        frame1 = Frame.from_size(100, 100)
        frame2 = Frame.from_size(200, 200)
        assert not frames_equal(frame1, frame2)
