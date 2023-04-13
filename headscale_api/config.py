"""Headscale config abstration."""

from pydantic_yaml import YamlModelMixin

from .schema.config import Model as ConfigModel


class HeadscaleConfig(YamlModelMixin, ConfigModel):
    """Headscale config abstraction.

    Can be loaded, e.g., from file with `parse_file()` or from string with
    `parse_raw()`. for more details look at pydantic_yaml documentation
    (https://pydantic-yaml.readthedocs.io/en/latest/).
    """
