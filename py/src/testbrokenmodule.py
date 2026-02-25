import argparse

from bbsengine6 import module

parser = argparse.ArgumentParser("testbrokenmodule")
parser.add_argument("--verbose", action="store_true", dest="verbose")
parser.add_argument("--debug", action="store_true", dest="debug")
args = parser.parse_args()

module.check(args, "brokenmodule")
