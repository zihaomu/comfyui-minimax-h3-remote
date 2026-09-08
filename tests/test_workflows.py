from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / "example_workflows"
EXPECTED_LINKED_INPUTS = {
    "t2v": set(),
    "i2v": {"first_frame"},
    "fl2v": {"first_frame", "last_frame"},
    "r2v": {"ref_images"},
}


class WorkflowTemplateTests(unittest.TestCase):
    def test_four_v1_workflows_are_structurally_consistent(self) -> None:
        paths = sorted(WORKFLOWS.glob("minimax_h3_remote_*.json"))
        modes = sorted(path.stem.removeprefix("minimax_h3_remote_") for path in paths)
        self.assertEqual(modes, sorted(EXPECTED_LINKED_INPUTS))

        for path in paths:
            with self.subTest(path=path.name):
                workflow = json.loads(path.read_text(encoding="utf-8"))
                mode = path.stem.removeprefix("minimax_h3_remote_")
                self.assertEqual(workflow["version"], 1)
                self.assertEqual(workflow["revision"], 0)
                self.assertIn("lastNodeId", workflow["state"])
                self.assertIn("lastLinkId", workflow["state"])

                nodes = workflow["nodes"]
                node_ids = {node["id"] for node in nodes}
                self.assertEqual(len(node_ids), len(nodes))
                remote_nodes = [node for node in nodes if node["type"] == "MiniMaxH3Remote"]
                self.assertEqual(len(remote_nodes), 1)
                remote = remote_nodes[0]
                self.assertEqual(remote["widgets_values"][0:2], ["", ""])
                self.assertEqual(remote["widgets_values"][2], mode)
                self.assertEqual(remote["properties"]["ver"], "0.1.0")

                input_by_name = {item["name"]: item for item in remote["inputs"]}
                linked_names = {name for name, item in input_by_name.items() if item.get("link") is not None}
                self.assertEqual(linked_names, EXPECTED_LINKED_INPUTS[mode])

                link_ids = set()
                for link in workflow["links"]:
                    self.assertNotIn(link["id"], link_ids)
                    link_ids.add(link["id"])
                    self.assertIn(link["origin_id"], node_ids)
                    self.assertIn(link["target_id"], node_ids)
                    self.assertEqual(link["target_id"], remote["id"])
                    target = remote["inputs"][link["target_slot"]]
                    self.assertEqual(target["link"], link["id"])
                    self.assertEqual(link["type"], target["type"])

                serialized = json.dumps(workflow)
                self.assertNotIn("Bearer ", serialized)
                self.assertNotIn("api-key", serialized.lower())


if __name__ == "__main__":
    unittest.main()
