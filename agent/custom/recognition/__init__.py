from importlib import import_module

RECOGNITION_MODULES = ("enemy", "vehicle", "pvp")


def register_all() -> None:
    for module_name in RECOGNITION_MODULES:
        import_module(f"custom.recognition.{module_name}")


__all__ = ["register_all"]
