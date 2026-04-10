import argparse
from bbsengine6 import io
import bbsengine6.io.terminal as terminal

parser = argparse.ArgumentParser()
parser.add_argument("--terminal-width", type=int, default=None, help="Override terminal width")
args = parser.parse_args()

if args.terminal_width:
    terminal.columns = lambda: args.terminal_width
    terminal.width = lambda: args.terminal_width

#io.echo("{reset}")

buf = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis mi nibh, feugiat a finibus in, sodales eget lacus. Fusce auctor nisi vitae mollis aliquam. In fringilla felis et nibh volutpat aliquam. In blandit orci in ipsum placerat facilisis quis eu ante. Curabitur tempus ante non nulla fringilla viverra. Aliquam vel feugiat sapien. Duis in varius lorem. Proin mollis vehicula ornare. Donec venenatis, ex ac bibendum ornare, libero nibh efficitur quam, a congue lectus dolor a urna. Praesent porttitor dui sit amet augue ullamcorper, in tempor est vulputate.

Donec et sem leo. Cras ornare semper sem, at fermentum ligula mattis eget. Pellentesque est enim, lobortis sit amet arcu eu, aliquet commodo orci. Maecenas dignissim id massa nec tincidunt. Mauris rutrum justo non lacus iaculis placerat nec at risus. Sed fermentum velit eros, et pharetra eros tempus id. In nec lacus malesuada, pretium ex ac, porta erat. Vestibulum velit est, pellentesque sed ullamcorper nec, dignissim vitae est.
"""

io.echo("*indent set to ten:*{indent:10}{f6}" + buf)
