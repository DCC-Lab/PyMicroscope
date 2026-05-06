"""Local Tk diagnostic UI for the Epiphan acquisition stack.

Driven by a ``HardwareManager`` (see ``acquisitiondaemon.py``). The window
queries the manager every action, so when the user clicks "Reconnect" any
freshly-opened device shows up immediately. All buttons are no-ops when the
relevant subsystem is None - no NoneType crashes.

Layout: status bar, controls panel (free-form numeric entries + a
preset dropdown loaded from the legacy iPhotonRT plist when available,
otherwise the PDF transcription), and a ``ttk.Notebook`` with R / G / B /
Combined preview tabs.
"""
from __future__ import annotations

import logging
import os
import plistlib
import time
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
from PIL import Image, ImageTk

from pymicroscope.acquisition.epiphan.polygoncontroller import (
    PolygonController,
    TMR1_MIN,
    TMR1_MAX,
    POLYGON_FACES,
)


log = logging.getLogger(__name__)

PREVIEW_INTERVAL_MS = 100  # ~10 Hz; increase if CPU is the bottleneck
PREVIEW_MAX_WIDTH = 800     # downscale very large frames so Tk stays responsive


# ---- Preset loading --------------------------------------------------------

# Hard-coded fallback that mirrors the PDF Fast VGA Modes table. Used when the
# legacy iPhotonRT plist is not on disk.
_PDF_FALLBACK_PRESETS = [
    {"name": "500 x 500 Fast",  "width": 500,  "height": 500,
     "lines_per_frame": 540, "lines_for_vsync": 5,
     "dac_start": 19761, "dac_increment": 48, "polygon_rpm": 28800},
    {"name": "752 x 500 Fast",  "width": 752,  "height": 500,
     "lines_per_frame": 540, "lines_for_vsync": 5,
     "dac_start": 24138, "dac_increment": 32, "polygon_rpm": 28800},
    {"name": "1000 x 500 Fast", "width": 1000, "height": 500,
     "lines_per_frame": 540, "lines_for_vsync": 5,
     "dac_start": 26288, "dac_increment": 24, "polygon_rpm": 28800},
    {"name": "1252 x 500 Fast", "width": 1252, "height": 500,
     "lines_per_frame": 540, "lines_for_vsync": 5,
     "dac_start": 27595, "dac_increment": 19, "polygon_rpm": 28800},
    {"name": "1500 x 500 Fast", "width": 1500, "height": 500,
     "lines_per_frame": 540, "lines_for_vsync": 5,
     "dac_start": 28453, "dac_increment": 16, "polygon_rpm": 28800},
    {"name": "1752 x 500 Fast", "width": 1752, "height": 500,
     "lines_per_frame": 540, "lines_for_vsync": 5,
     "dac_start": 29075, "dac_increment": 14, "polygon_rpm": 28800},
    {"name": "2000 x 500 Fast", "width": 2000, "height": 500,
     "lines_per_frame": 540, "lines_for_vsync": 5,
     "dac_start": 29534, "dac_increment": 12, "polygon_rpm": 28800},
    {"name": "2252 x 500 Fast", "width": 2252, "height": 500,
     "lines_per_frame": 540, "lines_for_vsync": 5,
     "dac_start": 29896, "dac_increment": 11, "polygon_rpm": 28800},
]

_LEGACY_PLIST_CANDIDATES = [
    # Most likely path when running from the repo root on the old Mac.
    "epiphan/iPhotonRT2.5.4erbel47/Contents/Resources/ScanningAcquisitionParameters.plist",
    "../epiphan/iPhotonRT2.5.4erbel47/Contents/Resources/ScanningAcquisitionParameters.plist",
]


def _load_presets() -> list[dict]:
    """Prefer the iPhotonRT plist (canonical); fall back to the PDF transcription."""
    for path in _LEGACY_PLIST_CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                data = plistlib.load(f)
            entries = data.get("scanningAcquisitionParameters", [])
            presets = []
            for e in entries:
                presets.append({
                    "name": e.get("label", f"{e.get('width')}x{e.get('height')}"),
                    "width": int(e["width"]),
                    "height": int(e["height"]),
                    "lines_per_frame": int(e["linesPerFrame"]),
                    "lines_for_vsync": int(e["linesPerVSync"]),
                    "dac_start": int(e["start"]),
                    "dac_increment": int(e["inc"]),
                    "polygon_rpm": int(e["rpm"]),
                })
            if presets:
                log.info("Loaded %d presets from %s", len(presets), path)
                return presets
        except Exception as err:
            log.warning("Failed to parse %s: %s", path, err)
    return list(_PDF_FALLBACK_PRESETS)


