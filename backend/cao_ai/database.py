from pathlib import Path


def build_database_config(base_dir: Path, env: dict[str, str]):
    engine = env.get("DB_ENGINE", "sqlite").lower()

    if engine == "mysql":
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env.get("DB_NAME", "cao_ai"),
            "USER": env.get("DB_USER", "root"),
            "PASSWORD": env.get("DB_PASSWORD", ""),
            "HOST": env.get("DB_HOST", "127.0.0.1"),
            "PORT": env.get("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
            },
        }

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": base_dir / "db.sqlite3",
    }
