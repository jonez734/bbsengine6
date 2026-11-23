"""Golden draw_frame output from the committed HEAD (43a26d2+), captured before the Frame change.

draw_frame(title, width) with no height, and with one moniker child, must still emit these exact bytes.

The one-child bytes were captured from a fresh output stream (no frame drawn before it in the same stream), the same
way test_frame_compatibility runs them. A stream that already holds a frame starts with a leading charset reset.
"""

BYTES_NO_CHILDREN = '\x1b[38;2;0;163;68m\x1b(0l\x1b(B\x1b(0q\x1b(B\x1b(0u\x1b(B \x1b[49m\x1b[38;2;198;198;198mzoid6 auth\x1b[38;2;0;163;68m \x1b(0t\x1b(B\x1b(0qqqqqqqqqq\x1b(B\x1b(0k\n\x1b(B\x1b(0x\x1b(B                         \x1b(0x\n\x1b(B\x1b(0m\x1b(B\x1b(0qqqqqqqqqqqqqqqqqqqqqqqqq\x1b(B\x1b(0j'
BYTES_ONE_CHILD = '\x1b[38;2;0;163;68m\x1b(0l\x1b(B\x1b(0q\x1b(B\x1b(0u\x1b(B \x1b[49m\x1b[38;2;198;198;198mzoid6 auth\x1b[38;2;0;163;68m \x1b(0t\x1b(B\x1b(0qqqqqqqqqq\x1b(B\x1b(0k\n\x1b(B\x1b(0x\x1b(B                         \x1b(0x\n\x1b(B\x1b(0m\x1b(B\x1b(0qqqqqqqqqqqqqqqqqqqqqqqqq\x1b(B\x1b(0j\n\x1b(B\x1b[38;2;0;163;68m\x1b(0l\x1b(B\x1b(0q\x1b(B\x1b(0u\x1b(B \x1b[49m\x1b[38;2;198;198;198mmoniker\x1b[38;2;0;163;68m \x1b(0t\x1b(B\x1b(0qqqqqqqqqqqqq\x1b(B\x1b(0k\n\x1b(B\x1b(0x\x1b(B                         \x1b(0x\n\x1b(B\x1b(0m\x1b(B\x1b(0qqqqqqqqqqqqqqqqqqqqqqqqq\x1b(B\x1b(0j'
GEOM_NO_CHILDREN = '0 2 25 0'
GEOM_ONE_CHILD = '0 6 25 [(4, 6, 3)]'
