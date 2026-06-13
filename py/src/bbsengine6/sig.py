"""
sig.py - Sig/Folder management module

This module provides sig (signal/folder) functionality as an alias to the folder module.
This maintains backwards compatibility while unifying the table name to "folder".

Security Considerations:
- Delegates to folder module which has proper path validation
- All path/URI inputs are validated against _SAFE_PATH_PATTERN before SQL queries
"""

from . import folder

# Aliases to folder module functions for backwards compatibility
input = folder.input
get = folder.get
insert = folder.insert
update = folder.update
delete = folder.delete
builduri = folder.builduri
buildpath = folder.buildpath
builddict = folder.builddict
buildrow = folder.buildrow
allexist = folder.allexist
noneexist = folder.noneexist
exists = folder.exists
uriexists = folder.uriexists
getchsigcompleter = folder.getchfoldercompleter


def getchfoldercompleter(word, **kwargs):
    """Alias for getchfoldercompleter."""
    return folder.getchfoldercompleter(word, **kwargs)
