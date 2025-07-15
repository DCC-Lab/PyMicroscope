from mytk import *
import signal
from contextlib import suppress
from typing import Tuple, Optional
import math
import numpy as np
import threading as Th
from queue import Queue, Empty, Full
from multiprocessing import RLock, shared_memory, Queue
from tkinter import filedialog
from pathlib import Path
from threading import Thread


from pymicroscope.utils.configurable import (
    ConfigurationDialog,
)
from pymicroscope.savetask import SaveTask

from PIL import Image as PILImage
from pymicroscope.vmscontroller import VMSController
from pymicroscope.vmsconfigdialog import VMSConfigDialog
from pymicroscope.acquisition.imageprovider import DebugImageProvider
from pymicroscope.acquisition.cameraprovider import OpenCVImageProvider
from pymicroscope.sutterconfigdialog import SutterConfigDialog
from typing import Tuple, Optional
from hardwarelibrary.motion import SutterDevice

class MicroscopeApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.image_queue = Queue()
        self.preview_queue = Queue(maxsize=1)
        self.save_queue = None
        self.images_directory = Path("~/Desktop").expanduser()
        self.images_template = "Image-{date}-{time}-{i}.tif"

        self.shape = (480, 640, 3)
        self.provider = None
        self.cameras = {
            "Debug": {
                "type": DebugImageProvider,
                "args": (),
                "kwargs": {"size": self.shape},
            }
        }
        self.is_camera_running = False

        self.vms_controller = VMSController()
        try:
            self.vms_controller.initialize()
        except Exception as err:
            pass  # vms_controller.is_accessible == False
        
        #self.sutter_device = SutterDevice(serialNumber="debug")
        self.sutter_device = SutterDevice()

        try:
            self.sutter_device.initializeDevice()
        except Exception as err:
            pass  # sutter_device.is_accessible == False

        if not self.sutter_device.initializeDevice:  # we don't konw now
            Dialog.showerror(
                title="sutter controller is not connected or found",
                message="Check that the controller is connected to the computer",
            )
            position = self.sutter_device.getPosition()
            self.initial_x_value = position[0]
            self.initial_y_value = position[1]
            self.initial_z_value = position[2]
            self.z_image_number = 1

        else:
            self.initial_x_value = 0
            self.initial_y_value = 0
            self.initial_z_value = 0
            self.z_image_number = 1

        self.parameters: dict[str, Optional[Tuple[int, int, int]]] = {
            "Upper left corner": None,
            "Upper right corner": None,
            "Lower left corner": None,
            "Lower right corner": None,
        }

        self.can_start_map = False

        self.sutter_config_dialog = SutterConfigDialog(self)

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

    def background_get_cameras(self):
        devices = OpenCVImageProvider.available_devices()
        for device in devices:
            self.cameras[f"OpenCV camera #{device}"] = {
                "type": OpenCVImageProvider,
                "args": (),
                "kwargs": {"camera_index": device},
            }

    def cleanup(self):
        if self.preview_queue is not None:
            self.preview_queue.close()
            self.preview_queue.join_thread()
        
        if self.preview_queue is not None:
            self.preview_queue.close()
            self.preview_queue.join_thread()
        pass

    def build_interface(self):
        self.window.widget.title("PyMicroscope")

        self.build_imageview_interface()
        self.build_sutter_interface()
        self.build_cameras_menu()
        self.build_start_stop_interface()
        
    def build_imageview_interface(self):
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

    def build_cameras_menu(self):
        self.background_get_cameras()

    def build_start_stop_interface(self):
        self.save_controls = Box(
            label="Image Acquisition", width=500, height=150
        )

        self.save_controls.grid_into(
            self.window, column=1, row=0, pady=10, padx=10, sticky="nse"
        )
        self.save_controls.widget.grid_propagate(False)

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
        self.change_provider()

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

        self.save_button = Button("Save …", user_event_callback=self.user_clicked_save)
        self.save_button.grid_into(
            self.save_controls,
            row=2,
            column=0,
            pady=10,
            padx=10,
        )
        self.bind_properties("is_camera_running", self.save_button, "is_enabled")
        
        Label("Images to average: ").grid_into(
            self.save_controls, row=2, column=1, pady=10, padx=10, sticky="e"
        )

        self.number_of_images_average = IntEntry(value=30, width=5)
        self.number_of_images_average.grid_into(
            self.save_controls, row=2, column=2, pady=10, padx=10, sticky="w"
        )

        self.choose_directory_button = Button("Directory …", user_event_callback=self.user_clicked_choose_directory)
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

        self.number_of_images_average = IntEntry(value=30, width=5)
        self.number_of_images_average.grid_into(
            self.save_controls, row=2, column=2, pady=10, padx=10, sticky="w"
        )

    def user_clicked_choose_directory(self, button, event):
        self.images_directory = filedialog.askdirectory(title="Select a destination for images:", initialdir=self.images_directory)
        
        if self.images_directory == "":
            self.images_directory = "/tmp"
                        
    def user_clicked_save(self, button, event):
        n_images = self.number_of_images_average.value
        
        task = SaveTask(n_images=n_images, root_dir=self.images_directory, template=self.images_template)
        self.save_queue = task.queue
        
        if True:
            th = Thread(target=task.hook)
            th.start()
        else:  
            task.start()
    
    def user_changed_camera(self, popup, index):
        self.change_provider()
    
    def build_sutter_interface(self):
        self.sutter = Box(label="Position", width=500, height=250)
        self.sutter.grid_into(
            self.window, column=1, row=2, pady=10, padx=10, sticky="nse"
        )
        self.sutter.widget.grid_propagate(False)

        Label("sutter position").grid_into(
            self.sutter,
            row=0,
            column=0,
            columnspan=2,
            pady=8,
            padx=10,
            sticky="w",
        )
        Label("x :").grid_into(
            self.sutter, row=1, column=0, pady=10, padx=10, sticky="e"
        )
        Label(self.initial_x_value).grid_into(
            self.sutter, row=1, column=1, pady=10, padx=10, sticky="w"
        )
        Label("y :").grid_into(
            self.sutter, row=1, column=2, pady=10, padx=10, sticky="e"
        )
        Label(self.initial_y_value).grid_into(
            self.sutter, row=1, column=3, pady=10, padx=10, sticky="w"
        )
        Label("z :").grid_into(
            self.sutter, row=1, column=4, pady=10, padx=10, sticky="e"
        )
        Label(self.initial_z_value).grid_into(
            self.sutter, row=1, column=5, pady=10, padx=10, sticky="w"
        )

        Label("Initial configuration").grid_into(
            self.sutter,
            row=2,
            column=0,
            columnspan=2,
            pady=10,
            padx=10,
            sticky="w",
        )

        Label("Nomber of z image :").grid_into(
            self.sutter,
            row=3,
            column=0,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="e",
        )
        self.z_image_number_entry = IntEntry(value=self.z_image_number, width=5)
        self.z_image_number_entry.grid_into(
            self.sutter, row=3, column=2, pady=2, padx=2, sticky="w"
        )
        self.z_image_number = self.z_image_number_entry.value

        self.apply_upper_left_button = Button(
            "Upper left corner",
            user_event_callback=self.user_clicked_saving_position,
        )  # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_upper_left_button.grid_into(
            self.sutter,
            row=4,
            column=0,
            columnspan=2,
            pady=3,
            padx=2,
            sticky="w",
        )

        self.apply_upper_right_button = Button(
            "Upper right corner",
            user_event_callback=self.user_clicked_saving_position,
        )  # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_upper_right_button.grid_into(
            self.sutter,
            row=4,
            column=2,
            columnspan=2,
            pady=3,
            padx=2,
            sticky="w",
        )

        self.apply_lower_right_button = Button(
            "Lower right corner",
            user_event_callback=self.user_clicked_saving_position,
        )  # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_lower_right_button.grid_into(
            self.sutter,
            row=5,
            column=2,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="w",
        )

        self.apply_lower_left_button = Button(
            "Lower left corner",
            user_event_callback=self.user_clicked_saving_position,
        )  # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_lower_left_button.grid_into(
            self.sutter,
            row=5,
            column=0,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="w",
        )

        self.start_map_aquisition = Button(
            "Start Map",
            user_event_callback=self.user_clicked_aquisition_image,
        )  # want that when the button is push, the first value is memorised and we see the position at the button place
        self.start_map_aquisition.grid_into(
            self.sutter,
            row=4,
            column=5,
            pady=2,
            padx=2,
            sticky="e",
        )
        self.bind_properties(
            "can_start_map", self.start_map_aquisition, "is_enabled"
        )

        self.clear_map_aquisition = Button(
            "Clear",
            user_event_callback=self.user_clicked_saving_position,
        )  # want that when the button is push, the first value is memorised and we see the position at the button place
        self.clear_map_aquisition.grid_into(
            self.sutter,
            row=5,
            column=5,
            pady=2,
            padx=2,
            sticky="e",
        )
        self.bind_properties(
            "can_start_map", self.clear_map_aquisition, "is_enabled"
        )

    def user_clicked_saving_position(self, even, button):
        if button.label == "Clear":
            for p in self.parameters:
                self.parameters[p] = None
                self.can_start_map = False

        else:
            position = (0, 0, 0)
            try:
                position = self.sutter_device.doGetPosition()
            except Exception as err:
                pass

            self.parameters[button.label] = position
            self.start_map_aquisition.is_enabled = all(
                x is not None for x in self.parameters.values()
            )

    def user_clicked_aquisition_image(self, event, button):
        if self.sutter_device.initializeDevice() is not None:
            self.sutter_config_dialog.aquisition_image()
        else:
            raise Exception("No sutter device found")

    def user_clicked_configure_button(self, event, button):
        restart_after = False

        if self.provider._is_running.value:
            self.stop_capture()
            restart_after = True

        properties_description = self.provider.properties_description
        configuration = self.provider.configuration

        diag = ConfigurationDialog(
            title="Configuration",
            properties_description=properties_description,
            configuration=configuration,
        )
        reply = diag.run()

        if restart_after:
            self.start_capture(diag.configuration)

    def change_provider(self, configuration={}):
        self.release_provider()

        if self.image_queue is not None:
            self.image_queue.close()
            self.image_queue.join_thread()
        
        self.image_queue = Queue()
            
        selected_camera_name = self.camera_popup.value_variable.get()
        CameraType = self.cameras[selected_camera_name]["type"]
        args = self.cameras[selected_camera_name]["args"]
        kwargs = self.cameras[selected_camera_name]["kwargs"]
        self.provider = CameraType(
            queue=self.image_queue, configuration=configuration, *args, **kwargs
        )
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
        self.provider.start_capture(configuration)
        self.is_camera_running = True
        self.start_stop_button.label = "Stop"

    def stop_capture(self):
        self.provider.stop_capture()
        self.is_camera_running = False
        self.start_stop_button.label = "Start"

    def empty_queue(self, queue):
        try:
            while queue.get(timeout=0.1) is not None:
                pass
        except Empty:
            pass

    def handle_new_image(self):
        img_array = None
        try:
            img_array = self.image_queue.get(timeout=0.001)

            with suppress(Full):
                self.preview_queue.put_nowait(img_array)

            if self.save_queue is not None:
                try:
                    self.save_queue.put_nowait(img_array)
                except Full as err:
                    self.save_queue = None # Task has reference
                    
            while img_array is not None:
                img_array = self.image_queue.get(timeout=0.001)
        except Empty:
            pass

    def update_preview(self):
        try:
            img_array = self.preview_queue.get_nowait()
            pil_image = PILImage.fromarray(img_array, mode="RGB")
            self.image.update_display(pil_image)
        except Empty:
            pass

    def microscope_run_loop(self):
        self.handle_new_image()
        self.update_preview()

        self.after(20, self.microscope_run_loop)

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
        except Exception as err:
            pass

        self.cleanup()
        super().quit()


if __name__ == "__main__":
    app = MicroscopeApp()
    app.mainloop()
