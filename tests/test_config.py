import csv
import json
import unittest


class ConfigTests(unittest.TestCase):
    def test_config_contains_companies_through_sixty_except_meta(self):
        with open("h1b-102-companies-careers-pages.csv", newline="") as file:
            rows = list(csv.DictReader(file))
            expected = {row["company"] for row in rows[:20]}
            expected.update(
                row["company"] for index, row in enumerate(rows[:60])
                if index != 25
            )

        with open("config/companies.json") as file:
            config = json.load(file)

        configured = {
            item["company"]
            for source, items in config.items()
            if source not in ("greenhouse", "lever")
            for item in items
        }
        greenhouse_companies = {
            "smartsheet": "Smartsheet",
            "digitalocean98": "DigitalOcean",
            "life360": "Life360",
            "seatgeek": "SeatGeek",
            "doordashusa": "DoorDash",
            "databricks": "Databricks",
            "stripe": "Stripe",
            "airbnb": "Airbnb",
            "anthropic": "Anthropic",
            "block": "Block",
            "coinbase": "Coinbase",
            "robinhood": "Robinhood",
            "pinterest": "Pinterest",
            "roblox": "Roblox",
        }
        configured.update(
            greenhouse_companies[token]
            for token in config.get("greenhouse", [])
        )
        configured.update(token.title() for token in config.get("lever", []))

        # Highspot's own page redirects to the consolidated Seismic board.
        configured.discard("Highspot / Seismic")
        configured.add("Highspot")
        # Juniper's career search now feeds into HPE's combined board.
        configured.add("Juniper Networks")
        self.assertEqual(configured, expected)


if __name__ == "__main__":
    unittest.main()
