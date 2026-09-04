import unittest

from env_lint.__main__ import lint_env, lint_file, compare_with_example


class SyntaxTests(unittest.TestCase):
    def test_valid_file_passes(self):
        r = lint_env("A=1\nB=hello world\n# comment\n\nC=\"quoted value\"\n")
        self.assertEqual(r.errors, 0)
        self.assertEqual(r.warnings, 0)
        self.assertEqual(sorted(r.vars_seen), ["A", "B", "C"])

    def test_missing_equals_is_error(self):
        r = lint_env("JUST_A_WORD\n")
        self.assertEqual(r.errors, 1)
        self.assertEqual(r.issues[0].rule, "syntax")

    def test_invalid_key_chars(self):
        r = lint_env("MY-KEY=1\n1BAD=2\n")
        self.assertEqual(r.errors, 2)
        rules = {i.rule for i in r.issues}
        self.assertIn("key-format", rules)

    def test_export_prefix_allowed(self):
        r = lint_env("export DATABASE_URL=postgres://x\n")
        self.assertEqual(r.errors, 0)
        self.assertIn("DATABASE_URL", r.vars_seen)

    def test_duplicate_key_is_error_with_line_number(self):
        r = lint_env("PORT=3000\nX=1\nPORT=8080\n")
        dups = [i for i in r.issues if i.rule == "duplicate-key"]
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0].line, 3)
        self.assertIn("line 1", dups[0].message)

    def test_unterminated_quote_is_error(self):
        r = lint_env('MSG="open quote\n')
        self.assertTrue(any(i.rule == "unterminated-quote" for i in r.issues))


class SecretHygieneTests(unittest.TestCase):
    def test_short_secret_warns(self):
        r = lint_env("API_KEY=abc\n")
        self.assertEqual(r.errors, 0)
        self.assertTrue(any(i.rule == "weak-secret" for i in r.issues))

    def test_unquoted_secret_with_spaces_warns(self):
        r = lint_env("PASSWORD=my secret words\n")
        self.assertTrue(any(i.rule == "unquoted-secret" for i in r.issues))

    def test_normal_var_not_flagged(self):
        r = lint_env("LOG_LEVEL=debug\nDEBUG=true\n")
        self.assertEqual(r.errors, 0)
        self.assertFalse(any("secret" in i.rule for i in r.issues))


class ExampleDiffTests(unittest.TestCase):
    def test_missing_and_extra_vars_reported(self):
        env = "A=1\nEXTRA=2\n"
        example = "A=1\nB=2\n"
        issues = compare_with_example(env, "nonexistent-file")
        self.assertTrue(any(i.rule == "example-missing" for i in issues))

    def test_diff_finds_missing_and_extra(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        ex = os.path.join(d, ".env.example")
        with open(ex, "w") as f:
            f.write("A=1\nB=2\n")
        issues = compare_with_example("A=1\nEXTRA=2\n", ex)
        rules = {(i.rule, i.message.split("'")[1]) for i in issues}
        self.assertIn(("missing-in-env", "B"), rules)
        self.assertIn(("extra-in-env", "EXTRA"), rules)


class FileTests(unittest.TestCase):
    def test_missing_file_error(self):
        r = lint_file("/nonexistent/.env")
        self.assertEqual(r.errors, 1)
        self.assertEqual(r.issues[0].rule, "io")


class CliTests(unittest.TestCase):
    def test_main_exit_codes(self):
        import io, contextlib
        from env_lint.__main__ import main

        import tempfile, os
        d = tempfile.mkdtemp()
        bad = os.path.join(d, "bad.env")
        with open(bad, "w") as f:
            f.write("OOPS NO EQUALS\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([bad])
        self.assertEqual(code, 1)

        good = os.path.join(d, "good.env")
        with open(good, "w") as f:
            f.write("A=1\nB=hello\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([good])
        self.assertEqual(code, 0)

    def test_strict_mode_treats_warnings_as_errors(self):
        import io, contextlib, tempfile, os
        from env_lint.__main__ import main
        d = tempfile.mkdtemp()
        warn = os.path.join(d, "warn.env")
        with open(warn, "w") as f:
            f.write("API_KEY=abc\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([warn])
        self.assertEqual(code, 0)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([warn, "--strict"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

class BooleanValueTests(unittest.TestCase):
    def test_common_boolean_values_not_flagged(self):
        r = lint_env("DEBUG=true\nVERBOSE=false\nCACHE=yes\n")
        self.assertFalse(any(i.rule == "suspicious-value" for i in r.issues))

class JsonOutputTests(unittest.TestCase):
    def test_json_output_shape(self):
        import io, contextlib, json, tempfile, os
        from env_lint.__main__ import main
        d = tempfile.mkdtemp()
        bad = os.path.join(d, "bad.env")
        with open(bad, "w") as f:
            f.write("OOPS\nPORT=1\nPORT=2\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([bad, "--json"])
        self.assertEqual(code, 1)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["errors"], 2)
        self.assertEqual(data["vars"], 2)
        self.assertTrue(any(i["rule"] == "duplicate-key" for i in data["issues"]))

    def test_json_clean_exit(self):
        import io, contextlib, json, tempfile, os
        from env_lint.__main__ import main
        d = tempfile.mkdtemp()
        good = os.path.join(d, "good.env")
        with open(good, "w") as f:
            f.write("A=1\nB=hello\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([good, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue())["issues"], [])
