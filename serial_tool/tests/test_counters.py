from serial_tool.core.counters import Counter


class TestCounter:
    def test_initial_zero(self):
        c = Counter()
        assert c.received == 0
        assert c.sent == 0

    def test_add_received(self):
        c = Counter()
        c.add_received(3)
        assert c.received == 3

    def test_add_sent(self):
        c = Counter()
        c.add_sent(2)
        assert c.sent == 2

    def test_accumulates(self):
        c = Counter()
        c.add_received(3)
        c.add_received(4)
        assert c.received == 7

    def test_reset(self):
        c = Counter()
        c.add_received(3)
        c.add_sent(2)
        c.reset()
        assert (c.received, c.sent) == (0, 0)

    def test_text_format(self):
        c = Counter()
        c.add_received(3)
        c.add_sent(2)
        text = c.text()
        assert "3" in text and "2" in text
        assert "接收" in text and "发送" in text
