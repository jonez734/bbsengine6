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
| attractions | article2.attraction_place | Attractions places |

## Attractions

When "attractions" is selected, the listbox shows only `attraction_place` entries. When a place is selected, the detail view shows:
- Place details
- Related `attraction_hour` data (or "needinfo" if none)
- Related `attraction_social_media` data

## Features

- Single item: If there's only one record, detail is shown directly without listbox
- Dynamic key column detection via `TABLE_KEY_COLUMNS` dictionary
- All detail views use `{{labelcolor}}` for column names and `{{valuecolor}}` for values
- Detail views skip columns with `None` values by default (shows blank when `--debug` flag is set)
- After viewing details, returns to categories listbox for same president
- Bottom bar shows navigation path: `article2 | {president_name} | {category}`

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
7. Detail view displays columns (skipping None values unless --debug is set)
8. User presses any key to return to categories listbox
9. User can select another category or cancel to return to presidents

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

## Helper Functions

### compose_person_name(person: dict) -> str

Composes a display name from available name parts in a person record. Tries combinations in order of preference:
1. `name_common` + `name_sur` (e.g., "Bill Clinton")
2. `name_given` + `name_sur` (e.g., "William Clinton")
3. `name_sur` only
4. `name_common` only
5. `name_given` only

If no name parts are available, logs a warning and returns `"[NEEDINFO]"`.

### setbottombar(args, left: str) -> None

Sets the bottom bar with the given left side text. The right side shows `[debug]` when `args.debug` is True, otherwise blank.

## Bottom Bar

The bottom bar displays navigation context:
- Initial: `article2`
- After selecting president: `article2 | {president_name}`
- In category selection: `article2 | {president_name} | select category`
- After selecting category: `article2 | {president_name} | {category}`
- Right side: `[debug]` when `--debug` flag is set, otherwise blank

## Echovars

The demo uses the following echovars for listbox styling:

| Echovar | Value | Description |
|---------|-------|-------------|
| `listbox.boxcolor` | `{darkgreen}` | Color for box drawing characters |
| `listbox.titlecolor` | `{inverse}` | Color for title text |
| `listbox.item.normal` | `{white}` | Normal item color |
| `listbox.item.highlighted` | `{listbox.item.normal}{inverse}` | Highlighted item color |
| `listbox.item.disabled` | `{darkgray}` | Disabled item color |
| `listbox.bgcolor` | `""` | Box background (empty) |

## Error Handling

- Checks database existence before connecting
- Checks schema existence before querying
- Catches `psycopg.DatabaseError` exceptions
- Returns appropriate error codes on failure
