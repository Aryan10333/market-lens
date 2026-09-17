import json
import logging

import pytest

from jobs.config import ConfigError, load_settings, require
from jobs.log import JsonFormatter


def test_defaults_when_env_is_empty():
    s = load_settings({})
    assert s.app_env == "local"
    assert s.log_level == "INFO"
    assert s.database_url == ""


def test_values_are_cleaned():
    s = load_settings({"APP_ENV": " CI ", "LOG_LEVEL": "debug", "DATABASE_URL": " postgres://x "})
    assert s.app_env == "ci"
    assert s.log_level == "DEBUG"
    assert s.database_url == "postgres://x"


def test_invalid_env_is_rejected():
    with pytest.raises(ConfigError):
        load_settings({"APP_ENV": "staging"})


def test_invalid_log_level_is_rejected():
    with pytest.raises(ConfigError):
        load_settings({"LOG_LEVEL": "LOUD"})


def test_require_explains_missing_setting():
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        require("", "DATABASE_URL")


def test_log_lines_are_json_with_extra_fields():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    record.fields = {"rows": 5}
    entry = json.loads(JsonFormatter().format(record))
    assert entry["message"] == "hello"
    assert entry["level"] == "INFO"
    assert entry["rows"] == 5