VGA_PRESETS = _load_presets()


# ---- Window ----------------------------------------------------------------

class DiagnosticWindow(tk.Tk):
    def __init__(self, manager):
        super().__init__()
        self.title("PyMicroscope - Epiphan diagnostic")
        self.geometry("1024x720")

        self.manager = manager

        self._photos: dict[str, ImageTk.PhotoImage] = {}
        self._last_frame_time: float | None = None
        self._fps = 0.0

        self._build_status_bar()
        self._build_controls()
        self._build_preview()
        self._refresh_status()
        self._reload_from_devices()
        self._schedule_preview()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- service shortcuts (always read fresh from manager) -------------

    @property
    def image_service(self):
        return self.manager.image_service

    @property
    def vms(self):
        return self.manager.vms_service

    @property
    def polygon(self):
        return self.manager.polygon_service

    # ---- layout ---------------------------------------------------------

    def _build_status_bar(self):
        bar = ttk.Frame(self, padding=4)
        bar.pack(side=tk.TOP, fill=tk.X)
        self.var_vms_status = tk.StringVar(value="VMS: ?")
        self.var_polygon_status = tk.StringVar(value="Polygon: ?")
        self.var_epiphan_status = tk.StringVar(value="Epiphan: ?")
        self.var_fps = tk.StringVar(value="FPS: -")
        ttk.Label(bar, textvariable=self.var_vms_status).pack(anchor="w")
        ttk.Label(bar, textvariable=self.var_polygon_status).pack(anchor="w")
        ttk.Label(bar, textvariable=self.var_epiphan_status).pack(anchor="w")
        ttk.Label(bar, textvariable=self.var_fps).pack(anchor="w")
        ttk.Separator(self).pack(side=tk.TOP, fill=tk.X)

    def _build_controls(self):
        ctl = ttk.LabelFrame(self, text="Controls", padding=6)
        ctl.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

        self.var_width = tk.IntVar(value=1000)
        self.var_height = tk.IntVar(value=500)
        self.var_lines_per_frame = tk.IntVar(value=540)
        self.var_lines_vsync = tk.IntVar(value=5)
        self.var_dac_start = tk.IntVar(value=26288)
        self.var_dac_inc = tk.IntVar(value=24)
        self.var_tmr1 = tk.IntVar(value=60327)
        self.var_rpm = tk.StringVar(value="-")

        rows = [
            ("Width [px] (software crop)", self.var_width),
            ("Height [px] (software crop)", self.var_height),
            ("Lines per frame", self.var_lines_per_frame),
            ("VSync lines", self.var_lines_vsync),
            ("DAC start", self.var_dac_start),
            ("DAC increment", self.var_dac_inc),
            ("Polygon TMR1 reload", self.var_tmr1),
        ]
        for r, (label, var) in enumerate(rows):
            ttk.Label(ctl, text=label).grid(row=r, column=0, sticky="w", padx=2, pady=1)
            ttk.Entry(ctl, textvariable=var, width=10).grid(row=r, column=1, sticky="w")

        ttk.Label(ctl, text="Polygon RPM (derived):").grid(row=6, column=2, padx=10, sticky="e")
        ttk.Label(ctl, textvariable=self.var_rpm).grid(row=6, column=3, sticky="w")
        self.var_tmr1.trace_add("write", lambda *_: self._update_rpm_display())
        self._update_rpm_display()

        preset_row = len(rows)
        ttk.Label(ctl, text="VGA preset (loads fields, doesn't apply):").grid(
            row=preset_row, column=0, sticky="w", padx=2, pady=(8, 1)
        )
        self.var_preset = tk.StringVar(value="-")
        names = ["-"] + [p["name"] for p in VGA_PRESETS]
        ttk.OptionMenu(
            ctl, self.var_preset, "-", *names, command=self._on_preset_chosen
        ).grid(row=preset_row, column=1, columnspan=3, sticky="w", pady=(8, 1))

        # Buttons
        btns = ttk.Frame(ctl)
        btns.grid(row=preset_row + 1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(btns, text="Reconnect hardware", command=self._on_reconnect).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Reload from device", command=self._reload_from_devices).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Apply", command=self._on_apply).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Start streaming", command=self._on_start).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Stop streaming", command=self._on_stop).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Enable polygon", command=self._on_enable_polygon).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Disable polygon", command=self._on_disable_polygon).pack(side=tk.LEFT, padx=2)

    def _build_preview(self):
        nb = ttk.Notebook(self)
        nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._tabs: dict[str, tk.Label] = {}
        for ch in ("Combined", "R", "G", "B"):
            frame = ttk.Frame(nb)
            nb.add(frame, text=ch)
            label = tk.Label(frame, background="black")
            label.pack(fill=tk.BOTH, expand=True)
            self._tabs[ch] = label

    # ---- helpers --------------------------------------------------------

    def _update_rpm_display(self):
        try:
            tmr1 = int(self.var_tmr1.get())
        except (tk.TclError, ValueError):
            self.var_rpm.set("-")
            return
        if not (0 < tmr1 < 65535):
            self.var_rpm.set("-")
            return
        rpm = PolygonController.rpm_for_tmr1(tmr1)
        line_rate = rpm / 60 * POLYGON_FACES
        self.var_rpm.set(f"{rpm} RPM ({line_rate:.0f} l/s)")

    def _on_preset_chosen(self, name: str):
        preset = next((p for p in VGA_PRESETS if p["name"] == name), None)
        if preset is None:
            return
        self.var_width.set(preset["width"])
        self.var_height.set(preset["height"])
        self.var_lines_per_frame.set(preset["lines_per_frame"])
        self.var_lines_vsync.set(preset["lines_for_vsync"])
        self.var_dac_start.set(preset["dac_start"])
        self.var_dac_inc.set(preset["dac_increment"])
        self.var_tmr1.set(PolygonController.tmr1_for_rpm(preset["polygon_rpm"]))

    def _refresh_status(self):
        v = self.vms
        if v is not None and v.is_accessible():
            self.var_vms_status.set(v.build_info())
        else:
            self.var_vms_status.set("VMS: not accessible")

        p = self.polygon
        if p is not None and p.is_accessible():
            self.var_polygon_status.set(
                p.build_info()
                + f" | clock={'on' if p.clock_enabled else 'off'}"
            )
        else:
            self.var_polygon_status.set("Polygon: not accessible")

        img = self.image_service
        if img is None:
            self.var_epiphan_status.set("Epiphan: not accessible")
        else:
            info = img.device_info()
            if "error" in info:
                self.var_epiphan_status.set(f"Epiphan: {info['error']}")
            else:
                self.var_epiphan_status.set(
                    f"Epiphan: {info.get('product_name', '?')} "
                    f"SN:{info.get('serial_number', '?')}"
                )

    def _reload_from_devices(self):
        try:
            v = self.vms
            if v is not None and v.is_accessible():
                self.var_lines_per_frame.set(v.lines_per_frame)
                self.var_lines_vsync.set(v.lines_for_vsync)
                self.var_dac_start.set(v.dac_start)
                self.var_dac_inc.set(v.dac_increment)
            p = self.polygon
            if p is not None and p.is_accessible():
                self.var_tmr1.set(p.tmr1_reload)
        except Exception as err:
            messagebox.showwarning("Reload", f"Failed to reload: {err}")
        self._refresh_status()

    # ---- actions --------------------------------------------------------

    def _on_reconnect(self):
        result = self.manager.reconnect()
        details = ", ".join(f"{k}={v}" for k, v in result.items())
        log.info("Reconnect: %s", details)
        self._refresh_status()
        self._reload_from_devices()

    def _on_apply(self):
        try:
            self._apply_atomically()
        except Exception as err:
            messagebox.showerror("Apply", str(err))
            return
        self._refresh_status()

    def _apply_atomically(self):
        # Order: pause polygon -> write VMS -> write TMR1 -> resume polygon
        p = self.polygon
        polygon_was_on = bool(p is not None and p.is_accessible() and p.clock_enabled)
        if p is not None and p.is_accessible() and polygon_was_on:
            p.disable_clock()

        v = self.vms
        if v is not None and v.is_accessible():
            settings = {
                "WRITE_NUMBER_OF_LINES_PER_FRAME": int(self.var_lines_per_frame.get()),
                "WRITE_NUMBER_OF_LINES_FOR_VSYNC": int(self.var_lines_vsync.get()),
                "WRITE_DAC_START": int(self.var_dac_start.get()),
                "WRITE_DAC_INCREMENT": int(self.var_dac_inc.get()),
            }
            v.apply_settings(settings)

        if p is not None and p.is_accessible():
            tmr1 = int(self.var_tmr1.get())
            if not (TMR1_MIN <= tmr1 <= TMR1_MAX):
                raise ValueError(f"TMR1 {tmr1} out of [{TMR1_MIN}, {TMR1_MAX}]")
            p.set_tmr1_reload(tmr1)
            if polygon_was_on:
                p.enable_clock()

    def _on_start(self):
        img = self.image_service
        if img is None:
            messagebox.showwarning(
                "Start streaming",
                "Epiphan device is not accessible. Click 'Reconnect hardware' first.",
            )
            return
        try:
            img.start_streaming()
        except Exception as err:
            messagebox.showerror("Start streaming", str(err))

    def _on_stop(self):
        img = self.image_service
        if img is None:
            return
        try:
            img.stop_streaming()
        except Exception as err:
            messagebox.showerror("Stop streaming", str(err))

    def _on_enable_polygon(self):
        p = self.polygon
        if p is None or not p.is_accessible():
            messagebox.showwarning("Polygon", "Polygon controller not accessible. Reconnect first.")
            return
        try:
            p.enable_clock()
        except Exception as err:
            messagebox.showerror("Polygon", str(err))
        self._refresh_status()

    def _on_disable_polygon(self):
        p = self.polygon
        if p is None or not p.is_accessible():
            return
        try:
            p.disable_clock()
        except Exception as err:
            messagebox.showerror("Polygon", str(err))
        self._refresh_status()

    # ---- preview loop ---------------------------------------------------

    def _schedule_preview(self):
        self.after(PREVIEW_INTERVAL_MS, self._tick_preview)

    def _tick_preview(self):
        try:
            img = self.image_service
            arr = None
            if img is not None and img.is_streaming():
                arr = img.grab_array()
            if arr is not None:
                self._render_frame(arr)
                now = time.time()
                if self._last_frame_time is not None:
                    dt = now - self._last_frame_time
                    if dt > 0:
                        self._fps = 0.8 * self._fps + 0.2 * (1.0 / dt)
                self._last_frame_time = now
                self.var_fps.set(f"FPS: {self._fps:.1f}")
        except Exception as err:
            self.var_fps.set(f"FPS: err ({err})")
        finally:
            self._schedule_preview()

    def _render_frame(self, arr: np.ndarray):
        try:
            target_w = int(self.var_width.get())
            target_h = int(self.var_height.get())
        except (tk.TclError, ValueError):
            target_w, target_h = arr.shape[1], arr.shape[0]
        h, w = arr.shape[:2]
        cw = max(1, min(w, target_w))
        ch = max(1, min(h, target_h))
        cropped = arr[:ch, :cw, :]

        disp = cropped
        if disp.shape[1] > PREVIEW_MAX_WIDTH:
            scale = PREVIEW_MAX_WIDTH / disp.shape[1]
            new_w = PREVIEW_MAX_WIDTH
            new_h = max(1, int(disp.shape[0] * scale))
            pil = Image.fromarray(disp).resize((new_w, new_h), Image.NEAREST)
        else:
            pil = Image.fromarray(disp)

        self._photos["Combined"] = ImageTk.PhotoImage(pil)
        self._tabs["Combined"].configure(image=self._photos["Combined"])

        arr_pil = np.array(pil)
        for idx, ch_name in enumerate(("R", "G", "B")):
            single = np.zeros_like(arr_pil)
            single[..., idx] = arr_pil[..., idx]
            self._photos[ch_name] = ImageTk.PhotoImage(Image.fromarray(single))
            self._tabs[ch_name].configure(image=self._photos[ch_name])

    def _on_close(self):
        try:
            img = self.image_service
            if img is not None:
                img.stop_streaming()
        except Exception:
            pass
        self.destroy()
