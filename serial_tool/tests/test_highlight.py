from serial_tool.core.highlight import Rule, compile_rule, find_matches


def rule(pattern, color="#ff0000", is_regex=False, enabled=True):
    return compile_rule(Rule(pattern=pattern, color=color, is_regex=is_regex, enabled=enabled))


class TestCompileRule:
    def test_invalid_regex_is_tolerated(self):
        r = compile_rule(Rule(pattern="[", color="#ff0000", is_regex=True))
        assert r.regex is None

    def test_valid_regex_compiled(self):
        r = compile_rule(Rule(pattern=r"\d+", color="#ff0000", is_regex=True))
        assert r.regex is not None

    def test_plain_rule_has_no_regex(self):
        r = rule("ERROR")
        assert r.regex is None


class TestFindMatches:
    def test_plain_text_all_occurrences(self):
        matches = find_matches("x ERROR y ERROR", [rule("ERROR")])
        assert len(matches) == 2
        assert matches[0][0:2] == (2, 7)
        assert matches[1][0:2] == (10, 15)

    def test_plain_text_case_sensitive(self):
        assert find_matches("error", [rule("ERROR")]) == []

    def test_regex_matches(self):
        matches = find_matches("a1b22", [rule(r"\d+", is_regex=True)])
        assert len(matches) == 2
        assert matches[0][0:2] == (1, 2)
        assert matches[1][0:2] == (3, 5)

    def test_disabled_rule_ignored(self):
        assert find_matches("ERROR", [rule("ERROR", enabled=False)]) == []

    def test_invalid_regex_does_not_break_others(self):
        matches = find_matches("ERROR 42", [rule("[", is_regex=True), rule(r"\d+", is_regex=True)])
        assert len(matches) == 1

    def test_color_is_returned(self):
        matches = find_matches("ERROR", [rule("ERROR", color="#00ff00")])
        assert matches[0][2] == "#00ff00"

    def test_empty_rules(self):
        assert find_matches("ERROR", []) == []

    def test_empty_text(self):
        assert find_matches("", [rule("ERROR")]) == []

    def test_multiple_rules_both_reported(self):
        matches = find_matches("AB", [rule("A", "#111111"), rule("B", "#222222")])
        assert [m[2] for m in matches] == ["#111111", "#222222"]

    def test_no_infinite_loop_on_empty_pattern(self):
        assert find_matches("abc", [rule("")]) == []
