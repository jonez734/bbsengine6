# demo_listbox_masterdetail Specification

## Overview

`demo_listbox_masterdetail` demonstrates a master-detail view using two listboxes: one for selecting a US President (master) and another for selecting a detail category (details). It extends `demo_listbox_cursor` functionality.

## Architecture

- **President Listbox**: `ListboxCursor` displaying presidents from `article2.president` (lazy-loaded from cursor)
- **Category Listbox**: Static `Listbox` showing available detail categories for selected president
- **Detail Display**: Shows data from the selected category table

## Detail Categories

| Category | Table | Description |
|----------|-------|-------------|
| person | article2.person | Personal details (name, birth, death) |
| edu | article2.edu | Education history |
| elector | article2.elector | Electoral information |
| attraction_* | article2.attraction_* | Dynamic attraction tables |

Attraction tables are discovered dynamically from the database and include: `attractions`, `attraction_hour`, `attraction_place`, `attraction_social_media`, `attraction_join`.

## Usage

```bash
python demo_listbox_masterdetail.py --databasename yummyjam --databasehost localhost
```

## Command-line Arguments

| Argument | Description |
|----------|-------------|
| `--databasename` | Database name (default: yummyjam) |
| `--databasehost` | Database host (default: 127.0.0.1) |
| `--databaseport` | Database port (default: 5432) |
| `--databaseuser` | Database user |
| `--databasepassword` | Database password |
| `--debug` | Enable debug output |
| `--verbose` | Enable verbose output |

## User Flow

1. President listbox is displayed with scrollable list of US Presidents
2. User selects a president (Enter key)
3. System queries which tables have data for selected president
4. Category listbox shows available categories for that president
5. User selects a category
6. Detail data from that category table is displayed
7. User presses any key to return to category selection

## Helper Functions

### Height NamedTuple

```python
class Height(NamedTuple):
  cm: float
  feet: float
  inches: float
```

### cmtofeet(cm: float) -> Height

Converts centimeters to feet/inches format.

## Constants

| Constant | Description |
|----------|-------------|
| `NAME` | User's name for height comparison (default: "jam") |
| `HEIGHT` | User's height in cm for comparison (default: 193.04) |
| `CATEGORY_TABLES` | List of detail table names |

## Database Requirements

- Database: Must exist (checked via `database.exists()`)
- Schema: `article2` must exist (checked via `database.schemaexists()`)
- Tables: `article2.president`, `article2.person`, `article2.edu`, `article2.elector`, `article2.attractions`, and tables matching `attraction_*`

## Key Classes

### PresidentListboxItem

Custom `ListboxItem` subclass for displaying presidents in the master list.

### CategoryListboxItem

Custom `ListboxItem` subclass for displaying available categories in the detail list.

## Error Handling

- Checks database existence before connecting
- Checks schema existence before querying
- Catches `psycopg.DatabaseError` exceptions
- Returns appropriate error codes on failure
