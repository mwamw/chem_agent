import pytest

from app.core.config import Settings, validate_runtime_settings


def test_validate_runtime_settings_allows_dev_defaults():
    settings = Settings()
    validate_runtime_settings(settings)


def test_validate_runtime_settings_rejects_insecure_prod_defaults():
    settings = Settings(
        app_env="prod",
        jwt_secret_key="change-me",
        demo_auth_enabled=True,
        allow_auto_user_signup=True,
        allowed_origins=["*"],
    )
    with pytest.raises(RuntimeError):
        validate_runtime_settings(settings)
