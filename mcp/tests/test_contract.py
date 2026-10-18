"""The handshake that keeps this separately-installed client honest.

athena-mcp is installed on each user's machine and updated on their
schedule, so it can be either side of the deployment it talks to. These
cover both directions and the case where there is nothing to compare.
"""
import unittest

from athena_mcp import contract


class ContractTests(unittest.TestCase):
    def test_a_client_the_server_still_supports_may_run(self):
        health = {'mcp_contract': contract.CONTRACT_VERSION,
                  'mcp_contract_min': contract.CONTRACT_VERSION}
        self.assertIsNone(contract.refusal(health, 'https://api.example.com'))
        self.assertIsNone(contract.warning(health))

    def test_a_client_below_the_minimum_is_told_to_update(self):
        health = {'mcp_contract': contract.CONTRACT_VERSION + 3,
                  'mcp_contract_min': contract.CONTRACT_VERSION + 1}
        message = contract.refusal(health, 'https://api.example.com')
        self.assertIn('https://api.example.com', message)
        self.assertIn('uvx', message)

    def test_a_server_behind_this_client_warns_without_refusing(self):
        """Someone who updated early should still get their work done."""
        health = {'mcp_contract': contract.CONTRACT_VERSION - 1,
                  'mcp_contract_min': contract.CONTRACT_VERSION - 1}
        self.assertIsNone(contract.refusal(health, 'https://api.example.com'))
        self.assertIn('Older server', contract.warning(health))

    def test_a_deployment_that_advertises_nothing_is_left_alone(self):
        """A backend from before the handshake, or something that isn't
        Athena: there is no number to compare, so don't invent a verdict."""
        for health in ({'status': 'ok'}, {'mcp_contract_min': 'one'}):
            with self.subTest(health=health):
                self.assertIsNone(contract.refusal(health, 'https://api.example.com'))
                self.assertIsNone(contract.warning(health))


if __name__ == '__main__':
    unittest.main()
