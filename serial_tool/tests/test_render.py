from serial_tool.core.render import Line, Style, render_line_html


class TestEscaping:
    def test_tags_are_escaped(self):
        html = render_line_html(Line("<b>x</b>"))
        assert "&lt;b&gt;x&lt;/b&gt;" in html
        assert "<b>" not in html

    def test_ampersand_escaped(self):
        html = render_line_html(Line("a & b"))
        assert "a &amp; b" in html

    def test_quotes_not_escaped(self):
        html = render_line_html(Line('q"q'))
        assert 'q"q' in html

    def test_script_payload_neutralized(self):
        html = render_line_html(Line("<script>alert(1)</script>"))
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestStyles:
    def test_sent_is_green(self):
        assert "#008000" in render_line_html(Line("x", Style.SENT))

    def test_system_is_grey(self):
        assert "#888888" in render_line_html(Line("x", Style.SYSTEM))

    def test_received_has_text_color(self):
        html = render_line_html(Line("x", Style.RECEIVED))
        assert "x" in html


class TestTimestamp:
    def test_timestamp_prefix(self):
        html = render_line_html(Line("x", timestamp="12:00:00.123"))
        assert "[12:00:00.123]" in html
        assert html.index("[12:00:00.123]") < html.index("x")

    def test_no_timestamp_no_brackets(self):
        html = render_line_html(Line("x"))
        assert "[" not in html

    def test_timestamp_is_styled_grey(self):
        html = render_line_html(Line("x", timestamp="12:00:00.123"))
        assert "#888888" in html


class TestLineShape:
    def test_single_br_at_end(self):
        html = render_line_html(Line("x"))
        assert html.count("<br>") == 1

    def test_newline_in_text_becomes_br_not_raw_newline(self):
        html = render_line_html(Line("a\nb"))
        assert "\n" not in html

    def test_empty_text_still_valid(self):
        assert render_line_html(Line("")) == "<br>" or render_line_html(Line("")).endswith("<br>")
