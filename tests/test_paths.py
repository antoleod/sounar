from pathlib import Path

from sounar import paths


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("SOUNAR_CONFIG_DIR", "/x")
    monkeypatch.setenv("SOUNAR_STATE_DIR", "/y")
    monkeypatch.setenv("SOUNAR_CACHE_DIR", "/z")
    assert paths.config_dir() == Path("/x")
    assert paths.state_dir() == Path("/y")
    assert paths.cache_dir() == Path("/z")


def test_xdg_fallback(monkeypatch):
    for k in ("SOUNAR_CONFIG_DIR", "SOUNAR_STATE_DIR", "SOUNAR_CACHE_DIR"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", "/s")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/c")
    assert paths.state_dir() == Path("/s/sounar")
    assert paths.config_dir() == Path("/c/sounar")


def test_home_defaults(monkeypatch):
    for k in ("SOUNAR_CONFIG_DIR", "XDG_CONFIG_HOME", "SOUNAR_DATA_DIR", "XDG_DATA_HOME"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HOME", "/h")
    assert paths.config_dir() == Path("/h/.config/sounar")
    assert paths.data_dir() == Path("/h/.local/share/sounar")


def test_dry_run_flag(monkeypatch):
    monkeypatch.delenv("SOUNAR_DRY_RUN", raising=False)
    assert not paths.dry_run()
    monkeypatch.setenv("SOUNAR_DRY_RUN", "1")
    assert paths.dry_run()


def test_package_data_has_presets():
    assert (paths.package_data() / "presets.toml").name == "presets.toml"
    assert paths.package_data().name == "data"
