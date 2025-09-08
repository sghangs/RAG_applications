import yaml
import os
from utils.logger import logger
from exceptions import KnowledgeManagementException

class ConfigLoader:
    """
    Loads YAML configuration for parser settings
    """

    def __init__(self, config_path="config/parsers.yaml"):
        if not os.path.exists(config_path):
            raise KnowledgeManagementException(
                f"Config file not found at {config_path}",
                None,
                "ConfigLoader"
            )
        with open(config_path, "r") as f:
            try:
                self.config = yaml.safe_load(f)
                logger.info(f"Loaded parser config from {config_path}")
            except Exception as e:
                raise KnowledgeManagementException(
                    f"Failed to parse config: {e}",
                    None,
                    "ConfigLoader"
                )

    def get(self, parser_name: str, key: str, default=None):
        return self.config.get(parser_name, {}).get(key, default)
