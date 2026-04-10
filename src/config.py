import os
import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    config["tavily_api_key"] = os.environ["TAVILY_API_KEY"]
    config["deepseek_api_key"] = os.environ["DEEPSEEK_API_KEY"]
    config["serverchan_sendkey"] = os.environ["SERVERCHAN_SENDKEY"]

    config.setdefault("max_items_per_category", 5)
    config.setdefault("max_age_days", 3)
    config.setdefault("max_input_items", 80)
    config.setdefault("dedup_similarity_threshold", 0.7)

    return config
