"""Process-safe Configurable properties, built on top of mytk.configurable.

mytk's Configurable mixin (see mytk/configurable.py) stores each declared
property's value in the owning instance's __dict__. That is fine for a
plain in-process object, but PyMicroscope's ImageProvider runs inside its
own multiprocessing.Process: the GUI process must be able to change a
provider's configuration (e.g. via the "Configure..." dialog) after the
capture process has already started, and have the running process see the
new value on its next captured frame.

Verified empirically that mytk's Configurable does NOT support this: a
value set from the parent after the child process starts is never seen by
the child, because each process gets its own independent copy of the
instance's __dict__.

The classes below are a thin patch: they redirect each property's storage
into a multiprocessing.Manager().dict() (self.configuration) instead of
__dict__, which *is* visible across the process boundary. Everything else
(validation, clamping, ConfigurationDialog, show_config_dialog()) comes
from mytk unmodified.

This is meant to be temporary: once mytk itself supports process-safe
storage, this module should be deleted and callers should import directly
from mytk.
"""
from multiprocessing import Manager

from mytk.configurable import (
    Configurable as MytkConfigurable,
    ConfigurableProperty,
    ConfigurableNumericProperty,
    ConfigurableStringProperty,
)

__all__ = [
    "ConfigurableProperty",
    "ConfigurableNumericProperty",
    "ConfigurableStringProperty",
    "ProcessSafeConfigurableProperty",
    "ProcessSafeConfigurableNumericProperty",
    "ProcessSafeConfigurableStringProperty",
    "ProcessSafeConfigurable",
]


class ProcessSafeConfigurableProperty(ConfigurableProperty):
    """Like mytk's ConfigurableProperty, but stores its value in the owning
    instance's self.configuration (a multiprocessing.Manager().dict())
    instead of obj.__dict__."""

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.configuration.get(self.name, self.default_value)

    def __set__(self, obj, value):
        obj.configuration[self.name] = self.sanitize(value)


class ProcessSafeConfigurableNumericProperty(
    ProcessSafeConfigurableProperty, ConfigurableNumericProperty
):
    pass


class ProcessSafeConfigurableStringProperty(
    ProcessSafeConfigurableProperty, ConfigurableStringProperty
):
    pass


class ProcessSafeConfigurable(MytkConfigurable):
    """Like mytk's Configurable mixin, but backs every declared property
    with a multiprocessing.Manager().dict() (self.configuration) so that
    values set from one process are visible to another process holding
    the same (already-running) instance."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configuration = Manager().dict()
        for name, prop in self._configurable_properties().items():
            self.configuration[name] = prop.default_value

    def set_configuration(self, values: dict) -> None:
        """Apply a dict of property updates (sanitized by each descriptor)."""
        self.update_values(values)
