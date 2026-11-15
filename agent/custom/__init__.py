import sys

from . import action, recognition, sink

sys.modules.setdefault("custom", sys.modules[__name__])
sys.modules.setdefault("custom.action", action)
sys.modules.setdefault("custom.recognition", recognition)
sys.modules.setdefault("custom.sink", sink)


def register_all() -> None:
    action.register_all()
    recognition.register_all()
    sink.register_all()


__all__ = ["register_all"]
