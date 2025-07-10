from mytk import *
from tkinter import filedialog
import os
import csv
import re
import time
import gc
from collections import deque
import signal
from contextlib import suppress

import numpy as np
import scipy
import threading as Th
from queue import Queue, Empty
from multiprocessing import RLock, shared_memory, Queue

from PIL import Image as PILImage
from vmscontroller import VMSController
from vmsconfigdialog import VMSConfigDialog
from acquisition.imageprovider import DebugImageProvider
from hardwarelibrary.motion import SutterDevice
    
class MicroscopeApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.image_queue = Queue()

        self.shape = (480, 640, 3)
        self.provider = None
        
        self.vms_controller = VMSController()
        try:
            self.vms_controller.initialize()
        except Exception as err:
            pass # vms_controller.is_accessible == False

        self.sutter_device = SutterDevice()
        try:
            self.sutter_device.doInitializeDevice()
        except Exception as err:
            pass # sutter_device.is_accessible == False

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

    def cleanup(self):
        pass            
        
    def build_interface(self):
        self.window.widget.title("PyMicroscope")
        
        self.build_start_stop_interface()
        self.build_imageview_interface()
        self.build_control_interface()
        self.build_sutter_interface()

    def build_imageview_interface(self):
        array = np.zeros( self.shape, dtype=np.uint8)
        pil_image = PILImage.fromarray(array, mode="RGB")
        self.image = Image(pil_image=pil_image)
        
        self.image.grid_into(self.window, row=0, column=0, rowspan=5, pady=30, padx=20, sticky="nw")
    
    def build_start_stop_interface(self):
        self.save_controls = Box(label="Image Acquisition", width=500, height=150)
        self.save_controls.grid_into(
            self.window, column=1, row=0, pady=10, padx=10, sticky="nse"
        )
        self.save_controls.widget.grid_propagate(False)

        self.start_stop_button = Button("Start", user_event_callback=self.user_clicked_startstop)
        self.start_stop_button.grid_into(self.save_controls, row=0, column=0, pady=10, padx=10,)

        self.save_button = Button("Save …")
        self.save_button.grid_into(self.save_controls, row=2, column=0, pady=10, padx=10,)
        Label("Images to average: ").grid_into(self.save_controls, row=2, column=1, pady=10, padx=10,)

        self.number_of_images_average = IntEntry(value=30, width=5)
        self.number_of_images_average.grid_into(self.save_controls, row=2, column=2, pady=10, padx=10,)

                
    def build_control_interface(self):
        self.window.widget.grid_columnconfigure(0, weight=1)
        self.window.widget.grid_columnconfigure(1, weight=1)

        self.controls = Box(label="Image Creation Controls", width=500, height=100)

        self.controls.grid_into(
            self.window, column=1, row=1, pady=10, padx=10, sticky="nse"
        )
        self.controls.widget.grid_propagate(False)

        self.controls.widget.grid_rowconfigure(0, weight=1)
        self.controls.widget.grid_rowconfigure(1, weight=1)

        Label("Scan configuration").grid_into(self.controls, row=0, column=0, pady=10, padx=10,sticky="e")
        self.scan_settings = Button("Configure …", user_event_callback=self.user_clicked_configure_button)
        self.scan_settings.grid_into(self.controls, row=0, column=1, pady=10, padx=10,sticky="w")

    def build_sutter_interface(self):
        self.sutter = Box(label="Sutter", width=500, height=200)
        self.sutter.grid_into(
            self.window, column=1, row=2, pady=10, padx=10, sticky="nse"
        )
        self.sutter.widget.grid_propagate(False)

        if not self.sutter_device.doInitializeDevice: #we don't konw now
            Dialog.showerror(
                title="sutter controller is not connected or found",
                message="Check that the controller is connected to the computer",
            )
            position = self.sutter_device.doGetPosition()
            initial_x_value = position[0]
            initial_y_value = position[1]
            initial_z_value = position[2]

        else:
            initial_x_value = 0
            initial_y_value = 0
            initial_z_value = 0

        Label("sutter position").grid_into(self.sutter, row=0, column=0, columnspan=2, pady=8, padx=10,sticky="w")
        Label("x :").grid_into(self.sutter, row=1, column=0, pady=2, padx=1,sticky="e")
        Label(initial_x_value).grid_into(self.sutter, row=1, column=1, pady=2, padx=2,sticky="w")
        Label("y :").grid_into(self.sutter, row=1, column=2, pady=2, padx=2,sticky="e")
        Label(initial_y_value).grid_into(self.sutter, row=1, column=3, pady=2, padx=2,sticky="w")
        Label("z :").grid_into(self.sutter, row=1, column=4, pady=2, padx=2,sticky="e")
        Label(initial_z_value).grid_into(self.sutter, row=1, column=5, pady=2, padx=2,sticky="w")
        
        Label("Initial configuration").grid_into(self.sutter, row=2, column=0, columnspan=2, pady=10, padx=10,sticky="w")
        self.apply_upper_left_button = Button(
        "Upper left corner", user_event_callback=None
        ) # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_upper_left_button.grid_into(
            self.sutter, row=3, column=0, columnspan=2, pady=2, padx=2, sticky="e"
        )

        self.apply_upper_right_button = Button(
        "Upper right corner", user_event_callback=None
        ) # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_upper_right_button.grid_into(
            self.sutter, row=3, column=4, columnspan=2, pady=2, padx=2, sticky="e"
        )

        self.apply_lower_right_button = Button(
        "Lower right corner", user_event_callback=None
        ) # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_lower_right_button.grid_into(
            self.sutter, row=4, column=4, columnspan=2, pady=2, padx=2, sticky="e"
        )

        self.apply_lower_left_button = Button(
        "Lower left corner", user_event_callback=None
        ) # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_lower_left_button.grid_into(
            self.sutter, row=4, column=0, columnspan=2, pady=2, padx=2, sticky="e"
        )
    
    def button_saving_position(self, even, button):
        position = self.sutter_device.doGetPosition()
        parameter = {}
        parameter[button] = position
        return parameter
    
    def ajuste_map_imaging(self):
        parameters = self.button_saving_position
        if len(parameters == 4):
            upper_left_corner = parameters["Upper left corner"]
            upper_right_corner = parameters["Upper right corner"]
            lower_left_corner = parameters["Lower left corner"]
            lower_right_corner = parameters["Lower right corner"]
        else:
            raise ValueError("Some initial parameters are missing")
        

    def user_clicked_configure_button(self, event, button):
        restart_after = False
        if self.provider is not None:
            self.stop_capture()
            restart_after = True
        
        diag = VMSConfigDialog(
            vms_controller=self.vms_controller,
            title="Test Window",
            buttons_labels=[Dialog.Replies.Ok, Dialog.Replies.Cancel],
            # auto_click=[Dialog.Replies.Ok, 1000],
        )
        reply = diag.run()
        print({id: entry.value for id, entry in diag.entries.items()})

        if restart_after:
            self.start_capture()

    def user_clicked_startstop(self, event, button):
        if self.provider is None:
            self.start_capture()
        else:
            self.stop_capture()

    def start_capture(self):
        if self.provider is None:
            self.image_queue = Queue()
            self.provider = DebugImageProvider(queue=self.image_queue)
            self.provider.start_synchronously()
            self.start_stop_button.label = "Stop"
        else:
            raise RuntimeError("The capture is already running")

    def empty_image_queue(self):
        try:
            while self.image_queue.get(timeout=0.1) is not None:
                pass
        except Empty:
            pass
                       
    def stop_capture(self):
        if self.provider is not None:            
            self.provider.terminate()
            self.provider = None
            self.empty_image_queue()
            self.start_stop_button.label = "Start"
        else:
            raise RuntimeError("The capture is not running")
                      
    def handle_new_image(self):
        try:
            img_array = self.image_queue.get_nowait()
            pil_image = PILImage.fromarray(img_array, mode="RGB")
            self.image.update_display(pil_image)
        except Empty:
            return

    def microscope_run_loop(self):
        self.handle_new_image()
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
        # self.empty_image_queue()

        try:
            if self.provider is not None:
                self.stop_capture()
        except Exception as err:
            pass
        
        self.cleanup()
        super().quit()
        

if __name__ == "__main__":
    app = MicroscopeApp()
    app.mainloop()
