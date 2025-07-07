from mytk import *
from tkinter import filedialog
import os
import csv
import re
import time
import gc
from collections import deque
import signal
import atexit

import numpy as np
import scipy
import threading as Th
from queue import Queue, Empty
from multiprocessing import RLock, shared_memory

from PIL import Image as PILImage
#from pymicroscope.acquisition.imageprovider import (
#    RemoteImageProvider,)
#from utils.pyroprocess import (
#    PyroProcess,)
from vmscontroller import VMSController
from vmsconfigdialog import VMSConfigDialog
#from pymicroscope.acquisition.imageprovider import DebugImageProvider
from acquisition.imageprovider import DebugImageProvider

#from "" import "controller_setter"

class ImageSharedMemory(Image):
    def __init__(self, lock, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = lock
        self.name = name
        self.shm = shared_memory.SharedMemory(name=self.name)
        self.shape = (480, 640,3)
            
    def update_display(self, image_to_display=None):
        with self.lock:
            self.array = np.ndarray(self.shape, dtype=np.uint8, buffer=self.shm.buf)
            pil_image = PILImage.fromarray(self.array, mode="RGB")
            super().update_display(pil_image)
        self.widget.update_idletasks()
    
class MicroscopeApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.shm_name = "image-shared-memory"
        self.shm = shared_memory.SharedMemory(
            create=True, size=10_000_000, name=self.shm_name
        )
        self.shm_lock = RLock()
        self.shape = (480, 640, 3)
        
        self.provider_type = DebugImageProvider
        self.provider = None
        
        self.vms_controller = VMSController()
        try:
            self.vms_controller.initialize()
        except Exception as err:
            pass # vms_controller.is_accessible == False

        self.app_setup()
        self.build_interface()
        self.after(100, self.microscope_run_loop)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
    
    def app_setup(self):
        def handle_sigterm(signum, frame):
            print(f"Signal {signum} received")
            self.quit()  # or your full shutdown logic

        # self.window.widget.protocol("WM_DELETE_WINDOW", self.quit)    # for close button
        # self.window.widget.createcommand("exit", self.quit)           # for ⌘+Q / Apple menu
        # self.root.createcommand("exit", self.quit)           # for ⌘+Q / Apple menu

        for s in [signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]:
            signal.signal(s, handle_sigterm)

        # atexit.register(self.cleanup)

        # Define the Tcl callback for the macOS quit event
        def on_mac_quit():
            # This is called when the user clicks "Quit" from the Apple menu or presses ⌘+Q
            self.quit()

        try:
            self.root.createcommand("tk::mac::Quit", on_mac_quit)
        except TclError:
            pass  # Not on macOS or already defined

    def cleanup(self):
        print("Cleaning up shared memory...")
        self.image.shm.close()
        try:
            self.shm.unlink()
        except FileNotFoundError as err:
            pass
            
        
    def build_interface(self):
        self.window.widget.title("Microscope")
        
        self.build_start_stop_interface()
        self.build_imageview_interface()
        self.build_control_interface()
        self.build_setter_interface()

    def build_imageview_interface(self):
        self.image = ImageSharedMemory(lock=self.shm_lock, name=self.shm_name)
        self.image.grid_into(self.window, row=0, column=0, rowspan=5, pady=30, padx=20, sticky="nw")
    
    def build_start_stop_interface(self):
        self.save_controls = Box(label="Save", width=400, height=200)
        self.save_controls.grid_into(
            self.window, column=1, row=0, pady=10, padx=10, sticky="nse"
        )
        self.save_controls.widget.grid_propagate(False)

        self.start_stop_button = Button("Start", user_event_callback=self.user_clicked_startstop)
        self.start_stop_button.grid_into(self.save_controls, row=0, column=0, pady=10, padx=10,)
        self.save_button = Button("Save …")
        self.save_button.grid_into(self.save_controls, row=0, column=1, pady=10, padx=10,)

        Label("Images to average: ").grid_into(self.save_controls, row=2, column=0, pady=10, padx=10,)

        self.number_of_images_average = IntEntry(value=30, width=5)
        self.number_of_images_average.grid_into(self.save_controls, row=2, column=1, pady=10, padx=10,)
                
    def build_control_interface(self):
        self.window.widget.grid_columnconfigure(0, weight=1)
        self.window.widget.grid_columnconfigure(1, weight=1)

        self.controls = Box(label="Image Creation Controls", width=400, height=100)

        self.controls.grid_into(
            self.window, column=1, row=1, pady=10, padx=10, sticky="nse"
        )
        self.controls.widget.grid_propagate(False)

        self.controls.widget.grid_rowconfigure(0, weight=1)
        self.controls.widget.grid_rowconfigure(1, weight=1)

        Label("Scan configuration").grid_into(self.controls, row=0, column=0, pady=10, padx=10,sticky="e")
        self.scan_settings = Button("Configure …", user_event_callback=self.user_clicked_configure_button)
        self.scan_settings.grid_into(self.controls, row=0, column=1, pady=10, padx=10,sticky="w")

    def build_setter_interface(self):
        self.setter = Box(label="Setter", width=500, height=200)
        self.setter.grid_into(
            self.window, column=1, row=2, pady=10, padx=10, sticky="nse"
        )
        self.setter.widget.grid_propagate(False)

        Label("Setter position").grid_into(self.setter, row=0, column=0, columnspan=2, pady=8, padx=10,sticky="w")
        Label("x :").grid_into(self.setter, row=1, column=0, pady=2, padx=1,sticky="e")
        Label(0).grid_into(self.setter, row=1, column=1, pady=2, padx=2,sticky="w")
        Label("y :").grid_into(self.setter, row=1, column=2, pady=2, padx=2,sticky="e")
        Label(0).grid_into(self.setter, row=1, column=3, pady=2, padx=2,sticky="w")
        Label("z :").grid_into(self.setter, row=1, column=4, pady=2, padx=2,sticky="e")
        Label(0).grid_into(self.setter, row=1, column=5, pady=2, padx=2,sticky="w")
        
        Label("Initial configuration").grid_into(self.setter, row=2, column=0, columnspan=2, pady=10, padx=10,sticky="w")
        Label("Upper left corner").grid_into(self.setter, row=3, column=0, columnspan=2, pady=10, padx=10,sticky="w")
        self.apply_upper_left_button = Button(
            "Apply", user_event_callback=None
        ) # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_upper_left_button.grid_into(
            self.setter, row=3, column=2, columnspan=2, pady=2, padx=2, sticky="e"
        )

        Label("Upper right corner").grid_into(self.setter, row=3, column=4, columnspan=2, pady=10, padx=10,sticky="w")
        self.apply_upper_right_button = Button(
            "Apply", user_event_callback=None
        ) # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_upper_right_button.grid_into(
            self.setter, row=3, column=6, columnspan=2, pady=2, padx=2, sticky="e"
        )
        '''
        self.apply_upper_right_button.is_enabled = self.controller_setter.is_accessible #we don't konw now
        '''
        Label("Lower right corner").grid_into(self.setter, row=4, column=4, columnspan=2, pady=10, padx=10,sticky="w")
        self.apply_lower_right_button = Button(
            "Apply", user_event_callback=None
        ) # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_lower_right_button.grid_into(
            self.setter, row=4, column=6, columnspan=2, pady=2, padx=2, sticky="e"
        )

        Label("Lower left corner").grid_into(self.setter, row=4, column=0, columnspan=2, pady=10, padx=10,sticky="w")
        self.apply_lower_left_button = Button(
            "Apply", user_event_callback=None
        ) # want that when the button is push, the first value is memorised and we see the position at the button place
        self.apply_lower_left_button.grid_into(
            self.setter, row=4, column=2, columnspan=2, pady=2, padx=2, sticky="e"
        )
    
    #review the code before continue this section, we don't have that much information
    def button_introducing_position_setter(self, even, button):
        if not self.controller_setter.is_accessible: #we don't konw now
            Dialog.showerror(
                title="Setter controller is not connected or found",
                message="Check that the controller is connected to the computer",
            )
            return
        else:
            return (self.x.value, self.y.value, self.z.value) #to see again
        



    def user_clicked_configure_button(self, event, button):
        # if self.provider is not None:
        #     self.stop_capturing()
        
        diag = VMSConfigDialog(
            vms_controller=self.vms_controller,
            title="Test Window",
            buttons_labels=[Dialog.Replies.Ok, Dialog.Replies.Cancel],
            # auto_click=[Dialog.Replies.Ok, 1000],
        )
        reply = diag.run()
        print({id: entry.value for id, entry in diag.entries.items()})

        # if self.provider is not None:
        #     self.provider.start_capturing()

    def user_clicked_startstop(self, event, button):
        if self.provider is None:
            self.provider = DebugImageProvider()
            self.provider.start_synchronously()
        else:
            self.provider.terminate_synchronously()
            self.provider = None
          
    def new_image(self, pil_image):
        self.image.update_display()
    
    def microscope_run_loop(self):
        self.debug_generate_noise()

        self.after(30, self.microscope_run_loop)
        
    def debug_generate_noise(self):
        array = None
        with self.shm_lock:
            array = np.ndarray(self.shape, dtype=np.uint8, buffer=self.shm.buf)
            array[:] = np.random.randint(0, 256, self.shape, dtype=np.uint8)
        
        self.new_image(array)
        
        
    def about(self):
        showinfo(
            title="About Microscope",
            message="An application created with myTk",
        )

    def help(self):
        webbrowser.open("https://www.dccmlab.ca/")

    def quit(self):
        self.cleanup()
        super().quit()
        

if __name__ == "__main__":
    app = MicroscopeApp()
    app.mainloop()
