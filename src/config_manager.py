"""Configuration management for comic viewer."""

import json
from pathlib import Path
from typing import Optional
from xdg_base_dirs import xdg_config_home


def get_config_dir() -> Path:
    """
    Get XDG config directory for comic viewer.

    Returns:
        Path to ~/.config/comic_viewer/
    """
    config_dir = xdg_config_home() / "comic_viewer"

    # Create directory if it doesn't exist
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create config directory: {e}")

    return config_dir


def get_config_path() -> Path:
    """
    Get path to config file.

    Returns:
        Path to config.json
    """
    return get_config_dir() / "config.json"


def load_config() -> dict:
    """
    Load configuration from file.

    Returns default config if file doesn't exist or is invalid.

    Returns:
        dict with keys: version, last_browsed_directory
    """
    config_path = get_config_path()

    # Default configuration
    default_config = {
        'version': '1.0',
        'last_browsed_directory': None
    }

    # Check if config file exists
    if not config_path.exists():
        return default_config

    # Try to load config file
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Warning: Corrupted config file, using defaults: {e}")
        return default_config
    except OSError as e:
        print(f"Warning: Could not read config file: {e}")
        return default_config

    # Validate version compatibility
    if config_data.get('version') != '1.0':
        print(f"Warning: Unknown config version, using defaults")
        return default_config

    # Merge with defaults to handle missing keys
    merged_config = default_config.copy()
    merged_config.update(config_data)

    return merged_config


def save_config(config: dict) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary to save

    Silent error handling - failures are logged but don't raise exceptions.
    """
    config_path = get_config_path()

    # Ensure version is set
    if 'version' not in config:
        config['version'] = '1.0'

    # Write config file
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        print(f"Warning: Could not save config: {e}")


def update_last_browsed_directory(directory: Path) -> None:
    """
    Update last browsed directory in config.

    Args:
        directory: Path to directory to remember

    This is a convenience function that loads the config, updates the
    last_browsed_directory field, and saves it back.
    """
    # Load current config
    config = load_config()

    # Update last browsed directory
    config['last_browsed_directory'] = str(directory.resolve())

    # Save updated config
    save_config(config)
