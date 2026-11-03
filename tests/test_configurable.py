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

        prop = ConfigurableProperty(
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

        prop = ConfigurableProperty(
            name="Exposure Time",
            default_value=100,
        )
        
        self.assertIsNotNone(prop)
        self.assertTrue(prop.is_in_valid_range(100))
        self.assertTrue(prop.is_in_valid_range(10000))
        self.assertTrue(prop.is_in_valid_range(-10000))
                         
    def test020_configurable_property_validated(self) -> None:

        prop = ConfigurableProperty(
            name="Exposure Time",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )
        
        self.assertIsNotNone(prop)
        self.assertTrue(prop.is_in_valid_range(100))
        self.assertFalse(prop.is_in_valid_range(10000))

    def test030_configurable_object(self) -> None:

        prop1 = ConfigurableProperty(
            name="exposure_time",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )

        prop2 = ConfigurableProperty(
            name="gain",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )
        
        obj = TestObject([prop1, prop2])
        self.assertIsNotNone(obj)
        
        print(obj.configuration)

    def test040_configurable_object_dialog(self) -> None:

        prop1 = ConfigurableProperty(
            name="exposure_time",
            displayed_name="Exposure time",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )

        prop2 = ConfigurableProperty(
            name="gain",
            displayed_name="Gain",
            default_value=3.14,
            min_value=0,
            max_value=1000,            
        )
        
        diag = ConfigurationDialog(title="Configuration", properties_description=[prop1, prop2], configuration={})
        reply = diag.run()
        print(diag.configuration)

    def test050_configurable_with_initial_configuration(self) -> None:
        """Verify that initial configuration overrides default values."""
        prop = ConfigurableProperty(name="gain", default_value=1)
        obj = TestObject([prop], configuration={"gain": 42})
        self.assertEqual(obj.configuration["gain"], 42)

    def test060_configurable_property_defaults(self) -> None:
        """Verify default field values on ConfigurableProperty."""
        prop = ConfigurableProperty(name="x")
        self.assertIsNone(prop.default_value)
        self.assertIsNone(prop.displayed_name)
        self.assertEqual(prop.min_value, float("-inf"))
        self.assertEqual(prop.max_value, float("+inf"))
        self.assertIsNone(prop.validate_fct)
        self.assertIsNone(prop.format_string)
        self.assertEqual(prop.multiplier, 1)
        self.assertEqual(prop.value_type, int)

    def test070_int_property_list(self) -> None:
        """Verify int_property_list creates properties from key names."""
        props = ConfigurableProperty.int_property_list(["width", "height", "depth"])
        self.assertEqual(len(props), 3)
        self.assertEqual(props[0].name, "width")
        self.assertEqual(props[1].name, "height")
        self.assertEqual(props[2].name, "depth")
        for p in props:
            self.assertEqual(p.value_type, int)
            self.assertIsNone(p.default_value)

    def test080_configurable_property_validate_fct(self) -> None:
        """Verify custom validation function works."""
        prop = ConfigurableProperty(
            name="even_number",
            default_value=2,
            validate_fct=lambda x: x % 2 == 0,
        )
        self.assertTrue(prop.validate_fct(2))
        self.assertTrue(prop.validate_fct(100))
        self.assertFalse(prop.validate_fct(3))

    def test090_configurable_property_format_string(self) -> None:
        """Verify format_string can be used for display."""
        prop = ConfigurableProperty(
            name="exposure",
            default_value=100,
            format_string="{:.1f} ms",
        )
        self.assertEqual(prop.format_string.format(prop.default_value), "100.0 ms")

    def test100_configurable_property_multiplier(self) -> None:
        """Verify multiplier field is stored correctly."""
        prop = ConfigurableProperty(
            name="voltage",
            default_value=5,
            multiplier=1000,
        )
        self.assertEqual(prop.multiplier, 1000)
        self.assertEqual(prop.default_value * prop.multiplier, 5000)

    def test110_configurable_property_value_type(self) -> None:
        """Verify value_type can be set to float."""
        prop = ConfigurableProperty(
            name="temperature",
            default_value=36.6,
            value_type=float,
        )
        self.assertEqual(prop.value_type, float)
        self.assertIsInstance(prop.value_type(prop.default_value), float)

    def test120_configurable_properties_description_dict(self) -> None:
        """Verify properties_description_dict maps names to properties."""
        prop1 = ConfigurableProperty(name="a", default_value=1)
        prop2 = ConfigurableProperty(name="b", default_value=2)
        obj = TestObject([prop1, prop2])
        self.assertIn("a", obj.properties_description_dict)
        self.assertIn("b", obj.properties_description_dict)
        self.assertEqual(obj.properties_description_dict["a"].default_value, 1)

    def test130_configurable_shared_memory_dict(self) -> None:
        """Verify configuration uses Manager dict (supports multiprocessing)."""
        prop = ConfigurableProperty(name="x", default_value=10)
        obj = TestObject([prop])
        self.assertEqual(obj.configuration["x"], 10)
        obj.configuration["x"] = 99
        self.assertEqual(obj.configuration["x"], 99)

    def test140_is_in_valid_range_boundary(self) -> None:
        """Verify boundary values are valid (inclusive range)."""
        prop = ConfigurableProperty(name="x", min_value=0, max_value=100)
        self.assertTrue(prop.is_in_valid_range(0))
        self.assertTrue(prop.is_in_valid_range(100))
        self.assertFalse(prop.is_in_valid_range(-1))
        self.assertFalse(prop.is_in_valid_range(101))

    def test150_configurable_displayed_name(self) -> None:
        """Verify displayed_name is stored and accessible."""
        prop = ConfigurableProperty(
            name="frame_rate",
            displayed_name="Frame Rate (Hz)",
            default_value=30,
        )
        self.assertEqual(prop.displayed_name, "Frame Rate (Hz)")


if __name__ == "__main__":
    envtest.main()
