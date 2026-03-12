# article2 demo: given a year...

## Requirements
Given a year, list presidents categorized into 4 mutually exclusive groups:
1. Presidents in office that year
2. Presidents between terms (non-consecutive terms, year falls between)
3. Presidents who left office and are still alive that year
4. People alive that year who will become president after that year

- No person can appear in more than one group

## Implementation

### File
`/home/opencode/data/work/bbsengine6/py/src/demo_article2_givenyear.py`

### Usage
```bash
python demo_article2_givenyear.py --databasename yummyjam --year 2025
```

Arguments:
- `--year`: Year to query (optional, will prompt if not provided)
- `--databasename`: Database name (default: yummyjam)
- `--databasehost`: Database host (default: 127.0.0.1)
- `--debug`: Enable debug output

### Dependencies
- Use `bbsengine6` framework
- Use `io.echo()` instead of `print()`
- Use `io.inputinteger()` for interactive year input

### Database Tables
- `article2.person` - person details (name_given, name_sur, name_common, date_born, date_die)
- `article2.job` - job/term records (person_key, title, date_start, date_end)

### Key Fields
- `date_die = '9999-99-99'` indicates living person
- `job.date_start` and `job.date_end` for presidential terms
- `job.title` contains 'n_us_gov_president%' for presidential terms

### 4 Groups (mutually exclusive)

1. **Presidents in office**: `year >= job.date_start AND (job.date_end IS NULL OR year <= job.date_end)`
2. **Presidents between terms**: Non-consecutive terms, year falls between them (exclude Group 1)
3. **Left office, still alive**: `job.date_end < year AND (date_die = '9999-99-99' OR date_die > year)` (exclude Groups 1,2)
4. **Future presidents**: `date_born <= year < job.date_start AND (date_die = '9999-99-99' OR date_die > year)` (exclude Groups 1,2,3)

### Program Structure

1. **buildargs()**: argparse with database options + --verbose, --debug, --year
2. **init()**: Set io variables
3. **compose_person_name()**: Build display name from name fields
4. **Query functions**:
   - `get_presidents_in_office()`: Presidents serving in given year
   - `get_presidents_between_terms()`: Non-consecutive presidents between terms
   - `get_presidents_left_office_alive()`: Ex-presidents still living
   - `get_future_presidents()`: Future presidents (alive but not yet in office)
5. **main(args)**: 
   - Connect to database (yummyjam)
   - Input year (1789-present) via --year arg or io.inputinteger()
   - Track assigned person_keys to ensure exclusivity
   - Query each group, excluding already-assigned
   - Display with io.echo(), show "none" for empty groups

### Output Format
- Each group header with io.echo()
- Name and term dates per president (date_start - date_end)
- "none" message for empty groups

### Notes
- Does NOT use listbox (as per requirements)
- Uses dynamic SQL placeholders for psycopg3 compatibility
- Escapes `%` as `%%` in LIKE patterns
- Handles duplicate prevention with seen set in display
