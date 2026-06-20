from pathlib import Path
from unittest import TestCase

from cao_ai.database import build_database_config


class DatabaseConfigTests(TestCase):
    def test_builds_mysql_config_from_environment(self):
        config = build_database_config(
            Path("E:/project/backend"),
            {
                "DB_ENGINE": "mysql",
                "DB_NAME": "cao_ai",
                "DB_USER": "root",
                "DB_PASSWORD": "secret",
                "DB_HOST": "127.0.0.1",
                "DB_PORT": "3306",
            },
        )

        self.assertEqual(config["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(config["NAME"], "cao_ai")
        self.assertEqual(config["USER"], "root")
        self.assertEqual(config["PASSWORD"], "secret")
        self.assertEqual(config["HOST"], "127.0.0.1")
        self.assertEqual(config["PORT"], "3306")
        self.assertEqual(config["OPTIONS"]["charset"], "utf8mb4")

    def test_defaults_to_sqlite(self):
        config = build_database_config(Path("E:/project/backend"), {})

        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(config["NAME"], Path("E:/project/backend") / "db.sqlite3")
