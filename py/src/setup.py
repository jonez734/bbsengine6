#!/usr/bin/env python3

import os
import time
from setuptools import setup

projectname = "bbsengine6"

# If VERSION env var is set, use it; otherwise use timestamp
v = os.environ.get("VERSION")
if v is None:
    v = time.strftime("%Y%m%d%H%M")

setup(
    name=projectname,
    version=v,
    author="zoidtechnologies.com",
    author_email="%s@projects.zoidtechnologies.com" % (projectname),
    license="GPLv2+",
    #  py_modules=["bbsengine6.menu", "bbsengine6.session"],
    #  scripts=["con"],
    requires=[
        "argcomplete",
    ],
    url="https://bbsengine.org/",
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Environment :: Console",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: POSIX",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Terminals",
        "License :: OSI Approved :: GNU General Public License v2+ (GPLv2+)",
        "Topic :: Communications :: BBS",
    ],
    provides=[
        projectname,
    ],
    include_package_data=True,
    packages=["bbsengine6", "bbsengine6.io", "bbsengine6.console"],
    package_data={"bbsengine6": ["sql/*.sql", "sql/Makefile"]},
)
