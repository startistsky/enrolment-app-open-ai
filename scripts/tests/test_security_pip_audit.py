"""Verify temporary acceptance cannot hide new/fixable vulnerabilities."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('security_audit', Path(__file__).resolve().parents[1] / 'security_pip_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditGateTests(unittest.TestCase):
    def report(self):
        return {'dependencies': [{'name': 'chromadb', 'version': '1.5.9', 'vulns': [
            {'id': 'PYSEC-2026-311', 'aliases': ['GHSA-f4j7-r4q5-qw2c'], 'fix_versions': []}]}]}

    def test_raw_fails_gate_accepts_documented_findings(self):
        self.assertEqual(audit.audit_result(self.report(), 1, False), 1)
        self.assertEqual(audit.audit_result(self.report(), 1, True), 0)

    def test_every_documented_id(self):
        for identifier in audit.TEMPORARY_UNPATCHED_IGNORES:
            report = self.report()
            report['dependencies'][0]['vulns'][0]['aliases'] = [identifier]
            self.assertEqual(audit.audit_result(report, 1, True), 0)

    def test_new_vulnerability_blocks(self):
        report = self.report()
        report['dependencies'][0]['vulns'].append({'id': 'GHSA-new-finding', 'fix_versions': []})
        self.assertEqual(audit.audit_result(report, 1, True), 1)

    def test_other_package_version_or_available_fix_blocks(self):
        for change in ({'name': 'other-package'}, {'version': '1.6.0'}):
            report = self.report()
            report['dependencies'][0].update(change)
            self.assertEqual(audit.audit_result(report, 1, True), 1)
        report = self.report()
        report['dependencies'][0]['vulns'][0]['fix_versions'] = ['1.6.0']
        self.assertEqual(audit.audit_result(report, 1, True), 1)

    def test_invalid_or_incomplete_audit_blocks(self):
        for report, status in [({}, 1), (self.report(), 2), (self.report(), 0),
                               ({'dependencies': [{'skip_reason': 'Unavailable'}]}, 1)]:
            self.assertEqual(audit.audit_result(report, status, True), 2)

    def test_clean_audit_passes(self):
        self.assertEqual(audit.audit_result({'dependencies': []}, 0, True), 0)

    def test_all_student_dependency_manifests_are_audited(self):
        for student, components in {
            1: ('requirements.txt', 'backend/requirements.txt', 'database/requirements.txt',
                'tests/requirements.txt'),
            2: ('backend/requirements.txt', 'database/requirements.txt', 'tests/requirements.txt'),
            3: ('backend/requirements.txt', 'database/requirements.txt', 'tests/requirements.txt'),
            4: ('backend/requirements.txt', 'database/requirements.txt'),
            5: ('backend/requirements.txt', 'database/requirements.txt', 'tests/requirements.txt'),
        }.items():
            for component in components:
                self.assertIn(f'student-{student}/{component}', audit.REQUIREMENTS)
