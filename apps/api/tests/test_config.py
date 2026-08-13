from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.core.config import Settings


class SettingsTests(unittest.TestCase):
    def test_embedding_dimensions_accepts_env_style_string(self) -> None:
        settings = Settings(
            _env_file=None,
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_ANON_KEY="anon-key",
            SUPABASE_SERVICE_ROLE_KEY="service-role-key",
            EMBEDDING_DIMENSIONS="1536",
        )

        self.assertEqual(settings.EMBEDDING_DIMENSIONS, 1536)
        self.assertIsInstance(settings.EMBEDDING_DIMENSIONS, int)

    def test_embedding_dimensions_rejects_db_mismatch(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                SUPABASE_URL="https://example.supabase.co",
                SUPABASE_ANON_KEY="anon-key",
                SUPABASE_SERVICE_ROLE_KEY="service-role-key",
                EMBEDDING_DIMENSIONS="3072",
            )


if __name__ == "__main__":
    unittest.main()
