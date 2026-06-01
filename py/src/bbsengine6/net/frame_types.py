# bbsengine6/net/frame_types.py
# Frame type abstractions: Frame (bytes) and NumpyFrame (numpy array)
# Copied from asimov.net (bbsengine6 is not permitted to import from asimov)

from typing import Union, Optional, Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


class Frame:
    """Base frame type: raw bytes."""

    def __init__(self, data: bytes, width: int, height: int, frame_id: int = 0):
        self.data = data
        self.width = width
        self.height = height
        self.frame_id = frame_id
        self._validate()

    def _validate(self):
        expected_size = self.width * self.height * 3
        if len(self.data) != expected_size:
            raise ValueError(
                f"Frame data size mismatch: expected {expected_size} bytes, got {len(self.data)}"
            )

    def to_bytes(self) -> bytes:
        return self.data

    def copy(self) -> "Frame":
        return Frame(self.data, self.width, self.height, self.frame_id)

    @staticmethod
    def from_size(width: int, height: int, fill: int = 0, frame_id: int = 0) -> "Frame":
        data = bytes([fill] * (width * height * 3))
        return Frame(data, width, height, frame_id)

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, other) -> bool:
        if isinstance(other, Frame):
            return self.data == other.data and self.width == other.width and self.height == other.height
        return False


class NumpyFrame:
    """Frame type: numpy array (3D: height x width x 3 channels)."""

    def __init__(self, data: Any, frame_id: int = 0):
        if not HAS_NUMPY:
            raise RuntimeError("numpy not installed")
        if not isinstance(data, np.ndarray):
            raise TypeError("data must be numpy array")
        if data.ndim != 3 or data.shape[2] != 3:
            raise ValueError("data must be shape (height, width, 3)")
        if data.dtype != np.uint8:
            raise ValueError("data must be dtype uint8")

        self.data = data
        self.frame_id = frame_id

    @property
    def height(self) -> int:
        return self.data.shape[0]

    @property
    def width(self) -> int:
        return self.data.shape[1]

    def to_bytes(self) -> bytes:
        return self.data.tobytes()

    def to_frame(self) -> Frame:
        return Frame(self.to_bytes(), self.width, self.height, self.frame_id)

    def copy(self) -> "NumpyFrame":
        return NumpyFrame(self.data.copy(), self.frame_id)

    @staticmethod
    def from_bytes(data: bytes, width: int, height: int, frame_id: int = 0) -> "NumpyFrame":
        if not HAS_NUMPY:
            raise RuntimeError("numpy not installed")
        arr = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3)).copy()
        return NumpyFrame(arr, frame_id)

    @staticmethod
    def from_size(width: int, height: int, fill: int = 0, frame_id: int = 0) -> "NumpyFrame":
        if not HAS_NUMPY:
            raise RuntimeError("numpy not installed")
        data = np.full((height, width, 3), fill, dtype=np.uint8)
        return NumpyFrame(data, frame_id)

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, other) -> bool:
        if isinstance(other, NumpyFrame):
            return np.array_equal(self.data, other.data)
        return False


def frame_from_any(
    data: Union[bytes, Any],
    width: Optional[int] = None,
    height: Optional[int] = None,
    frame_id: int = 0,
) -> Union[Frame, NumpyFrame]:
    """Create appropriate frame type from any data."""
    if HAS_NUMPY and isinstance(data, np.ndarray):
        return NumpyFrame(data, frame_id)
    elif isinstance(data, bytes):
        if width is None or height is None:
            raise ValueError("width and height required for bytes data")
        return Frame(data, width, height, frame_id)
    else:
        raise TypeError("data must be bytes or numpy array")


def frames_equal(
    frame1: Union[Frame, NumpyFrame],
    frame2: Union[Frame, NumpyFrame],
) -> bool:
    """Check if two frames contain equal data (ignores frame_id)."""
    if frame1.width != frame2.width or frame1.height != frame2.height:
        return False

    if HAS_NUMPY and isinstance(frame1, NumpyFrame) and isinstance(frame2, NumpyFrame):
        return np.array_equal(frame1.data, frame2.data)

    return frame1.to_bytes() == frame2.to_bytes()