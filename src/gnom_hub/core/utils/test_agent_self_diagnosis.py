import unittest
from unittest.mock import patch, MagicMock
import os
import json

from gnom_hub.agents.actions.action_handlers import process_actions
from gnom_hub.chat.brainstorm.brainstorm_helpers import ask_llm

class TestAgentSelfDiagnosis(unittest.TestCase):
    def test_gatekeeper_permission_denial(self):
        # 1. Test that without "write" permission, process_actions replaces [WRITE] with a Gatekeeper warning
        agent = {"name": "CoderAG", "role": "developer"}
        permissions = ["read"] # No "write"
        ans = "[WRITE: output.txt] test code [/WRITE]"
        result = process_actions(ans, agent, permissions, False, "/tmp")
        self.assertTrue("keine WRITE-Berechtigung" in result or "Schreibzugriff" in result)

    @patch("gnom_hub.soul.get_soul")
    @patch("gnom_hub.chat.brainstorm.brainstorm_helpers.post")
    @patch("gnom_hub.chat.brainstorm.brainstorm_helpers.ask_router")
    def test_self_diagnosis_feedback_loop(self, mock_ask_router, mock_post, mock_get_soul):
        # 2. Test that ask_llm triggers the self-diagnosis retry loop on failure and posts the Showbox card
        mock_get_soul.return_value = {
            "role": "developer",
            "permissions": ["read"], # No "write"
            "character": "Friendly Coder"
        }
        
        # First call to ask_router outputs the WRITE statement
        # Second call to ask_router outputs the SHOWBOX diagnostic warning card
        mock_response_1 = MagicMock()
        mock_response_1.content = "[WRITE: output.txt] some content [/WRITE]"
        
        mock_response_2 = MagicMock()
        mock_response_2.content = '<SHOWBOX:2>["<h3>Warnung: Fehlende Schreibrechte</h3>"]</SHOWBOX>'
        
        mock_ask_router.side_effect = [mock_response_1, mock_response_2]
        
        agent = {"name": "CoderAG", "role": "developer"}
        ask_llm(agent, "Speichere das in output.txt", ctx="")
        
        # Verify that ask_router was called twice (initial + self-diagnosis retry)
        self.assertEqual(mock_ask_router.call_count, 2)
        
        # Verify that the final posted content contains the Showbox warning card
        posted_content = mock_post.call_args[0][1]
        self.assertIn("<SHOWBOX:2>", posted_content)
        self.assertIn("Fehlende Schreibrechte", posted_content)

if __name__ == "__main__":
    unittest.main()
