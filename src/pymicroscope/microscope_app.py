import sys

import mytk
from mytk import *
from packaging.version import Version
from notificationcenter import NotificationCenter, Notification
import signal
from contextlib import suppress
import numpy as np
from queue import Queue as TQueue, Empty, Full
from multiprocessing import Queue as MPQueue
from tkinter import filedialog
from pathlib import Path
from threading import Thread

# mytk has no app-level default padx/pady for grid_into (verified absent as of
# mytk 1.9.0): every call must repeat its own padding. MicroscopeApp.grid_into_with_defaults
# below is a *temporary* local shim for that, to be deleted and replaced by mytk's
# own mechanism once/if it gains one - see https://github.com/DCC-Lab/myTk.
# This constant marks the newest mytk version known to still lack it; bump it only
# after confirming (not assuming) a newer mytk still lacks the feature.
_MYTK_LAST_VERSION_WITHOUT_DEFAULT_PADDING = "1.9.0"
_mytk_version = Version(mytk.__version__)
NEEDS_PADDING_SHIM = _mytk_version <= Version(
    _MYTK_LAST_VERSION_WITHOUT_DEFAULT_PADDING
)

if not NEEDS_PADDING_SHIM:
    print(
        f"[PyMicroscope] WARNING: mytk {mytk.__version__} is newer than "
        f"{_MYTK_LAST_VERSION_WITHOUT_DEFAULT_PADDING}; skipping the local "
        "grid_into_with_defaults() padding shim in microscope_app.py. Check "
        "whether mytk now provides app-level default padx/pady for grid_into "
        "natively, and delete the shim (and this check) if so.",
        file=sys.stderr,
    )

from PIL import Image as PILImage
from pymicroscope.acquisition.imageprovider import DebugImageProvider, ImageProvider
from pymicroscope.acquisition.cameraprovider import OpenCVImageProvider
from pymicroscope.base.mapcontroller import MapController
from pymicroscope.experiment.actions import *
from pymicroscope.experiment.experiments import Experiment, ExperimentStep
from pymicroscope.app_notifications import MicroscopeAppNotification
from pymicroscope.base.save_history import SaveHistory
from pymicroscope.utils.thread_utils import is_main_thread
from pymicroscope.plugins.delay_line import DelaysController

from hardwarelibrary.physicaldevice import PhysicalDevice
from hardwarelibrary.motion import SutterDevice
from pymicroscope.hardware.kinesisdevice import KinesisDevice



class MicroscopeApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.image_queue:MPQueue = MPQueue()
        self.preview_queue:TQueue = TQueue(maxsize=1)
        self.images_directory:Path = Path("~/Desktop").expanduser()
        self.images_template:str = "Image-{date}-{time}-{i}.tif"

        self.shape:tuple = (480, 640, 3)
        self.provider:ImageProvider = None
        
        # Do not modify outside of main thread
        self.cameras = {
            "Debug": {
                "type": DebugImageProvider,
                "args": (),
                "kwargs": {"size": self.shape},
            }
        }

        self.history = SaveHistory()
        
        self.is_camera_running = False

        self.sample_position_device = SutterDevice(serialNumber="debug")
        self.delay_device:LinearMotionDevice = KinesisDevice(serialNumber="83849018")

        try:
            self.delay_device.initializeDevice()
            self.delay_position = self.delay_device.position()
            self.delay_device_is_ready = True
        except PhysicalDevice.UnableToInitialize as e:
            self.delay_position = None
            self.delay_device_is_ready = False
            
        self.delay_controller = DelaysController()

        self.map_controller = MapController(self.sample_position_device)

        self.can_start_map = False

        self.app_setup()
        self.build_interface()
        self.after(100, self.microscope_run_loop)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def app_setup(self):
        def handle_sigterm(signum, frame):
            self.quit()

        for s in [signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]:
            signal.signal(s, handle_sigterm)

        try:
            # This is called when the user clicks "Quit" from the Apple menu or presses ⌘+Q
            self.root.createcommand("tk::mac::Quit", self.quit)
        except TclError:
            pass  # Not on macOS or already defined

        NotificationCenter().add_observer(
            self,
            method=self.handle_notification,
            notification_name=MicroscopeAppNotification.will_start_capture,
        )
        NotificationCenter().add_observer(
            self,
            method=self.handle_notification,
            notification_name=MicroscopeAppNotification.did_start_capture,
        )
        NotificationCenter().add_observer(
            self,
            method=self.handle_notification,
            notification_name=MicroscopeAppNotification.will_stop_capture,
        )
        NotificationCenter().add_observer(
            self,
            method=self.handle_notification,
            notification_name=MicroscopeAppNotification.did_stop_capture,
        )
        NotificationCenter().add_observer(
            self,
            method=self.handle_notification,
            notification_name=MicroscopeAppNotification.new_image_received,
        )
        NotificationCenter().add_observer(
            self,
            method=self.handle_notification,
            notification_name=MicroscopeAppNotification.available_providers_changed,
        )

        NotificationCenter().add_observer(
            self,
            method=self.handle_notification,
            notification_name=MicroscopeAppNotification.did_save,
        )

        NotificationCenter().add_observer(
            self,
            method=self.handle_notification,
            notification_name=MicroscopeAppNotification.did_save_file,
        )

    def background_get_providers(self):
        providers = {
            "Debug": {
                "type": DebugImageProvider,
                "args": (),
                "kwargs": {"size": self.shape},
            }
        }

        devices = OpenCVImageProvider.available_devices()
        for device in devices:
            providers[f"OpenCV camera #{device}"] = {
                "type": OpenCVImageProvider,
                "args": (),
                "kwargs": {"camera_index": device},
            }

        NotificationCenter().post_notification(
            MicroscopeAppNotification.available_providers_changed,
            notifying_object=self,
            user_info={"providers": providers},
        )
        
    def cleanup(self):
        try:
            self.history.window.widget.destroy()
        except Exception as err:
            pass    
        # del self.history
    
    def build_interface(self):
        assert is_main_thread()
        
        self.window.widget.title("PyMicroscope")

        self.build_imageview_interface()

        self.right_column = View()
        self.right_column.grid_into(
            self.window, column=1, row=0, rowspan=5, pady=30, padx=20, sticky="nw"
        )

        self.build_start_stop_interface()
        self.build_position_interface()
        # self.build_map_interface()  # temporarily removed from the main window
        self.build_cameras_menu()
        # self.build_delay_interface()  # temporarily removed from the main window

        self.constrain_window_size()

    def constrain_window_size(self):
        """Cap the window's width so it never exceeds MAX_WINDOW_WIDTH, letting
        the camera preview (the only resizable column) shrink to absorb the
        difference while keeping its aspect ratio."""
        MAX_WINDOW_WIDTH = 1300
        MIN_WINDOW_WIDTH = 1060

        window = self.window.widget
        window.update_idletasks()
        natural_width = window.winfo_reqwidth()
        natural_height = window.winfo_reqheight()

        target_width = min(natural_width, MAX_WINDOW_WIDTH)
        window.grid_propagate(False)
        window.geometry(f"{target_width}x{natural_height}")
        window.resizable(True, False)
        window.minsize(MIN_WINDOW_WIDTH, natural_height)
        window.maxsize(target_width, natural_height)

        window.update_idletasks()
        self.image.is_rescalable = True

    def build_imageview_interface(self):
        assert is_main_thread()

        array = np.zeros(self.shape, dtype=np.uint8)
        pil_image = PILImage.fromarray(array, mode="RGB")
        self.image = Image(pil_image=pil_image)

        self.image.grid_into(
            self.window,
            row=0,
            column=0,
            rowspan=5,
            pady=30,
            padx=20,
            sticky="nw",
        )
        self.window.widget.columnconfigure(0, weight=1)
        self.window.widget.rowconfigure(0, weight=1)

    def build_cameras_menu(self):
        Thread(target=self.background_get_providers).start()

    def update_provider_menu(self, providers):
        assert is_main_thread()

        selected_provider = self.camera_popup.value_variable.get()
        self.camera_popup.clear_menu_items()
        self.camera_popup.add_menu_items(list(providers.keys()))
        self.cameras = providers
        self.camera_popup.value_variable.set(value=selected_provider)
                

    def build_start_stop_interface(self):
        assert is_main_thread()

        self.save_controls = Box(label="Image Acquisition")

        self.save_controls.grid_into(
            self.right_column, column=0, row=0, sticky="new"
        )

        self.camera_popup = PopupMenu(
            list(self.cameras.keys()), user_callback=self.user_changed_camera
        )
        self.camera_popup.grid_into(
            self.save_controls, row=0, column=1, pady=10, padx=10, sticky="w"
        )
        self.camera_popup.value_variable.set(list(self.cameras.keys())[0])

        self.bind_properties(
            "is_camera_running", self.camera_popup, "is_disabled"
        )

        self.provider_settings = Button(
            "Configure …",
            user_event_callback=self.user_clicked_configure_button,
        )
        self.provider_settings.grid_into(
            self.save_controls, row=0, column=2, pady=10, padx=10, sticky="w"
        )

        self.start_stop_button = Button(
            "Start", user_event_callback=self.user_clicked_startstop
        )
        self.start_stop_button.grid_into(
            self.save_controls,
            row=0,
            column=0,
            pady=10,
            padx=10,
        )

        self.save_button = Button(
            "Save …", user_event_callback=self.user_clicked_save
        )
        self.save_button.grid_into(
            self.save_controls,
            row=2,
            column=0,
            pady=10,
            padx=10,
        )
        self.bind_properties(
            "is_camera_running", self.save_button, "is_enabled"
        )

        Label("Images to average: ").grid_into(
            self.save_controls, row=2, column=1, pady=10, padx=10, sticky="e"
        )

        self.number_of_images_average = IntEntry(value=30, width=5)
        self.number_of_images_average.grid_into(
            self.save_controls, row=2, column=2, pady=10, padx=10, sticky="w"
        )

        self.choose_directory_button = Button(
            "Directory …",
            user_event_callback=self.user_clicked_choose_directory,
        )
        self.choose_directory_button.grid_into(
            self.save_controls, row=3, column=0, pady=10, padx=10, sticky="e"
        )

        label = Label("(directory)")
        label.grid_into(
            self.save_controls, row=3, column=1, pady=10, padx=10, sticky="e"
        )
        self.bind_properties("images_directory", label, "value_variable")

        entry = Entry()
        entry.grid_into(
            self.save_controls, row=3, column=2, pady=10, padx=10, sticky="e"
        )
        self.bind_properties("images_template", entry, "value_variable")

    def handle_notification(self, notification: Notification):
        if notification.name == MicroscopeAppNotification.did_start_capture:
            self.is_camera_running = True
            self.start_stop_button.label = "Stop"

        if notification.name == MicroscopeAppNotification.did_stop_capture:
            self.is_camera_running = False
            self.start_stop_button.label = "Start"

        if notification.name == MicroscopeAppNotification.new_image_received:
            with suppress(Full):
                self.preview_queue.put_nowait(
                    notification.user_info["img_array"]
                )

        if notification.name == MicroscopeAppNotification.did_save_file:
            filepath = notification.user_info['filepath']
            self.schedule_on_main_thread(self.history.add, (filepath, ))
                
        if (
            notification.name
            == MicroscopeAppNotification.available_providers_changed
        ):
            self.schedule_on_main_thread(self.update_provider_menu, (notification.user_info['providers'], ))
            # self.update_provider_menu(providers=notification.user_info['providers'])

    def user_clicked_choose_directory(self, button, event):
        self.images_directory = filedialog.askdirectory(
            title="Select a destination for images:",
            initialdir=self.images_directory,
        )

        if self.images_directory == "":
            self.images_directory = "/tmp"

    def user_clicked_save(self, button, event):
        self.save()

    def save_actions_current_settings(self, sound_bell=True) -> list[Action]:
        n_images = self.number_of_images_average.value

        start_provider = ActionProviderRun(app=self, start=True)
        starting1 = ActionChangeProperty(self.save_button, "is_disabled", True)
        starting2 = ActionChangeProperty(
            self.number_of_images_average, "is_disabled", True
        )
        notif_start = ActionPostNotification(
            MicroscopeAppNotification.did_start_saving
        )
        capture = ActionAccumulate(n_images=n_images)
        mean = ActionMean(source=capture)
        save = ActionSave(
            source=mean,
            root_dir=self.images_directory,
            template=self.images_template,
        )
        notif_complete = ActionPostNotification(
            MicroscopeAppNotification.did_save
        )
        bell = ActionSound(sound_name=ActionSound.MacOSSound.FUNK)
        ending1 = ActionChangeProperty(self.save_button, "is_disabled", False)
        ending2 = ActionChangeProperty(
            self.number_of_images_average, "is_disabled", False
        )

        return [
            start_provider,
            notif_start,
            starting1,
            starting2,
            capture,
            mean,
            save,
            notif_complete,
            bell,
            ending1,
            ending2,
        ]

    def save(self):
        actions = self.save_actions_current_settings()

        Experiment.from_actions(actions).perform_in_background_thread()

    def user_changed_camera(self, popup, index):
        self.change_provider()

    DEFAULT_PADX = 4
    DEFAULT_PADY = 4

    def grid_into_with_defaults(self, widget, parent, **kwargs):
        """Like widget.grid_into(parent, **kwargs), but falls back to this
        app's default padx/pady when the caller doesn't specify them.

        Temporary shim - see NEEDS_PADDING_SHIM at the top of this module.
        """
        if NEEDS_PADDING_SHIM:
            kwargs.setdefault("padx", self.DEFAULT_PADX)
            kwargs.setdefault("pady", self.DEFAULT_PADY)
        widget.grid_into(parent, **kwargs)

    def build_position_interface(self):
        self.position = Box()
        self.position.grid_into(
            self.right_column, column=0, row=1, sticky="new"
        )
        self.position.widget.configure(padding=(8, 6))

        self.grid_into_with_defaults(
            Label("Position: (0, 0, 0)"), self.position, row=0, column=0, sticky="w"
        )

    def build_map_interface(self):
        self.map_controls = Box(label="Map")
        self.map_controls.grid_into(
            self.right_column, column=0, row=2, sticky="new"
        )
        self.map_controls.widget.configure(padding=(8, 6))

        Label("Image Pixel Dimension:").grid_into(
            self.map_controls,
            row=0,
            column=0,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="w",
        )
        Label("X Dimension:").grid_into(
            self.map_controls,
            row=0,
            column=2,
            pady=4,
            padx=4,
            sticky="e",
        )
        self.x_pixel_entry = IntEntry(
            value=0, width=4
        )
        self.x_pixel_entry.grid_into(
            self.map_controls, row=0, column=3, pady=4, padx=4, sticky="nsw"
        )
        self.map_controller.bind_properties(
            "x_dimension", self.x_pixel_entry, "value_variable"
        )

        Label("Y Dimension:").grid_into(
            self.map_controls,
            row=0,
            column=4,
            pady=4,
            padx=4,
            sticky="e",
        )
        self.y_pixel_entry = IntEntry(
            value=0, width=4
        )
        self.y_pixel_entry.grid_into(
            self.map_controls, row=0, column=5, pady=4, padx=4, sticky="nsw"
        )
        self.map_controller.bind_properties(
            "y_dimension", self.y_pixel_entry, "value_variable"
        )

        Label("Facteur:").grid_into(
            self.map_controls,
            row=1,
            column=0,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="e",
        )

        self.microstep_pixel_entry = FormattedEntry(
            value=float(self.map_controller.microstep_pixel),
            character_width=7,
            format_string="{0:.5f}",
        )
        self.microstep_pixel_entry.grid_into(
            self.map_controls, row=1, column=2, pady=4, padx=4, sticky="ns"
        )
        self.map_controller.bind_properties(
            "microstep_pixel", self.microstep_pixel_entry, "value"
        )

        Label("um/px").grid_into(
            self.map_controls,
            row=1,
            column=3,
            pady=4,
            padx=4,
            sticky="nsw",
        )

        Label("Number of Z Images:").grid_into(
            self.map_controls,
            row=2,
            column=0,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="e",
        )
        self.z_image_number_entry = IntEntry(
            value=self.map_controller.z_image_number, width=5
        )
        self.z_image_number_entry.grid_into(
            self.map_controls, row=2, column=2, pady=4, padx=4, sticky="ns"
        )
        self.map_controller.bind_properties(
            "z_image_number", self.z_image_number_entry, "value_variable"
        )

        Label("Z Step:").grid_into(
            self.map_controls,
            row=2,
            column=3,
            pady=4,
            padx=4,
            sticky="e",
        )

        self.z_range_entry = IntEntry(
            value=self.map_controller.z_range, width=5
        )
        self.z_range_entry.grid_into(
            self.map_controls, row=2, column=4, pady=4, padx=4, sticky="ns"
        )
        self.map_controller.bind_properties(
            "z_range", self.z_range_entry, "value_variable"
        )

        Label("um").grid_into(
            self.map_controls,
            row=2,
            column=5,
            pady=4,
            padx=4,
            sticky="nsw",
        )

        self.apply_upper_left_button = Button(
            "Upper Left Corner",
            user_event_callback=self.user_clicked_saving_position,
        )
        self.apply_upper_left_button.grid_into(
            self.map_controls,
            row=3,
            column=0,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="w",
        )

        self.apply_upper_right_button = Button(
            "Upper Right Corner",
            user_event_callback=self.user_clicked_saving_position,
        )
        self.apply_upper_right_button.grid_into(
            self.map_controls,
            row=3,
            column=2,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="w",
        )

        self.apply_lower_right_button = Button(
            "Lower Right Corner",
            user_event_callback=self.user_clicked_saving_position,
        )
        self.apply_lower_right_button.grid_into(
            self.map_controls,
            row=4,
            column=2,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="w",
        )

        self.apply_lower_left_button = Button(
            "Lower Left Corner",
            user_event_callback=self.user_clicked_saving_position,
        )
        self.apply_lower_left_button.grid_into(
            self.map_controls,
            row=4,
            column=0,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="w",
        )

        self.start_map_aquisition = Button(
            "Start Map",
            user_event_callback=self.user_clicked_map_aquisition_image,
        )
        self.start_map_aquisition.grid_into(
            self.map_controls,
            row=3,
            column=4,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="ns",
        )
        self.bind_properties(
            "can_start_map", self.start_map_aquisition, "is_enabled"
        )

        self.clear_map_aquisition = Button(
            "Clear",
            user_event_callback=self.user_clicked_clear,
        )
        self.clear_map_aquisition.grid_into(
            self.map_controls,
            row=4,
            column=4,
            columnspan=2,
            pady=4,
            padx=4,
            sticky="ns",
        )
        self.bind_properties(
            "can_start_map", self.clear_map_aquisition, "is_enabled"
        )

    def build_delay_interface(self):

        self.delay_controls = Box(
            label="Delay", width=370, height=250
        )

        self.delay_controls.grid_into(
            self.window, column=3, row=0, pady=10, padx=10, sticky="nse"
        )
        self.delay_controls.widget.grid_propagate(False)

        Label("Position in encoder steps").grid_into(
            self.delay_controls, row=1, column=0, columnspan=2, pady=4, padx=4, sticky="w"
        )
        Label(self.delay_position).grid_into(
            self.delay_controls, row=1, column=1, columnspan=2, pady=4, padx=4, sticky="e"
        )
        Label("Tunable Wavelenght").grid_into(
            self.delay_controls, row=2, column=0, pady=4, padx=4, sticky="w"
        )
        self.wavelenght_entry = IntEntry(
            value=0, width=5
        )
        self.wavelenght_entry.grid_into(
            self.delay_controls, row=2, column=1, pady=4, padx=4, sticky="e"
        )
        Label("nm").grid_into(
            self.delay_controls, row=2, column=2, pady=4, padx=4, sticky="w"
        )
        Label("Delay/Wavelenght relation:").grid_into(
            self.delay_controls, row=3, column=0, columnspan=2, pady=4, padx=4, sticky="w"
        )
        self.a_equation_entry = FormattedEntry(
            value=self.delay_controller.a_value,
            character_width=6,
            format_string="{0:.3f}",
        )
        self.a_equation_entry.grid_into(
            self.delay_controls, row=3, column=1, pady=4, padx=4, sticky="e"
        )
        self.delay_controller.bind_properties(
            "a_value", self.a_equation_entry, "value"
        )

        Label("x  +").grid_into(
            self.delay_controls, row=3, column=2, pady=4, padx=4, sticky="w"
        )
        self.b_equation_entry = IntEntry(
            value=self.delay_controller.b_value, width=3
        )
        self.b_equation_entry.grid_into(
            self.delay_controls, row=3, column=3, pady=4, padx=4, sticky="w"
        )
        self.delay_controller.bind_properties(
            "b_value", self.b_equation_entry, "value_variable"
        )
        
        self.start_ajustement_placement = Button(
            "Start wavelength Placement",
            user_event_callback=self.user_clicked_ajustement_placement,
        )
        self.start_ajustement_placement.grid_into(
            self.delay_controls,
            row=4,
            column=0,
            columnspan=3,
            pady=4,
            padx=4,
            sticky="ns",
        )

        self.bind_properties(
            "delay_device_is_ready", self.start_ajustement_placement, "is_enabled"
        )
        
        self.start_move_left = Button(
            "Left",
            user_event_callback=self.user_clicked_left_direction,
        )
        self.start_move_left.grid_into(
            self.delay_controls,
            row=5,
            column=0,
            pady=4,
            padx=4,
            sticky="ns",
        )
        self.bind_properties(
            "delay_device_is_ready", self.start_move_left, "is_enabled"
        )

        self.start_move_right = Button(
            "Right",
            user_event_callback=self.user_clicked_right_direction,
        )
        self.start_move_right.grid_into(
            self.delay_controls,
            row=5,
            column=1,
            pady=4,
            padx=4,
            sticky="nsw",
        )

        self.bind_properties(
            "delay_device_is_ready", self.start_move_right, "is_enabled"
        )

        self.start_homing = Button(
            "Homing Placement",
            user_event_callback=self.user_clicked_homing,
        )
        self.start_homing.grid_into(
            self.delay_controls,
            row=6,
            column=0,
            pady=4,
            padx=4,
            sticky="nsw",
        )
        self.bind_properties(
            "delay_device_is_ready", self.start_homing, "is_enabled"
        )

    def user_clicked_ajustement_placement(self, even, button):
        delay_position = self.delay_controller.linear_relation_delays_and_wavelength(self.wavelenght_entry.value) #modifier l'équation de la relation en fct de la nouvelle implémentation
        ActionMove(position=(delay_position,), linear_motion_device=self.delay_device).perform()

    def user_clicked_homing(self, even, button):
        ActionHome(linear_motion_device=self.delay_device).do_perform()

    def user_clicked_left_direction(self, even, button):
        ActionMoveBy(d_position=(5,), linear_motion_device=self.delay_device).do_perform()

    def user_clicked_right_direction(self, even, button):
        ActionMoveBy(d_position=(-5,), linear_motion_device=self.delay_device).do_perform()

    def user_clicked_saving_position(self, even, button):
        corner_label = button.label
        self.map_controller.parameters[
            corner_label
        ] = self.sample_position_device.positionInMicrons()

        if self.map_controller.corners_are_set:
            self.can_start_map = True

    def user_clicked_clear(self, even, button):
        for corner in self.map_controller.parameters:
            self.map_controller.parameters[corner] = None

        self.can_start_map = False

    def user_clicked_map_aquisition_image(self, event, button):
        self.save_map_experience()

    def save_map_experience(self):
        positions = self.map_controller.create_positions_for_map()
        exp = Experiment()

        for position in positions:
            prepare_actions = []
            move = ActionMove(
                position=position,
                linear_motion_device=self.sample_position_device,
            )
            beep1 = ActionSound()
            prepare_actions.extend([move, beep1])

            save_actions = self.save_actions_current_settings(sound_bell=False)

            exp_step = ExperimentStep(
                prepare=prepare_actions,
                perform=save_actions,
                finalize=[ActionSound(ActionSound.MacOSSound.FUNK)],
            )
            exp.add_step(experiment_step=exp_step)

        exp.perform_in_background_thread()


    def user_clicked_configure_button(self, event, button):
        if self.provider is None:
            self.change_provider()

        was_running = self.provider._is_running.value
        if was_running:
            self.stop_capture()

        self.provider.show_config_dialog(title="Configuration")

        if was_running:
            self.start_capture()

    def change_provider(self, configuration={}):
        self.release_provider()

        self.image_queue = MPQueue()

        selected_camera_name = self.camera_popup.value_variable.get()
        CameraType = self.cameras[selected_camera_name]["type"]
        args = self.cameras[selected_camera_name]["args"]
        kwargs = self.cameras[selected_camera_name]["kwargs"]
            
        self.provider = CameraType(queue=self.image_queue, *args, **kwargs)
        if configuration:
            self.provider.update_values(configuration)
        self.provider.start_synchronously()

    def release_provider(self):
        if self.provider is not None:
            self.provider.stop_capture()
            self.provider.terminate()
            self.provider = None
            self.empty_queue(self.image_queue)
            self.image_queue.close()
            self.image_queue.join_thread()
            self.start_stop_button.label = "Start"
            self.is_camera_running = False

    def user_clicked_startstop(self, event, button):
        if self.provider is None:
            self.change_provider()

        if self.provider.is_running:
            self.stop_capture()
        else:
            self.start_capture()

    def start_capture(self, configuration={}):
        if not self.is_camera_running:
            NotificationCenter().post_notification(
                MicroscopeAppNotification.will_start_capture,
                notifying_object=self,
            )

            self.provider.start_capture(configuration)

            NotificationCenter().post_notification(
                MicroscopeAppNotification.did_start_capture,
                notifying_object=self,
            )

    def stop_capture(self):
        if self.is_camera_running:
            NotificationCenter().post_notification(
                MicroscopeAppNotification.will_stop_capture,
                notifying_object=self,
            )

            self.provider.stop_capture()

            NotificationCenter().post_notification(
                MicroscopeAppNotification.did_stop_capture,
                notifying_object=self,
            )

    def empty_queue(self, queue):
        try:
            while queue.get(timeout=0.1) is not None:
                pass
        except Empty:
            pass

    def retrieve_new_image(self):
        img_array = None
        try:
            img_array = self.image_queue.get(timeout=0.001)

            NotificationCenter().post_notification(
                MicroscopeAppNotification.new_image_received,
                self,
                user_info={"img_array": img_array},
            )

            while img_array is not None:
                img_array = self.image_queue.get(timeout=0.001)
        except Empty:
            pass

    def update_preview(self):
        try:
            img_array = self.preview_queue.get_nowait()
            pil_image = PILImage.fromarray(img_array, mode="RGB")
            self.image.pil_image = pil_image
            self.image.resize_image_to_fit_widget()
        except Empty:
            pass

                        
    def microscope_run_loop(self):
        self.retrieve_new_image()
        self.update_preview()
        
        self.after(20, self.microscope_run_loop)

    def delay_return_home(self):
        if self.delay_device.position() != 0:
            ActionHome(linear_motion_device=self.delay_device).perform()
        else:
            pass

    def about(self):
        Dialog.showinfo(
            title="About Microscope",
            message="An application created with myTk",
        )

    def help(self):
        import webbrowser

        webbrowser.open("https://www.dccmlab.ca/")

    def quit(self):
        try:
            self.release_provider()
            self.delay_return_home()
        except Exception as err:
            pass

        self.cleanup()
        super().quit()


if __name__ == "__main__":
    app = MicroscopeApp()
    app.mainloop()
