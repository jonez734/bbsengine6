[ ] logout hook -- some code in murdermotel gets run when the user logs out (including eof) (@since 20221015)
[x] port to PDO from PEAR::MDB2 @since 20230402
[x] php8
[ ] io.echo(): unknown tokens (anything in curly braces) are silently dropped. make a way to display them unchanged (@since 20240107)
[ ] SETBOTTOMBAR packet type (12) - server-to-client UI update for bottom bar (e.g., casino module can update client status bar) (@since 20250621)

## Python Issues

- [x] Fix psycopg-pool 3.3.0 incompatibility: The async database layer uses `pool.connection()` which in psycopg-pool 3.3.0 returns an AsyncGeneratorContextManager instead of an awaitable. This breaks `async_connect()`, `get_async_pool()`, and `async_query()` in `database.py`. The error is "object _AsyncGeneratorContextManager can't be used in 'await' expression". **Fix**: Updated the async pool code to work with psycopg-pool 3.3.0+ API - handles both 3.1.x (awaitable) and 3.3.0+ (async context manager) automatically.
