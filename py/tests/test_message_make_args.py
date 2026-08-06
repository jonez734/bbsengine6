# test_message_make_args.py
# Regression test: _make_args must populate the full set of connection
# fields (host/port/user/password/schema) so that downstream getpool()
# calls see a complete args namespace instead of bare database/databasename
# attrs (which previously caused debug logs to show 'MISSING' for host/port).



class TestMakeArgsConnectionFields:
    def test_make_args_sets_all_connection_fields(self, monkeypatch):
        monkeypatch.delenv("BBSENGINE6_DBHOST", raising=False)
        monkeypatch.delenv("BBSENGINE6_DBPORT", raising=False)
        monkeypatch.delenv("BBSENGINE6_DBUSER", raising=False)
        monkeypatch.delenv("BBSENGINE6_DBPASSWORD", raising=False)
        monkeypatch.delenv("BBSENGINE6_DBSCHEMA", raising=False)

        from bbsengine6 import message

        args = message._make_args("zoid6")

        assert args.database == "zoid6"
        assert args.databasename == "zoid6"
        assert args.databasehost == "localhost"
        assert args.databaseport == 5432
        assert args.databaseuser is None
        assert args.databasepassword is None
        assert args.databaseschema == "engine"

    def test_make_args_honors_env_overrides(self, monkeypatch):
        monkeypatch.setenv("BBSENGINE6_DBHOST", "db.example.com")
        monkeypatch.setenv("BBSENGINE6_DBPORT", "6543")
        monkeypatch.setenv("BBSENGINE6_DBUSER", "alice")
        monkeypatch.setenv("BBSENGINE6_DBPASSWORD", "s3cret")
        monkeypatch.setenv("BBSENGINE6_DBSCHEMA", "public")

        from bbsengine6 import message

        args = message._make_args("zoid6")

        assert args.databasehost == "db.example.com"
        assert args.databaseport == 6543
        assert args.databaseuser == "alice"
        assert args.databasepassword == "s3cret"
        assert args.databaseschema == "public"
