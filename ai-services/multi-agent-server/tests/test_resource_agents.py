"""Regression tests for Student 3 Resource Multi-Agent workflow."""

import unittest
from unittest.mock import patch

from agents import resource_reviewer_agent, resource_worker_agent


RESOURCES = [
    {
        "resource_id": 1,
        "resource_name": "Study Room A",
        "resource_type": "Study Room",
        "capacity": 6,
        "availability_status": "Available",
    },
    {
        "resource_id": 2,
        "resource_name": "Study Room B",
        "resource_type": "Study Room",
        "capacity": 2,
        "availability_status": "Busy",
    },
    {
        "resource_id": 3,
        "resource_name": "Library Printer",
        "resource_type": "Printer",
        "capacity": 1,
        "availability_status": "Available",
    },
    {
        "resource_id": 4,
        "resource_name": "Quiet Study Area",
        "resource_type": "Study Space",
        "capacity": 20,
        "availability_status": "Available",
    },
]


class ResourceAgentTests(unittest.TestCase):

    def test_available_study_room(self):
        result = resource_worker_agent.matching_resources(
            "Find an available study room for 4 students.",
            RESOURCES,
        )
        self.assertEqual(
            {r["resource_id"] for r in result},
            {"1"},
        )

    def test_printer_classification(self):
        result = resource_worker_agent.matching_resources(
            "Find a printer.",
            RESOURCES,
        )
        self.assertEqual(
            {r["resource_id"] for r in result},
            {"3"},
        )

    def test_library_printer_not_library(self):
        result = resource_worker_agent.matching_resources(
            "Find a library.",
            RESOURCES,
        )
        self.assertEqual(result, [])

    def test_grounded_capacity(self):
        fake_response = {
            "answer": "Study Room A has capacity for 50 students.",
            "evidence_used": ["1"],
            "missing_evidence": [],
        }

        with patch.object(
            resource_worker_agent,
            "generate",
            return_value=fake_response,
        ):
            result = resource_worker_agent.run(
                "Find an available study room for 4 students.",
                RESOURCES,
                {},
            )

        self.assertIn("capacity: 6", result["answer"])
        self.assertNotIn("50 students", result["answer"])

    def test_invalid_resource_id(self):
        fake_response = {
            "answer": "Unknown Study Room is available.",
            "evidence_used": ["999"],
            "missing_evidence": [],
        }

        with patch.object(
            resource_worker_agent,
            "generate",
            return_value=fake_response,
        ):
            result = resource_worker_agent.run(
                "Find an available study room for 4 students.",
                RESOURCES,
                {},
            )

        self.assertEqual(result["evidence_used"], ["1"])
        self.assertNotIn("Unknown Study Room", result["answer"])

    def test_reviewer_rejects_invalid_id(self):
        fake_review = {
            "risk": "",
            "unsupported_claims": [],
            "correction": "",
            "recommendation": "",
        }

        with patch.object(
            resource_reviewer_agent,
            "generate",
            return_value=fake_review,
        ):
            result = resource_reviewer_agent.run(
                "Find an available study room for 4 students.",
                RESOURCES,
                {},
                {
                    "answer": "Unknown Study Room",
                    "evidence_used": ["999"],
                },
            )

        self.assertIn("999", result["risk"])
        self.assertIn("Do not accept", result["recommendation"])


    def test_reviewer_false_positive_ids(self):
        resources = [
            {
                "resource_id": 2,
                "resource_name": "Study Room A",
                "resource_type": "Study Room",
                "capacity": 6,
                "availability_status": "Available",
            }
        ]

        worker = {
            "answer": "Study Room A (ID: 2, capacity: 6, status: Available)",
            "evidence_used": ["2"],
            "missing_evidence": [],
        }

        fake_review = {
            "risk": "The worker answer does not specify the resource IDs.",
            "unsupported_claims": [{
                "claim": "The worker answer does not specify the resource IDs.",
                "description": "The worker answer does not provide resource IDs.",
            }],
            "correction": "The worker answer should specify the resource IDs.",
            "recommendation": "The worker answer should provide the resource IDs.",
        }

        with patch.object(
            resource_reviewer_agent, "generate",
            return_value=fake_review,
        ):
            result = resource_reviewer_agent.run(
                "Find an available study room for 4 students.",
                resources, {}, worker,
            )

        self.assertEqual(result["unsupported_claims"], [])
        self.assertNotIn("does not specify", result["risk"].lower())
        self.assertNotIn("should specify", result["correction"].lower())
        self.assertNotIn("should provide", result["recommendation"].lower())

    def test_reviewer_preserves_missing_ids(self):
        resources = [
            {
                "resource_id": 2,
                "resource_name": "Study Room A",
                "resource_type": "Study Room",
                "capacity": 6,
                "availability_status": "Available",
            }
        ]

        worker = {
            "answer": "Study Room A is available for 6 students.",
            "evidence_used": ["2"],
            "missing_evidence": [],
        }

        fake_review = {
            "risk": "The worker answer does not specify the resource IDs.",
            "unsupported_claims": [{
                "claim": "The worker answer does not specify the resource IDs.",
                "description": "Resource ID is missing from the answer.",
            }],
            "correction": "The worker answer should specify the resource IDs.",
            "recommendation": "The worker answer should provide the resource IDs.",
        }

        with patch.object(
            resource_reviewer_agent, "generate",
            return_value=fake_review,
        ):
            result = resource_reviewer_agent.run(
                "Find an available study room for 4 students.",
                resources, {}, worker,
            )

        self.assertTrue(result["unsupported_claims"])
        self.assertIn("does not specify", result["risk"].lower())


if __name__ == "__main__":
    unittest.main()
