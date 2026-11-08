from mytk import Dialog, Label, Entry
from typing import Protocol, Optional, Any, Callable
from multiprocessing import Manager
from dataclasses import dataclass

@dataclass
class ConfigurableProperty:
    name: str
    default_value : Optional[Any] = None
    displayed_name: str = None
    min_value: Optional[Any] = float("-inf")
    max_value: Optional[Any] = float("+inf")
    validate_fct : Optional[Callable[[Any], bool]] = None
    format_string: Optional[str] = None
    multiplier: int = 1
    value_type: type = int
    
    def is_in_valid_range(self, value:Any):
        return (value >= self.min_value and value <= self.max_value)
    
    @staticmethod
    def int_property_list(keys:list[str]):
        properties = []
        for key in keys:
            properties.append(ConfigurableProperty(name=key, value_type=int))
        
        return properties
    
class Configurable:

    def __init__(self, properties_description:list[ConfigurableProperty] = None, configuration = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if properties_description is None:
            properties_description = []
        self.properties_description = properties_description
        self.properties_description_dict = { pd.name:pd  for pd in properties_description}

        self.configuration = Manager().dict()

        self.configuration.update({ p.name:p.default_value for p in properties_description })

        if configuration is not None:
            self.configuration.update(configuration)


class ConfigurationDialog(Dialog, Configurable):
    def __init__(
        self,
        populate_body_fct=None,
        properties_description=None,
        configuration=None,
        *args,
        **kwargs,
    ):
        # mytk's Bindable/EventCapable/DragAndDropCapable all call
        # super().__init__() with no arguments somewhere in Dialog's cooperative
        # multiple-inheritance chain, silently dropping any kwargs meant for
        # Configurable.__init__ further down the MRO (confirmed against mytk
        # 1.9.0: properties_description/configuration never arrived there).
        # So take them directly here and inline Configurable.__init__'s setup,
        # instead of relying on it ever being reached with these values.
        # Remove this workaround if a future mytk fixes the kwarg forwarding.
        super().__init__(*args, **kwargs)
        self.populate_body_fct = populate_body_fct
        self.configuration_widgets = {}

        if properties_description is None:
            properties_description = []
        self.properties_description = properties_description
        self.properties_description_dict = {
            pd.name: pd for pd in properties_description
        }

        self.configuration = Manager().dict()
        self.configuration.update(
            {p.name: p.default_value for p in properties_description}
        )
        if configuration is not None:
            self.configuration.update(configuration)
    
    def populate_widget_body(self):
        if self.populate_body_fct is None:
            for i, (key, value) in enumerate(self.configuration.items()):
                if key in self.properties_description_dict:
                    text_label = key
                    if self.properties_description_dict[key].displayed_name is not None:
                        text_label = self.properties_description_dict[key].displayed_name
                        
                    Label(text_label).grid_into(self, row=i, column=0, padx=10, pady=5, sticky="e")
                    entry = Entry(character_width=6)
                    entry.value_variable.set(value)
                    entry.grid_into(self, row=i, column=1, padx=10, pady=5, sticky="w")
                    self.configuration_widgets[key] = entry
        else:
            self.populate_body_fct()
                    
    def run(self):
        reply = super().run()
        for key, entry_widget in self.configuration_widgets.items():
            ValueType = self.properties_description_dict[key].value_type
            
            self.configuration[key] = ValueType(entry_widget.value_variable.get())
            
        return reply
