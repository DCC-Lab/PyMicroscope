import envtest
from typing import Optional, Tuple, Any

from pymicroscope.utils.configurable import Configurable, ConfigurableStringProperty, ConfigurableNumericProperty
# from mytk import Dialog, Label, Entry
import threading, atexit, sys


class TestObject(Configurable):
    pass

class ConfigurableTestCase(envtest.CoreTestCase):
    def test000_configurable_property(self) -> None:
        """
        Verify that the abstract ImageProvider cannot be instantiated directly.
        """

        prop = ConfigurableNumericProperty(
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

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            default_value=100,
        )
        
        self.assertIsNotNone(prop)
        self.assertTrue(prop.is_in_valid_range(100))
        self.assertTrue(prop.is_in_valid_range(10000))
        self.assertTrue(prop.is_in_valid_range(-10000))
                         
    def test020_configurable_property_validated(self) -> None:

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )
        
        self.assertIsNotNone(prop)
        self.assertTrue(prop.is_in_valid_range(100))
        self.assertFalse(prop.is_in_valid_range(10000))

    def test022_configurable_property_is_valid_set(self) -> None:

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            valid_set = set([1,2,3])
        )

        self.assertTrue(prop.is_in_valid_set(1))
        self.assertTrue(prop.is_in_valid_set(2))
        self.assertFalse(prop.is_in_valid_set(0))

    def test022_configurable_property_is_valid_set_as_list(self) -> None:

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            valid_set = [1,2,3]
        )

        self.assertTrue(prop.is_in_valid_set(1))
        self.assertTrue(prop.is_in_valid_set(2))
        self.assertFalse(prop.is_in_valid_set(0))

    def test025_configurable_property_is_valid(self) -> None:

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            default_value=100,
            min_value=0,
            max_value=1000,
            value_type=int         
        )
        
        self.assertTrue(prop.is_valid(100))
        self.assertTrue(prop.is_valid(0))
        self.assertTrue(prop.is_valid(1000))
        self.assertFalse(prop.is_valid(-100))
        self.assertFalse(prop.is_valid(5.5))
        self.assertFalse(prop.is_valid(5000.12))
        
    def test025_configurable_property_sanitize(self) -> None:

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            default_value=100,
            min_value=0,
            max_value=1000,
            value_type=int         
        )

        self.assertEqual(prop.sanitize(-100), 0)
        self.assertEqual(prop.sanitize(2000), 1000)
        self.assertEqual(prop.sanitize(100.5), 100)
        
    def test026_configurable_property_sanitize_no_type(self) -> None:

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            default_value=100,
            min_value=0,
            max_value=1000,
        )

        self.assertEqual(prop.sanitize(-100.1), 0)
        self.assertEqual(prop.sanitize(2000), 1000)
        self.assertEqual(prop.sanitize(100.5), 100) 

    def test026_configurable_property_sanitize_type_inferred_from_default_no_range(self) -> None:

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            default_value=100,
        )

        self.assertEqual(prop.sanitize(-100.1), -100)
        self.assertEqual(prop.sanitize(2000), 2000)
        self.assertEqual(prop.sanitize(100.5), 100)

    def test027_configurable_property_sanitize_no_type_no_range(self) -> None:

        prop = ConfigurableNumericProperty(
            name="Exposure Time",
            default_value=100,
            value_type=Any
        )

        self.assertEqual(prop.sanitize(-100.1), -100.1)
        self.assertEqual(prop.sanitize(2000), 2000)
        self.assertEqual(prop.sanitize(100.5), 100.5)

    def test028_configurable_property_wrong_type(self) -> None:

        with self.assertRaises(ValueError):
            prop = ConfigurableNumericProperty(
                name="Exposure Time",
                default_value=100.1,
                min_value=0,
                max_value=1000,
                value_type=int
            )

        with self.assertRaises(ValueError):
            prop = ConfigurableNumericProperty(
                name="Exposure Time",
                default_value=100.0,
                min_value=0,
                max_value=1000,
                value_type=int
            )

    def test028_configurable_property_wrong_str_type(self) -> None:
        with self.assertRaises(ValueError):
            prop = ConfigurableStringProperty(
                name="String",
                default_value=100.0,
            )

    def test029_configurable_property_is_invalid(self) -> None:
        prop = ConfigurableStringProperty(name="String")
        self.assertFalse(prop.is_valid(10))

    def test031_configurable_property_is_in_valid_set_but_set_is_empty(self) -> None:
        prop = ConfigurableStringProperty(name="String")
        self.assertTrue(prop.is_in_valid_set(10))

    def test031_configurable_property_has_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            prop = ConfigurableStringProperty(name="String", valid_set=['a', 1])

    def test031_configurable_property_sanitize_none_to_default(self) -> None:
        prop = ConfigurableStringProperty(name="String", default_value="Something")
        self.assertEqual(prop.sanitize(None), "Something")

    def test031_configurable_property_sanitize_unabnle_to_cast_defaults_to_default_value(self) -> None:
        prop = ConfigurableNumericProperty(name="Numeric value", default_value=100)
        self.assertEqual(prop.sanitize("adsklahjs"), 100)
            
    def test050_configurable_str_property(self) -> None:

        prop = ConfigurableStringProperty(
            name="Name",
            valid_regex="[ABC]def"
        )

        self.assertEqual(prop.value_type, str)
        
        self.assertTrue(prop.is_valid("Adef"))
        self.assertTrue(prop.is_valid("Bdef"))
        self.assertTrue(prop.is_valid("Cdef"))
        self.assertFalse(prop.is_valid("Test"))
        self.assertFalse(prop.is_valid(100))
        self.assertEqual(prop.sanitize("Cdef"), 'Cdef')

    def test051_configurable_str_property_is_valid_set_as_list(self) -> None:

        prop = ConfigurableStringProperty(
            name="Name",
            valid_set = ["Daniel", "Mireille"],
            valid_regex = ".*"
        )

        self.assertTrue(prop.is_in_valid_set("Daniel"))
        self.assertTrue(prop.is_in_valid_set("Mireille"))
        self.assertFalse(prop.is_in_valid_set("Bob the builder"))

    
    def test060_quick_propertyy_lists(self):
        props = ConfigurableNumericProperty.int_property_list(['a','b'])
        self.assertIsNotNone(props)
        self.assertEqual(len(props), 2)
        
    def test030_configurable_object(self) -> None:

        prop1 = ConfigurableNumericProperty(
            name="exposure_time",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )

        prop2 = ConfigurableNumericProperty(
            name="gain",
            default_value=100,
            min_value=0,
            max_value=1000,            
        )
        
        obj = TestObject([prop1, prop2])
        self.assertIsNotNone(obj)
        
    # def test040_configurable_object_dialog(self) -> None:

    #     prop1 = ConfigurableNumericProperty(
    #         name="exposure_time",
    #         displayed_name="Exposure time",
    #         default_value=100,
    #         min_value=0,
    #         max_value=1000,
    #         value_type=int          
    #     )

    #     prop2 = ConfigurableNumericProperty(
    #         name="gain",
    #         displayed_name="Gain",
    #         default_value=3,
    #         min_value=0,
    #         max_value=1000,
    #         value_type=int
    #     )
        
    #     diag = ConfigurationDialog(title="Configuration", properties=[prop1, prop2],
    #                                buttons_labels=["Ok"], auto_click=("Ok", 200))
    #     reply = diag.run()
    #     print(diag.values)
        
    # # def test050_ConfiguModel(self) -> None:
    # #     ConfigModel()

def tearDownModule():
    # 1) Ensure all non-main threads are gone
    others = [t for t in threading.enumerate() if t is not threading.main_thread()]
    if others:
        print("\n[DIAG] Non-main threads still alive at teardown:", file=sys.stderr)
        for t in others:
            print(f"  - {t!r} (daemon={t.daemon})", file=sys.stderr)
    # 2) Forcefully flush stdio (helps surface late exceptions)
    sys.stderr.flush()
    sys.stdout.flush()
    
if __name__ == "__main__":
    envtest.main()
