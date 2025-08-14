from mytk import *

class VMSConfigDialog(Dialog):
    def __init__(self, vms_controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vms_controller = vms_controller
        
    def populate_widget_body(self):
        self.scan_controls = Box(
            label="Scanning control", width=500, height=200
        )
        self.scan_controls.grid_into(
            self, row=1, column=1, pady=5, padx=10, sticky="nse"
        )

        Label("DAC start").grid_into(
            self.scan_controls, row=0, column=0, pady=5, padx=10, sticky="w"
        )

        if self.vms_controller.is_accessible:
            initial_dac_start = self.vms_controller.dac_start
            initial_dac_increment = self.vms_controller.dac_increment
            initial_lines_per_frame = self.vms_controller.lines_per_frame
            initial_lines_for_vsync = self.vms_controller.lines_for_vsync
            initial_tmr1_reload_value = self.vms_controller.tmr1_reload_value
            initial_polygone_rev_per_min = self.vms_controller.polygone_rev_per_min
            initial_hsync_frequency = self.vms_controller.hsync_frequency
            initial_vsync_frequency = self.vms_controller.vsync_frequency
            initial_pixel_frequency = self.vms_controller.pixel_frequency
        else:
            initial_dac_start = 0
            initial_dac_increment = 0
            initial_lines_per_frame = 0
            initial_lines_for_vsync = 0
            initial_tmr1_reload_value = self.vms_controller.tmr1_reload_value
            initial_polygone_rev_per_min = self.vms_controller.polygone_rev_per_min
            initial_hsync_frequency = self.vms_controller.hsync_frequency
            initial_vsync_frequency = 0
            initial_pixel_frequency = 0

        self.dac_start_entry = IntEntry(value=initial_dac_start, width=6)
        self.dac_start_entry.grid_into(
            self.scan_controls, row=0, column=1, pady=5, padx=10, sticky="w"
        )

        Label("DAC increment").grid_into(
            self.scan_controls, row=1, column=0, pady=5, padx=10, sticky="w"
        )
        self.dac_increment_entry = IntEntry(
            value=initial_dac_increment, width=6
        )
        self.dac_increment_entry.grid_into(
            self.scan_controls, row=1, column=1, pady=5, padx=10, sticky="w"
        )

        Label("Lines per frame").grid_into(
            self.scan_controls, row=2, column=0, pady=5, padx=10, sticky="w"
        )
        self.lines_per_frame_entry = IntEntry(
            value=initial_lines_per_frame, width=6
        )
        self.lines_per_frame_entry.grid_into(
            self.scan_controls, row=2, column=1, pady=5, padx=10, sticky="w"
        )

        Label("Lines for VSYNC").grid_into(
            self.scan_controls, row=3, column=0, pady=5, padx=10, sticky="w"
        )
        self.lines_for_vsync_entry = IntEntry(
            value=initial_lines_for_vsync, width=6
        )
        self.lines_for_vsync_entry.grid_into(
            self.scan_controls, row=3, column=1, pady=5, padx=10, sticky="w"
        )

        Label("TMR1 reload value (for polygone speed control)").grid_into(
            self.scan_controls, row=0, column=2, pady=5, padx=10, sticky="w"
        )
        Label(initial_tmr1_reload_value).grid_into(
            self.scan_controls, row=0, column=3, pady=5, padx=10, sticky="w"
        )

        Label("Polygon Revolutions Per Minute [rpm]").grid_into(
            self.scan_controls, row=1, column=2, pady=5, padx=10, sticky="w"
        )

        Label(initial_polygone_rev_per_min).grid_into(
            self.scan_controls, row=1, column=3, pady=5, padx=10, sticky="w"
        )

        Label("Pixel Frequency [Hz]").grid_into(
            self.scan_controls, row=2, column=2, pady=5, padx=10, sticky="w"
        )
        Label(initial_pixel_frequency).grid_into(
            self.scan_controls, row=2, column=3, pady=5, padx=10, sticky="w"
        )

        Label("HSync Frequency [Hz]").grid_into(
            self.scan_controls, row=3, column=2, pady=5, padx=10, sticky="w"
        )
        Label(initial_hsync_frequency).grid_into(
            self.scan_controls, row=3, column=3, pady=5, padx=10, sticky="w"
        )

        Label("VSync Frequency [Hz]").grid_into(
            self.scan_controls, row=4, column=2, pady=5, padx=10, sticky="w"
        )
        Label(initial_vsync_frequency).grid_into(
            self.scan_controls, row=4, column=3, pady=5, padx=10, sticky="w"
        )


        self.apply_scan_parameters_button = Button(
            "Apply", user_event_callback=self.user_clicked_apply_button
        )
        self.apply_scan_parameters_button.grid_into(
            self.scan_controls, row=5, column=3, pady=5, padx=10, sticky="e"
        )

        if self.vms_controller.is_accessible:
            Label(self.vms_controller.build_info()).grid_into(
                self.scan_controls,
                row=5,
                column=0,
                columnspan=2,
                pady=5,
                padx=10,
                sticky="w",
            )
        else:
            Label("VMS controller serial port is not inaccessible").grid_into(
                self.scan_controls,
                row=5,
                column=0,
                columnspan=2,
                pady=5,
                padx=10,
                sticky="w",
            )

        self.scan_controls.is_enabled = self.vms_controller.is_accessible
        self.dac_start_entry.is_enabled = self.vms_controller.is_accessible
        self.dac_increment_entry.is_enabled = self.vms_controller.is_accessible
        self.lines_per_frame_entry.is_enabled = (
            self.vms_controller.is_accessible
        )
        self.lines_for_vsync_entry.is_enabled = (
            self.vms_controller.is_accessible
        )
        self.apply_scan_parameters_button.is_enabled = self.vms_controller.is_accessible
        
    def user_clicked_apply_button(self, event, button):
        if not self.vms_controller.is_accessible:
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
