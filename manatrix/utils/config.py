"""
Configuration utilities for Manatrix.

Provides functions for loading, saving, and manipulating YAML/JSON configuration files.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union


# Default config file path
DEFAULT_CONFIG_PATH = "config.yaml"

# Config cache for performance
_config_cache: Dict[str, Any] = {}


def load_config(
    config_path: Union[str, Path] = DEFAULT_CONFIG_PATH,
    use_cache: bool = True,
    create_if_missing: bool = False
) -> Dict[str, Any]:
    """
    Load configuration from a YAML or JSON file.

    Args:
        config_path: Path to the config file (YAML or JSON)
        use_cache: Whether to use cached config if available
        create_if_missing: Create default config if file doesn't exist

    Returns:
        Configuration dictionary

    Example:
        >>> config = load_config("config.yaml")
        >>> print(config["llm"]["api_key"])
    """
    config_path = str(config_path)

    # Check cache
    if use_cache and config_path in _config_cache:
        return _config_cache[config_path].copy()

    # Determine file format
    path = Path(config_path)
    ext = path.suffix.lower()

    if not path.exists():
        if create_if_missing:
            default = get_default_config()
            save_config(default, config_path)
            return default
        else:
            raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load based on format
    with open(path, "r", encoding="utf-8") as f:
        if ext in (".yaml", ".yml"):
            config = yaml.safe_load(f) or {}
        elif ext == ".json":
            config = json.load(f)
        else:
            # Try YAML first, then JSON
            content = f.read()
            try:
                config = yaml.safe_load(content) or {}
            except yaml.YAMLError:
                config = json.loads(content)

    # Update cache
    if use_cache:
        _config_cache[config_path] = config.copy()

    return config


def save_config(
    config: Dict[str, Any],
    config_path: Union[str, Path] = DEFAULT_CONFIG_PATH,
    format: Optional[str] = None
) -> None:
    """
    Save configuration to a YAML or JSON file.

    Args:
        config: Configuration dictionary to save
        config_path: Path to the config file
        format: Output format ("yaml", "json", or None to auto-detect)

    Example:
        >>> config = {"llm": {"api_key": "sk-xxx"}}
        >>> save_config(config, "config.yaml")
    """
    config_path = Path(config_path)

    # Determine format
    if format is None:
        ext = config_path.suffix.lower()
        format = "json" if ext == ".json" else "yaml"

    # Create parent directories if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write based on format
    with open(config_path, "w", encoding="utf-8") as f:
        if format == "json":
            json.dump(config, f, indent=2, ensure_ascii=False)
        else:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    # Update cache
    _config_cache[str(config_path)] = config.copy()


def get_config_value(
    key: str,
    config: Optional[Dict[str, Any]] = None,
    config_path: Union[str, Path] = DEFAULT_CONFIG_PATH,
    default: Any = None
) -> Any:
    """
    Get a configuration value using dot notation.

    Args:
        key: Dot-notation key (e.g., "llm.api_key")
        config: Config dict (if None, loads from file)
        config_path: Path to config file
        default: Default value if key not found

    Returns:
        Configuration value or default

    Example:
        >>> api_key = get_config_value("llm.api_key", default="")
    """
    if config is None:
        try:
            config = load_config(config_path)
        except FileNotFoundError:
            return default

    # Navigate nested keys
    keys = key.split(".")
    current = config

    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default

    return current


def set_config_value(
    key: str,
    value: Any,
    config: Optional[Dict[str, Any]] = None,
    config_path: Union[str, Path] = DEFAULT_CONFIG_PATH,
    save: bool = True
) -> Dict[str, Any]:
    """
    Set a configuration value using dot notation.

    Args:
        key: Dot-notation key (e.g., "llm.api_key")
        value: Value to set
        config: Config dict (if None, loads from file)
        config_path: Path to config file
        save: Whether to save to file after setting

    Returns:
        Updated configuration dictionary

    Example:
        >>> config = set_config_value("llm.api_key", "sk-xxx")
    """
    if config is None:
        try:
            config = load_config(config_path)
        except FileNotFoundError:
            config = {}

    # Navigate and set nested keys
    keys = key.split(".")
    current = config

    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]

    current[keys[-1]] = value

    # Save if requested
    if save:
        save_config(config, config_path)

    return config


def get_default_config() -> Dict[str, Any]:
    """
    Get the default configuration for Manatrix.

    Returns:
        Default configuration dictionary
    """
    return {
        "model": {
            "name": "mamba-password",
            "d_model": 256,
            "n_layer": 4,
            "vocab_size": 128,
        },
        "llm": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_base": "https://api.deepseek.com/v1",
            "api_key": "",
        },
        "training": {
            "batch_size": 64,
            "epochs": 100,
            "learning_rate": 0.001,
        },
        "pentest": {
            "auto_mode": True,
            "max_steps": 50,
        },
        "rag": {
            "embedding": "all-MiniLM-L6-v2",
            "chunk_size": 512,
            "top_k": 5,
        },
    }


def merge_configs(
    base: Dict[str, Any],
    override: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deep merge two configuration dictionaries.

    Args:
        base: Base configuration
        override: Configuration to merge/override

    Returns:
        Merged configuration
    """
    result = base.copy()

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def validate_config(
    config: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None
) -> tuple[bool, list[str]]:
    """
    Validate configuration against a schema.

    Args:
        config: Configuration to validate
        schema: Validation schema (if None, uses default schema)

    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []

    if schema is None:
        # Basic validation
        required_sections = ["model", "llm"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")

    else:
        # Schema-based validation
        for section, requirements in schema.items():
            if requirements.get("required", False) and section not in config:
                errors.append(f"Missing required section: {section}")

    return len(errors) == 0, errors


def clear_cache(config_path: Optional[str] = None) -> None:
    """
    Clear the configuration cache.

    Args:
        config_path: Specific path to clear, or None to clear all
    """
    global _config_cache

    if config_path:
        _config_cache.pop(config_path, None)
    else:
        _config_cache.clear()
