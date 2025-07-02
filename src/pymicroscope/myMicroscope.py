from mytk import *
from tkinter import filedialog
import os
import csv
import re
import time
import gc
from collections import deque

import numpy as np
import scipy
import threading as Th
from queue import Queue, Empty

from PIL import Image as PILImage
#from pymicroscope.acquisition.imageprovider import (
#    RemoteImageProvider,)
#from utils.pyroprocess import (
#    PyroProcess,)
#from pymicroscope.vmscontroller import VMSController
from vmscontroller import VMSController


class MicroscopeApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.vms_controller_is_accessible = True
        self.vms_controller = VMSController()
        try:
            self.vms_controller.initialize()
        except Exception as err:
            self.vms_controller_is_accessible = False

        self.build_interface()

    def build_interface(self):
        self.window.widget.title("Microscope")

        self.camera = VideoView(device=0, auto_start=False, zoom_level=3)
        self.camera.grid_into(
            self.window, row=0, column=0, pady=10, padx=10, sticky="nw"
        )

        self.controls = Box(label="Controls", width=500, height=700)
        self.window.widget.grid_columnconfigure(0, weight=1)
        self.window.widget.grid_columnconfigure(1, weight=1)

        self.controls.grid_into(
            self.window, column=1, row=0, pady=10, padx=10, sticky="nsew"
        )
        self.controls.widget.grid_rowconfigure(0, weight=1)
        self.controls.widget.grid_rowconfigure(1, weight=1)

        self.exposure_time_label = Label("Exposure:")
        self.exposure_time_label.grid_into(
            self.controls, column=0, row=3, pady=5, padx=5, sticky="e"
        )
        self.exposure_time_slider = Slider()
        self.exposure_time_slider.grid_into(
            self.controls, column=1, row=3, pady=5, padx=10, sticky="nw"
        )

        self.gain_label = Label("Gain:")
        self.gain_label.grid_into(
            self.controls, column=0, row=4, pady=5, padx=5, sticky="e"
        )
        self.gain_slider = Slider()
        self.gain_slider.grid_into(
            self.controls, column=1, row=4, pady=5, padx=10, sticky="nw"
        )

        self.popup_label = Label("Camera:")
        self.popup_label.grid_into(
            self.controls, column=0, row=2, pady=5, padx=10, sticky="e"
        )

        self.zoomlevel_label = Label("Zoom level:")
        self.zoomlevel_label.grid_into(
            self.controls, column=0, row=6, pady=5, padx=10, sticky="e"
        )
        self.zoom_level_control = IntEntry(value=3, width=5, minimum=1)
        self.zoom_level_control.grid_into(
            self.controls, column=1, row=6, pady=5, padx=10, sticky="w"
        )
        self.camera.bind_properties(
            "zoom_level", self.zoom_level_control, "value_variable"
        )

        self.camera.histogram_xyplot = Histogram(figsize=(3.5, 1))
        self.camera.histogram_xyplot.grid_into(
            self.controls,
            column=0,
            columnspan=2,
            row=7,
            pady=5,
            padx=10,
            sticky="w",
        )

        self.popup_camera = self.camera.create_behaviour_popups()
        self.popup_camera.grid_into(
            self.controls, column=1, row=2, pady=5, padx=10, sticky="w"
        )

        self.scan_controls = Box(
            label="Scanning control", width=500, height=200
        )
        self.scan_controls.grid_into(
            self.window, row=1, column=1, pady=10, padx=10, sticky="nsew"
        )

        Label("DAC start").grid_into(
            self.scan_controls, row=0, column=0, pady=10, padx=10, sticky="w"
        )

        if self.vms_controller_is_accessible:
            initial_dac_start = self.vms_controller.dac_start
            initial_dac_increment = self.vms_controller.dac_increment
            initial_lines_per_frame = self.vms_controller.lines_per_frame
            initial_lines_for_vsync = self.vms_controller.lines_for_vsync
        else:
            initial_dac_start = 0
            initial_dac_increment = 0
            initial_lines_per_frame = 0
            initial_lines_for_vsync = 0

        self.dac_start_entry = IntEntry(value=initial_dac_start, width=6)
        self.dac_start_entry.grid_into(
            self.scan_controls, row=0, column=1, pady=10, padx=10, sticky="w"
        )

        Label("DAC increment").grid_into(
            self.scan_controls, row=1, column=0, pady=10, padx=10, sticky="w"
        )
        self.dac_increment_entry = IntEntry(
            value=initial_dac_increment, width=6
        )
        self.dac_increment_entry.grid_into(
            self.scan_controls, row=1, column=1, pady=10, padx=10, sticky="w"
        )

        Label("Lines per frame").grid_into(
            self.scan_controls, row=2, column=0, pady=10, padx=10, sticky="w"
        )
        self.lines_per_frame_entry = IntEntry(
            value=initial_lines_per_frame, width=6
        )
        self.lines_per_frame_entry.grid_into(
            self.scan_controls, row=2, column=1, pady=10, padx=10, sticky="w"
        )

        Label("Lines for VSYNC").grid_into(
            self.scan_controls, row=3, column=0, pady=10, padx=10, sticky="w"
        )
        self.lines_for_vsync_entry = IntEntry(
            value=initial_lines_for_vsync, width=6
        )
        self.lines_for_vsync_entry.grid_into(
            self.scan_controls, row=3, column=1, pady=10, padx=10, sticky="w"
        )

        self.apply_scan_parameters_button = Button(
            "Apply", user_event_callback=self.user_clicked_apply_button
        )
        self.apply_scan_parameters_button.grid_into(
            self.scan_controls, row=5, column=1, pady=10, padx=10, sticky="w"
        )

        if self.vms_controller_is_accessible:
            Label(self.vms_controller.build_info()).grid_into(
                self.scan_controls,
                row=4,
                column=0,
                columnspan=2,
                pady=10,
                padx=10,
                sticky="w",
            )
        else:
            Label("VMS controller serial port is not inaccessible").grid_into(
                self.scan_controls,
                row=4,
                column=0,
                columnspan=2,
                pady=10,
                padx=10,
                sticky="w",
            )

        self.scan_controls.is_enabled = self.vms_controller_is_accessible
        self.dac_start_entry.is_enabled = self.vms_controller_is_accessible
        self.dac_increment_entry.is_enabled = self.vms_controller_is_accessible
        self.lines_per_frame_entry.is_enabled = (
            self.vms_controller_is_accessible
        )
        self.lines_for_vsync_entry.is_enabled = (
            self.vms_controller_is_accessible
        )

        App.app.root.after(20, self.get_latest_image)

    def user_clicked_apply_button(self, event, button):
        if not self.vms_controller_is_accessible:
            Dialog.showerror(
                title="VMS controller is not connected or found",
                message="Check that the controller is connected to the computer",
            )
            return

        parameters = {
            "WRITE_DAC_START": self.dac_start_entry.value,
            "WRITE_DAC_INCREMENT": self.dac_increment_entry.value,
            "WRITE_NUMBER_OF_LINES_PER_FRAME": self.lines_per_frame_entry.value,
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC": self.lines_for_vsync_entry.value,
        }

        is_valid = self.vms_controller.parameters_are_valid(parameters)
        if all([value is None for value in is_valid.values()]):
            self.vms_controller.dac_start = self.dac_start_entry.value
            self.vms_controller.dac_increment = self.dac_increment_entry.value
            self.vms_controller.lines_per_frame = (
                self.lines_per_frame_entry.value
            )
            self.vms_controller.lines_for_vsync = (
                self.lines_for_vsync_entry.value
            )
        else:
            err_message = ""
            for parameter, value in is_valid.items():
                if value is not None:
                    err_message += f" {parameter} must be between {value[0]}  and {value[1]} "

            Dialog.showerror(title="Invalid parameters", message=err_message)

    def get_latest_image(self):
        # provider_proxy = PyroProcess.by_name("ca.dccmlab.imageprovider.debug")
        # img_pack = provider_proxy.get_last_packaged_image()
        # image_array = RemoteImageProvider.image_from_package(img_pack)
        # # pil_image = PILImage.fromarray(image_array)
        # # print(image_array, pil_image)
        # self.camera.update_display(image_array)

        # App.app.root.after(20, self.get_latest_image)
        pass

    def about(self):
        showinfo(
            title="About Microscope",
            message="An application created with myTk",
        )

    def help(self):
        webbrowser.open("https://www.dccmlab.ca/")


if __name__ == "__main__":
    app = MicroscopeApp()
    app.mainloop()
