from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_completion_summary import (
    COMPLETION_COLUMNS,
    build_completion_summary_row,
    count_ready_chains,
    write_outputs,
)


class FrontierExecutionQueueCompletionSummaryBuildRowTest(unittest.TestCase):
    def test_count_ready_chains_counts_execution_chain_ready(self) -> None:
        status_row = {
            "meeteval_chain_status": "execution_chain_ready",
            "speaker_profile_chain_status": "execution_chain_ready",
            "external_staging_chain_status": "pending",
            "llm_critic_chain_status": "pending",
            "demo_excellence_chain_status": "pending",
        }
        ready, total = count_ready_chains(status_row)
        self.assertEqual(ready, 2)
        self.assertEqual(total, 5)

    def test_build_completion_summary_row_marks_queue_complete_when_all_ready(self) -> None:
        status_row = {key: "execution_chain_ready" for key in [
            "meeteval_chain_status",
            "speaker_profile_chain_status",
            "external_staging_chain_status",
            "llm_critic_chain_status",
            "demo_excellence_chain_status",
        ]}
        row = build_completion_summary_row(status_row)
        self.assertEqual(row["ready_chain_count"], "5")
        self.assertEqual(row["pending_chain_count"], "0")
        self.assertEqual(row["queue_status"], "queue_complete")


if __name__ == "__main__":
    unittest.main()
