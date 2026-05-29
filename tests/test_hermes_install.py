from pathlib import Path

import yaml

from google_health_local_sync.hermes_install import install_hermes_plugin


def test_install_hermes_plugin_copies_bundle(tmp_path):
    result = install_hermes_plugin(hermes_home=tmp_path, enable=False, platforms=["cli"])

    plugin_dir = Path(result["plugin_dir"])
    assert result["ok"] is True
    assert (plugin_dir / "plugin.yaml").exists()
    plugin_yaml = (plugin_dir / "plugin.yaml").read_text()
    assert "google_health_backfill" in plugin_yaml
    assert "google_health_latest" in plugin_yaml
    assert (plugin_dir / "__init__.py").exists()
    assert not (tmp_path / "config.yaml").exists()


def test_install_hermes_plugin_can_enable_toolset(tmp_path):
    (tmp_path / "config.yaml").write_text("plugins:\n  enabled: []\nplatform_toolsets:\n  cli: []\n", encoding="utf-8")

    result = install_hermes_plugin(hermes_home=tmp_path, enable=True, platforms=["cli", "whatsapp"])

    data = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert "google-health-local-sync" in data["plugins"]["enabled"]
    assert "google_health" in data["platform_toolsets"]["cli"]
    assert "google_health" in data["platform_toolsets"]["whatsapp"]
    assert "google_health" in data["known_plugin_toolsets"]["cli"]
    assert Path(result["config_backup"]).exists()
