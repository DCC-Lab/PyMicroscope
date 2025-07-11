import envtest
from typing import Optional, Tuple, Any

from pymicroscope.utils.configurable import Configurable, ConfigurableProperty, ConfigurationDialog
from mytk import Dialog, Label, Entry

class TestObject(Configurable):
    pass

class ConfigurableTestCase(envtest.CoreTestCase):
    def test000_configurable_property(self) -> None:
        """
        Verify that the abstract ImageProvider cannot be instantiated directly.
        """

        prop = ConfigurableProperty[int](
            name="Exposure Time",
            default_value=100,
            min_value=0,
            max_value=1000,
            validate_fct=lambda x: x >= 0,
            format_string="{:.1f} ms",
            multiplier=1000
        )
        
        self.assertIsNotNone(prop)

    def test010_configurable_property_with_defaults(self) -> None:

        prop = ConfigurableProperty[int](
            name="Exposure Time",
            default_value=100,
        )
        
        self.assertIsNotNone(prop)
        self.assertTrue(prop.is_in_valid_range(100))
        self.assertTrue(prop.is_in_valid_range(10000))
        self.assertTrue(prop.is_in_valid_range(-10000))
                         
    def test020_configurable_property_validated(self) -> None:

        prop = ConfigurableProperty[int](
            name="Exposure Time",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )
        
        self.assertIsNotNone(prop)
        self.assertTrue(prop.is_in_valid_range(100))
        self.assertFalse(prop.is_in_valid_range(10000))

    def test030_configurable_object(self) -> None:

        prop1 = ConfigurableProperty[int](
            name="exposure_time",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )

        prop2 = ConfigurableProperty[int](
            name="gain",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )
        
        obj = TestObject([prop1, prop2])
        self.assertIsNotNone(obj)
        
        print(obj.configuration)

    def test040_configurable_object_dialog(self) -> None:

        prop1 = ConfigurableProperty[int](
            name="exposure_time",
            displayed_name="Exposure time",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )

        prop2 = ConfigurableProperty[int](
            name="gain",
            displayed_name="Gain",
            default_value=3.14,
            min_value=0,
            max_value=1000,            
        )
        
        diag = ConfigurationDialog(title="Configuration", properties_description=[prop1, prop2], configuration={})
        reply = diag.run()
        print(diag.configuration)

if __name__ == "__main__":
    envtest.main()
