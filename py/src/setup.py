#!/usr/bin/env python3

from setuptools import setup

import time

v = time.strftime("%Y%m%d%H%M")
projectname = "bbsengine6"

setup(
  name=projectname,
  version=v,
  author="zoidtechnologies.com",
  author_email="%s@projects.zoidtechnologies.com" % (projectname),
  license="GPLv3",
#  py_modules=["bbsengine6"],
#  scripts=["con"],
  requires=["ttyio6", "getdate"],
  url="https://bbsengine.org/",
  classifiers=[
    "Programming Language :: Python :: 3.11",
    "Environment :: Console",
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Operating System :: POSIX",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Terminals",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
  ],
  provides=[projectname],
  packages=["bbsengine6", "con"],
)
