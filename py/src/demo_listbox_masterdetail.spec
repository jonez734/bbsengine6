# demo_listbox_masterdetail Specification

## Overview

`demo_listbox_masterdetail` demonstrates a master-detail view using multiple listboxes: one for selecting a US President (master), one for selecting a detail category, and nested listboxes for detail records.

## Architecture

- **President Listbox**: `ListboxCursor` displaying presidents from `article2.president` (lazy-loaded from cursor)
- **Category Listbox**: Static `Listbox` showing available detail categories for selected president
- **Detail Listbox**: For categories with multiple records, displays a listbox to select a record
- **Detail Display**: Shows all columns with `{{labelcolor}}` for column names and `{{valuecolor}}` for values

## Detail Categories

| Category | Table | Description |
|----------|-------|-------------|
| person | article2.person | Personal details (name, birth, death) |
| edu | article2.edu | Education history |
| elector | article2.elector | Electoral information |
| attractions | article2.attraction_* | Attractions including place, hours, social media |

## Attractions

When "attractions" is selected, displays items from:
- `attraction_place` - place details
- `attraction_hour` - hours of operation
- `attraction_social_media` - social media links

## Features

- Single item: If there's only one record, detail is shown directly without listbox
- Dynamic key column detection via `TABLE_KEY_COLUMNS` dictionary
- All detail views use `{{labelcolor}}` for column names and `{{valuecolor}}` for values

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
6. If multiple records exist, detail listbox is shown
7. Detail view displays all columns with labels and values
8. User presses any key to return

## Constants

| Constant | Description |
|----------|-------------|
| `CATEGORY_TABLES` | List of detail table names |
| `TABLE_KEY_COLUMNS` | Dictionary mapping table names to their primary key columns |

## Database Requirements

- Database: Must exist (checked via `database.exists()`)
- Schema: `article2` must exist (checked via `database.schemaexists()`)
- Tables: `article2.president`, `article2.person`, `article2.edu`, `article2.elector`, `article2.attractions`, `article2.attraction_place`, `article2.attraction_hour`, `article2.attraction_social_media`, `article2.attraction_join`

## Key Classes

### PresidentListboxItem

Custom `ListboxItem` subclass for displaying presidents in the master list.

### CategoryListboxItem

Custom `ListboxItem` subclass for displaying available categories in the category list.

## Error Handling

- Checks database existence before connecting
- Checks schema existence before querying
- Catches `psycopg.DatabaseError` exceptions
- Returns appropriate error codes on failure
