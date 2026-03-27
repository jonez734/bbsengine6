import argparse

import bbsengine6 as bbsengine

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true", default=True)
args = parser.parse_args()

buf = bbsengine.util.inputfilename(
    "prompt: ",
    "$HOME/projects/",
    verify=bbsengine.util.verifyDirExistsWritable,
    args=args,
)
print(buf)
