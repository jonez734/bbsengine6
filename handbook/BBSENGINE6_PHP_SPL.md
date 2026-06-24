# BBSEngine6 SPL Features

## Current State
**bbsengine6 PHP uses zero SPL features** - it uses standard PHP functions like `scandir()`, `is_dir()`, `file_get_contents()`, etc.

## SPL Features That Could Be Used in bbsengine6

### High Value for BBS Applications:

| Category | SPL Class | BBS Use Case |
|----------|-----------|--------------|
| **File Handling** | `SplFileInfo` / `SplFileObject` | File uploads, log reading, config files, message attachments |
| **Directory Iteration** | `DirectoryIterator` / `RecursiveDirectoryIterator` | Forum file scans, file browser, batch operations |
| **Data Structures** | `SplStack` | Undo/redo in message editors, command history |
| **Data Structures** | `SplQueue` | Message queue processing, batch email sending |
| **Data Structures** | `SplPriorityQueue` | Message priority sorting, task scheduling |
| **Data Structures** | `SplFixedArray` | Memory-efficient arrays for large message boards |
| **Object Storage** | `SplObjectStorage` | Session data, caching objects, user tracking |
| **Iterators** | `ArrayIterator` | Paginating message lists, search results |
| **Autoloading** | `spl_autoload_register` | Class autoloading (replaces custom autoloaders) |

### Most Impactful Replacements:
1. **`DirectoryIterator`** → Replace `scandir()` loops for directory traversal
2. **`SplFileObject`** → Replace `file()` / `file_get_contents()` for large files
3. **`RecursiveDirectoryIterator`** → File browser functionality
