import os
import toml

from ..types.config import Config


def load_config() -> Config:
    """Loads Role Assigner config from its toml file

    Returns:
        Config: The config object
    """
    module_root = os.path.join(os.path.dirname(__file__), "..")

    with open(f"{module_root}/config.toml") as f:
        config: dict = toml.load(f)
        config: Config = Config(**config)

    return config


def write_config(config: Config) -> None:
    """Saves Role Assigner config in its toml file

    Args:
        config (Config): config object
    """
    module_root = os.path.join(os.path.dirname(__file__), "..")

    with open(f"{module_root}/config.toml", "w") as f:
        config = config.dict()
        toml.dump(config, f)
