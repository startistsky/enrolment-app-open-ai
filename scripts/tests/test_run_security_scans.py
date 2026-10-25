import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "run_security_scans.py"
SPEC = importlib.util.spec_from_file_location("run_security_scans", SCRIPT)
SCANS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCANS)


class SecurityScanReportTests(unittest.TestCase):
    def test_report_distinguishes_raw_findings_from_failed_gate(self):
        results = {
            "Ruff Security": ("PASS", "All checks passed!"),
            "Detect Secrets": ("PASS", "No secrets found."),
            "Raw Dependency Audit": ("FINDINGS", "chromadb 1.5.9: advisory"),
            "Dependency Audit Gate": ("PASS", "Pre-commit gated dependency audit: PASS"),
        }

        report, overall = SCANS.render_report(results, "2026-10-25T00:00:00+00:00")

        self.assertEqual(overall, "PASS")
        self.assertIn("Overall security gate: **PASS**", report)
        self.assertIn("| Raw Dependency Audit | FINDINGS |", report)
        self.assertIn("chromadb 1.5.9: advisory", report)

    def test_report_fails_when_security_control_fails(self):
        results = {
            "Ruff Security": ("PASS", ""),
            "Detect Secrets": ("FAIL", "Potential secret found."),
            "Raw Dependency Audit": ("PASS", ""),
            "Dependency Audit Gate": ("PASS", ""),
        }

        report, overall = SCANS.render_report(results, "2026-10-25T00:00:00+00:00")

        self.assertEqual(overall, "FAIL")
        self.assertIn("Overall security gate: **FAIL**", report)
