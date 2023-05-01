#!/usr/bin/env python3

from setuptools import setup

import time

v = time.strftime("%Y%m%d%H%M")
projectname = "bbsengine5"

setup(
  name=projectname,
  version=v,
  author="zoidtechnologies.com",
  author_email="%s@projects.zoidtechnologies.com" % (projectname),
  license="GPLv3",
  py_modules=["bbsengine5", "engine"],
  scripts=["engine"],
  requires=["ttyio5", "getdate"],
  url="http://bbsengine.org/",
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
)
