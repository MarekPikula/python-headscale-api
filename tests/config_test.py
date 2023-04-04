"""Config abstraction test."""

from headscale_api.config import HeadscaleConfig


def test_config_load():
    """Test default headscale config loading to generated model."""
    HeadscaleConfig.parse_file("external/headscale/config-example.yaml")
