from .eos_config import init_config


def plugin_init(config: dict):
    if not config:
        return

    init_config(config)
