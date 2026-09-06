from importlib import import_module

ACTION_MODULES = (
    "general",
    "sweep",
    "scene_jump",
    "stage_select",
    "pvp",
    "activity.1_sweep",
    "activity.1_shop",
)


def register_all() -> None:
    for module_name in ACTION_MODULES:
        import_module(f"custom.action.{module_name}")


__all__ = ["register_all"]
