# -*- coding: utf-8 -*-
"""Unit tests for radar.services.pdf — pure builder, no Streamlit."""
import pandas as pd
import pytest

import radar.services.pdf as pdf_module
from radar.services.pdf import build_pdf, HAS_PDF


class TestHasPdfFlag:
    def test_flag_is_bool(self):
        assert isinstance(HAS_PDF, bool)


@pytest.mark.skipif(not HAS_PDF, reason="reportlab not installed")
class TestBuildPdf:
    def test_returns_bytes_for_simple_input(self):
        sections = [{"heading": "Test", "text": "Hello world"}]
        out = build_pdf("Test Report", sections)
        assert isinstance(out, bytes)
        assert len(out) > 100

    def test_pdf_starts_with_magic_header(self):
        sections = [{"heading": "X", "text": "Y"}]
        out = build_pdf("Report", sections)
        assert out is not None
        assert out[:5] == b"%PDF-"

    def test_empty_sections(self):
        out = build_pdf("Empty", [])
        assert out is not None
        assert out[:5] == b"%PDF-"

    def test_section_with_table(self):
        df = pd.DataFrame({
            "col_a": [1, 2, 3],
            "col_b": ["x", "y", "z"],
        })
        sections = [
            {"heading": "Metrics", "text": "See table below"},
            {"heading": "Data", "table": df},
        ]
        out = build_pdf("With Table", sections)
        assert out is not None
        assert out[:5] == b"%PDF-"

    def test_many_sections(self):
        sections = [
            {"heading": f"Section {i}", "text": "Lorem ipsum " * 10}
            for i in range(20)
        ]
        out = build_pdf("Long Report", sections)
        assert out is not None
        assert out[:5] == b"%PDF-"


class TestNoReportlabPath:
    def test_returns_none_when_reportlab_absent(self, monkeypatch):
        monkeypatch.setattr(pdf_module, "HAS_PDF", False)
        out = pdf_module.build_pdf("Title", [{"text": "x"}])
        assert out is None