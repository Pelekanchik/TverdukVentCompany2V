"""QThread helpers for background GUI work."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class FunctionWorker(QThread):
    """Run a function in a background thread and emit result/error."""

    result = Signal(object)
    error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:  # pragma: no cover - surfaced to GUI
            self.error.emit(str(exc) or repr(exc))
