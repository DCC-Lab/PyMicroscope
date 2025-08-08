from mytk import *
from mytk import __version__ as mytk_version
from mytk.notificationcenter import NotificationCenter, Notification
import signal
import time
from contextlib import suppress
import numpy as np
from queue import Queue as TQueue, Empty, Full
from multiprocessing import Queue as MPQueue
from tkinter import filedialog
from pathlib import Path
from threading import Thread
from packaging import version

from pymicroscope.utils.configurable import (
    ConfigurationDialog,
)

from PIL import Image as PILImage
from pymicroscope.acquisition.imageprovider import DebugImageProvider, ImageProvider
from pymicroscope.acquisition.cameraprovider import OpenCVImageProvider
from pymicroscope.position_and_mapcontroller import MapController
from pymicroscope.experiment.actions import *
from pymicroscope.experiment.experiments import Experiment, ExperimentStep
from pymicroscope.app_notifications import MicroscopeAppNotification
from pymicroscope.save_history import SaveHistory
from pymicroscope.utils.thread_utils import is_main_thread

from hardwarelibrary.motion import SutterDevice

class MicroscopeApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if version.parse(mytk_version) < version.parse("0.9.12"): 
            self.main_queue:TQueue = TQueue()

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
        self.sample_position_x = 0
        self.sample_position_y = 0
        self.sample_position_z = 0
        self.last_read_position = 0

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
        self.build_position_interface()
        self.build_start_stop_interface()
        self.build_cameras_menu()

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

        self.save_controls = Box(
            label="Image Acquisition", width=510, height=140
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

        self.number_of_images_average = IntEntry(value=30, width=5)
        self.number_of_images_average.grid_into(
            self.save_controls, row=2, column=2, pady=10, padx=10, sticky="w"
        )

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

    def build_position_interface(self):
        # assert is_main_thread()

        self.sample = Box(label="Sample Mapping Parameters", width=510, height=210)
        self.sample.grid_into(
            self.window, column=1, row=2, pady=10, padx=10, sticky="nse"
        )
        self.sample.widget.grid_propagate(False)

        self.position = Box(label="Sample Position", width=480, height=60)
        self.position.grid_into(
            self.sample, row=0, column=0, columnspan=7, pady=10, padx=10, sticky="nsew"
        )
        self.position.widget.grid_propagate(False)
        
        self.sample_pos = Label(f'(x, y, z) : {self.sample_position_x, self.sample_position_y, self.sample_position_z}')
        self.sample_pos.grid_into(
            self.position, row=0, column=0, pady=10, padx=10, sticky="nsew"
        )

        Label("Facteur :").grid_into(
            self.sample,
            row=1,
            column=0,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="nse",
        )

        self.microstep_pixel_entry = IntEntry(
            value=float(self.map_controller.microstep_pixel), width=5
        )
        self.microstep_pixel_entry.grid_into(
            self.sample, row=1, column=2, pady=2, padx=2, sticky="ns"
        )
        self.map_controller.bind_properties(
            "microstep_pixel", self.microstep_pixel_entry, "value_variable"
        )

        Label("um/px").grid_into(
            self.sample,
            row=1,
            column=3,
            pady=2,
            padx=0,
            sticky="nsw",
        )

        Label("Number of z images :").grid_into(
            self.sample,
            row=2,
            column=0,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="nse",
        )
        self.z_image_number_entry = IntEntry(
            value=self.map_controller.z_image_number, width=5
        )
        self.z_image_number_entry.grid_into(
            self.sample, row=2, column=2, pady=2, padx=2, sticky="ns"
        )
        self.map_controller.bind_properties(
            "z_image_number", self.z_image_number_entry, "value_variable"
        )

        Label("z step :").grid_into(
            self.sample,
            row=2,
            column=4,
            pady=2,
            padx=2,
            sticky="nse",
        )

        self.z_range_entry = IntEntry(
            value=self.map_controller.z_range, width=5
        )
        self.z_range_entry.grid_into(
            self.sample, row=2, column=5, pady=2, padx=2, sticky="ns"
        )
        self.map_controller.bind_properties(
            "z_range", self.z_range_entry, "value_variable"
        )

        Label("um").grid_into(
            self.sample,
            row=2,
            column=6,
            pady=2,
            padx=0,
            sticky="nsw",
        )

        self.apply_upper_left_button = Button(
            "Upper left corner",
            user_event_callback=self.user_clicked_saving_position,
        )  # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_upper_left_button.grid_into(
            self.sample,
            row=3,
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
            self.sample,
            row=3,
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
            self.sample,
            row=4,
            column=2,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="w",
        )

        self.apply_lower_left_button = Button(
            "Lower left corner",
            user_event_callback=self.user_clicked_saving_position,
        )
        self.apply_lower_left_button.grid_into(
            self.sample,
            row=4,
            column=0,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="w",
        )

        self.start_map_aquisition = Button(
            "Start Map",
            user_event_callback=self.user_clicked_map_aquisition_image,
        )
        self.start_map_aquisition.grid_into(
            self.sample,
            row=3,
            column=5,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="nsew",
        )
        self.bind_properties(
            "can_start_map", self.start_map_aquisition, "is_enabled"
        )

        self.clear_map_aquisition = Button(
            "Clear",
            user_event_callback=self.user_clicked_clear,
        )
        self.clear_map_aquisition.grid_into(
            self.sample,
            row=4,
            column=5,
            columnspan=2,
            pady=2,
            padx=2,
            sticky="nsew",
        )
        self.bind_properties(
            "can_start_map", self.clear_map_aquisition, "is_enabled"
        )

    def user_clicked_saving_position(self, even, button):
        corner_label = button.label
        self.map_controller.parameters[
            corner_label
        ] = self.sample_position_device.positionInMicrons()

        if all(x is not None for x in self.map_controller.parameters.values()):
            self.can_start_map = True

    def user_clicked_clear(self, even, button):
        value_to_clear = self.map_controller.parameters

        ActionClear(value_to_clear)
        self.can_start_map = None

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

        self.image_queue = MPQueue()

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
            self.image.update_display(pil_image)
        except Empty:
            pass

    def update_sample_position(self):
        # Update the sample position every 0.3 seconds
        if time.time() - self.last_read_position >= 0.3:
            if self.sample_position_device is not None:
                position = self.sample_position_device.positionInMicrons() # threading issue here? might try to send two commands at the same time to the device
                self.sample_position_x, self.sample_position_y, self.sample_position_z = position

            self.sample_pos.value_variable.set(f'(x, y, z) : {self.sample_position_x, self.sample_position_y, self.sample_position_z} um')
        self.last_read_position = time.time()

                        
    def microscope_run_loop(self):
        if version.parse(mytk_version) < version.parse("0.9.12"): 
            self.check_main_queue()
        
        self.retrieve_new_image()
        self.update_preview()
        self.update_sample_position()

        # factor = time.time()-self.last_read_position
        # self.sample_position_device.moveInMicronsTo((5*factor, 5, 5))
        
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

if version.parse(mytk_version) < version.parse("0.9.12"): 

    def schedule_on_main_thread(self, fct, args):
        self.main_queue.put( (fct, args) )

    def check_main_queue(self):
        while not self.main_queue.empty():
            try:
                f, args = self.main_queue.get_nowait()
                f(*args)
            except Exception as e:
                print("Unable to call scheduled function {fct} :", e)

    setattr(MicroscopeApp, "schedule_on_main_thread", schedule_on_main_thread)
    setattr(MicroscopeApp, "check_main_queue", check_main_queue)

    
            
    

if __name__ == "__main__":
    app = MicroscopeApp()
    app.mainloop()
