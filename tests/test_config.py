import csv
import json
import unittest


class ConfigTests(unittest.TestCase):
    def test_config_contains_exactly_the_first_ten_csv_companies(self):
        with open("h1b-102-companies-careers-pages.csv", newline="") as file:
            expected = {
                row["company"]
                for row in list(csv.DictReader(file))[:10]
            }

        with open("config/companies.json") as file:
            config = json.load(file)

        configured = {
            item["company"]
            for source, items in config.items()
            if source not in ("greenhouse", "lever")
            for item in items
        }
        configured.update(
            token.title() for token in config.get("greenhouse", [])
        )
        configured.update(token.title() for token in config.get("lever", []))

        # Highspot's own page redirects to the consolidated Seismic board.
        configured.discard("Highspot / Seismic")
        configured.add("Highspot")
        self.assertEqual(configured, expected)


if __name__ == "__main__":
    unittest.main()
