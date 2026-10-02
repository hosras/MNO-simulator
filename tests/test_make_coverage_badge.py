"""Unit tests for make_coverage_badge module."""

import pytest

import make_coverage_badge as mcb


# ==================================================================
# coverage_color
# ==================================================================
class TestCoverageColor:
    def test_90_or_above_is_green(self):
        assert mcb.coverage_color(95) == "#4c1"

    def test_boundary_90(self):
        assert mcb.coverage_color(90) == "#4c1"

    def test_80_to_89_is_yellow_green(self):
        assert mcb.coverage_color(85) == "#97ca00"

    def test_boundary_80(self):
        assert mcb.coverage_color(80) == "#97ca00"

    def test_70_to_79_is_yellow(self):
        assert mcb.coverage_color(75) == "#dfb317"

    def test_boundary_70(self):
        assert mcb.coverage_color(70) == "#dfb317"

    def test_60_to_69_is_orange(self):
        assert mcb.coverage_color(65) == "#fe7d37"

    def test_boundary_60(self):
        assert mcb.coverage_color(60) == "#fe7d37"

    def test_50_to_59_is_red_orange(self):
        assert mcb.coverage_color(55) == "#e05d44"

    def test_boundary_50(self):
        assert mcb.coverage_color(50) == "#e05d44"

    def test_below_50_is_red(self):
        assert mcb.coverage_color(30) == "#cb2431"

    def test_zero(self):
        assert mcb.coverage_color(0) == "#cb2431"


# ==================================================================
# render_svg
# ==================================================================
class TestRenderSvg:
    def test_starts_with_svg(self):
        assert mcb.render_svg(80).startswith("<svg")

    def test_contains_percentage(self):
        assert "80%" in mcb.render_svg(80)

    def test_contains_label(self):
        assert "coverage" in mcb.render_svg(80)

    def test_uses_correct_color(self):
        assert "#4c1" in mcb.render_svg(95)

    def test_zero_pct(self):
        assert "0%" in mcb.render_svg(0)

    def test_decimal_pct_is_rounded(self):
        assert "74%" in mcb.render_svg(74.5)

    def test_contains_closing_tag(self):
        assert "</svg>" in mcb.render_svg(50)


# ==================================================================
# main
# ==================================================================
class TestMain:
    def test_no_coverage_file_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mcb, "ROOT", tmp_path)
        with pytest.raises(SystemExit):
            mcb.main()

    def test_full_run(self, tmp_path, monkeypatch, capsys):
        # Create a fake .coverage marker so the check passes
        (tmp_path / ".coverage").touch()
        out_path = tmp_path / "out.svg"

        monkeypatch.setattr(mcb, "ROOT", tmp_path)
        monkeypatch.setattr(mcb, "OUT", out_path)

        class FakeCov:
            def load(self):
                pass

            def report(self, **kwargs):
                return 74.5

        class FakeCoverageModule:
            Coverage = FakeCov

        monkeypatch.setattr(mcb, "coverage", FakeCoverageModule)

        mcb.main()

        assert out_path.exists()
        assert "74%" in out_path.read_text(encoding="utf-8")

        captured = capsys.readouterr()
        assert "[OK]" in captured.out
