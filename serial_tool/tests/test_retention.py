from serial_tool.core.retention import trim_plan


class TestNoTrim:
    def test_under_limit(self):
        plan = trim_plan([100, 100], 1000)
        assert plan.delete_blocks == 0
        assert plan.keep_blocks == 2

    def test_empty(self):
        plan = trim_plan([], 1000)
        assert plan.delete_blocks == 0
        assert plan.keep_blocks == 0

    def test_exactly_at_limit(self):
        plan = trim_plan([500, 500], 1000)
        assert plan.delete_blocks == 0


class TestTrim:
    def test_trims_to_about_seventy_percent(self):
        plan = trim_plan([100] * 30, 1000)
        assert plan.delete_blocks > 0
        kept = 30 - plan.delete_blocks
        remaining = kept * 100
        assert remaining <= 1000
        assert remaining >= 700

    def test_block_aligned(self):
        plan = trim_plan([100] * 30, 1000)
        assert isinstance(plan.delete_blocks, int)
        assert isinstance(plan.keep_blocks, int)

    def test_counts_add_up(self):
        plan = trim_plan([100] * 30, 1000)
        assert plan.delete_blocks + plan.keep_blocks == 30

    def test_single_huge_block_keeps_one(self):
        plan = trim_plan([2000], 100)
        assert plan.keep_blocks == 1
        assert plan.delete_blocks == 0

    def test_keeps_at_least_one_block(self):
        plan = trim_plan([900, 900, 900], 100)
        assert plan.keep_blocks >= 1
        assert plan.delete_blocks + plan.keep_blocks == 3
