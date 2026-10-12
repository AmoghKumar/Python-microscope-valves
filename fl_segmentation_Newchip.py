import os
import time
import traceback
from pymmcore_plus import CMMCorePlus
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QScrollArea, QTabWidget, QFileDialog,
    QRadioButton, QFrame, QSpinBox, QLineEdit, QCheckBox, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QInputDialog, QGridLayout, QSizePolicy,
    QGroupBox, QSplitter, QPlainTextEdit
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot, Qt, QThread, QSize
from PyQt5 import QtGui, QtCore, QtWidgets
import serial
import numpy as np
import pandas as pd
import sys
from PIL import Image
import csv
import cv2
from skimage import exposure
from collections import defaultdict
import copy
import tifffile as tiff

# ─────────────────────────────────────────────
#  Hardware constants
# ─────────────────────────────────────────────
Arduino_port      = "COM4"
Arduino_baud_rate = 115200
Arduino_timeout   = 0.1

Relay_port    = 'COM6'
Relay_baudrate = 19200
Relay_timeout  = 0.1


# ─────────────────────────────────────────────
#  Style helpers
# ─────────────────────────────────────────────
BTN_YELLOW = "background-color: #d4a017; color: black; border-radius: 4px; padding: 4px 8px;"


def _pressable_button_style(bg, bg_hover, bg_pressed, fg, light_edge, dark_edge):
    """
    Button style with a raised edge (light top/left, thick dark bottom)
    that inverts while the button is held down: the thick edge moves to
    the top, so the face and label drop 1 px and the button looks pushed
    into the panel, popping back out on release.
    """
    return (
        f"QPushButton {{ background-color: {bg}; color: {fg};"
        f" border-style: solid; border-width: 1px 1px 3px 1px;"
        f" border-color: {light_edge} {dark_edge} {dark_edge} {light_edge};"
        f" border-radius: 4px; padding: 4px 8px; }}"
        f"QPushButton:hover {{ background-color: {bg_hover}; }}"
        f"QPushButton:pressed {{ background-color: {bg_pressed};"
        f" border-width: 3px 1px 1px 1px;"
        f" border-color: {dark_edge} {light_edge} {light_edge} {dark_edge}; }}"
        f"QPushButton:disabled {{ color: #77756f; }}"
    )


# Grey matching the Claude desktop app's dark-mode text box
BTN_GREY  = _pressable_button_style("#30302e", "#3a3a37", "#232321", "#f0efea",
                                    "#5a5a55", "#161615")
BTN_BLACK = _pressable_button_style("#222222", "#2c2c2c", "#181818", "white",
                                    "#4a4a4a", "#0e0e0e")


def _colored_pressable_style(base, fg):
    """_pressable_button_style with hover/pressed/edge shades derived from base."""
    c = QtGui.QColor(base)
    return _pressable_button_style(
        base, c.lighter(115).name(), c.darker(125).name(), fg,
        c.lighter(140).name(), c.darker(250).name())


BTN_RED   = _colored_pressable_style("#bb283a", "white")
BTN_GREEN = _colored_pressable_style("#2ac555", "white")


# Filter turret buttons (tab 1), coloured after each filter's emission:
# filter number -> (button colour, text colour)
FILTER_BUTTON_COLORS = {
    1: ("#3f6fe0", "white"),   # BFP-A      – blue
    2: ("#2f9e4a", "white"),   # FITC-Green – green
    3: ("#b8322a", "white"),   # TexasRed   – red
    4: ("#a8379a", "white"),   # Cy5        – far-red, shown as magenta
    5: ("#e0901e", "black"),   # Cy3        – orange
    6: ("#d8d8d2", "black"),   # DIA        – white transmitted light
}
BTN_PURPLE = "background-color: #6a3db8; color: white; border-radius: 4px; padding: 4px 8px;"
BTN_BLUE   = BTN_GREY   # old name; blue buttons are now grey

LABEL_BOLD = "font-weight: bold; color: #cccccc;"
GROUP_STYLE = """
QGroupBox {
    border: 1px solid #555555;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 4px;
    color: #aaaaaa;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
"""

CONSOLE_LOG_STYLE = """
QPlainTextEdit {
    background-color: #0c0c0c;
    color: #3ddc3d;
    font-family: Consolas, monospace;
    font-size: 11px;
    border: 1px solid #333333;
}
"""

WIDGET_STYLE = """
    QTableWidget, QTableView {
        background-color: #1e1e1e;
        color: #ffffff;
        gridline-color: #444444;
        border: 1px solid #444444;
    }
    QTableWidget::item { color: #ffffff; background-color: #1e1e1e; }
    QTableWidget::item:selected { background-color: #2a82da; color: white; }
    QHeaderView::section {
        background-color: #2d2d2d;
        color: #cccccc;
        border: 1px solid #444444;
        padding: 3px;
    }
    QComboBox {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 3px 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #2d2d2d;
        color: #ffffff;
        selection-background-color: #2a82da;
    }
    QComboBox::drop-down { border: none; }
    QSpinBox, QDoubleSpinBox {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 3px 6px;
    }
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
        background-color: #3a3a3a;
        border: none;
    }
    QLineEdit {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 3px 6px;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background-color: #1e1e1e;
        border: none;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background-color: #555555;
        border-radius: 3px;
        min-height: 20px;
    }
    QCheckBox { color: #cccccc; }
    QLabel { color: #cccccc; }
"""


DARK_PALETTE = {
    "Window":          (53,  53,  53),
    "WindowText":      (255, 255, 255),
    "Base":            (25,  25,  25),
    "AlternateBase":   (53,  53,  53),
    "ToolTipBase":     (255, 255, 255),
    "ToolTipText":     (255, 255, 255),
    "Text":            (255, 255, 255),
    "Button":          (53,  53,  53),
    "ButtonText":      (255, 255, 255),
    "BrightText":      (255, 0,   0),
    "Link":            (42,  130, 218),
    "Highlight":       (42,  130, 218),
    "HighlightedText": (0,   0,   0),
}


def make_dark_palette():
    p = QtGui.QPalette()
    mapping = {
        "Window":          QtGui.QPalette.Window,
        "WindowText":      QtGui.QPalette.WindowText,
        "Base":            QtGui.QPalette.Base,
        "AlternateBase":   QtGui.QPalette.AlternateBase,
        "ToolTipBase":     QtGui.QPalette.ToolTipBase,
        "ToolTipText":     QtGui.QPalette.ToolTipText,
        "Text":            QtGui.QPalette.Text,
        "Button":          QtGui.QPalette.Button,
        "ButtonText":      QtGui.QPalette.ButtonText,
        "BrightText":      QtGui.QPalette.BrightText,
        "Link":            QtGui.QPalette.Link,
        "Highlight":       QtGui.QPalette.Highlight,
        "HighlightedText": QtGui.QPalette.HighlightedText,
    }
    for name, role in mapping.items():
        p.setColor(role, QtGui.QColor(*DARK_PALETTE[name]))
    return p


def group(title, layout, flat=False):
    """Wrap a layout in a styled QGroupBox."""
    box = QGroupBox(title)
    box.setStyleSheet(GROUP_STYLE)
    box.setFlat(flat)
    box.setLayout(layout)
    return box


def hline():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    line.setStyleSheet("color: #444444;")
    return line


def labeled_input(label_text, widget, label_width=None):
    """Return an HBoxLayout with a label + widget."""
    lbl = QLabel(label_text)
    lbl.setStyleSheet("color: #aaaaaa;")
    if label_width:
        lbl.setFixedWidth(label_width)
    row = QHBoxLayout()
    row.addWidget(lbl)
    row.addWidget(widget)
    return row


# ─────────────────────────────────────────────
#  Hardware init
# ─────────────────────────────────────────────
def initialize_arduino(port, baud_rate, timeout):
    try:
        arduino = serial.Serial(port, baud_rate, timeout=timeout)
        time.sleep(2)
        print(f"Connected to {port} at {baud_rate} baud.")
        return arduino
    except serial.SerialException:
        print(f"Error: Could not open serial port {port}.")
        return None

def handshake(arduino):
    if arduino:
        for _ in range(5):
            arduino.write(b"HELLO\n")
            time.sleep(0.5)
            response = arduino.readline().decode('utf-8').strip()
            if response == "READY":
                print("Handshake successful!")
                return True
        print("Handshake failed!")
        return False
    return False

arduino = initialize_arduino(Arduino_port, Arduino_baud_rate, Arduino_timeout)
if arduino and handshake(arduino):
    print("Serial connection established.")
else:
    print("Failed to establish a connection. Exiting.")
    if arduino:
        arduino.close()
    exit()

# Console messages for Arduino commands that switch the voltage
ARDUINO_COMMAND_MESSAGES = {"2": "Voltage ON", "3": "Voltage OFF"}


def send_to_arduino(data):
    arduino.write(f"{data}\n".encode())
    if str(data) in ARDUINO_COMMAND_MESSAGES:
        print(ARDUINO_COMMAND_MESSAGES[str(data)])
    time.sleep(0.1)
    # Most commands get no reply - only print one if the Arduino sends it.
    response = arduino.readline().decode().strip()
    if response:
        print(f"Arduino Response: {response}")

def set_voltage(set_value):
    if str(set_value) == 'High':
        send_to_arduino(5)
    elif str(set_value) == 'Low':
        send_to_arduino(4)

    print(f"Voltage set to: {str(set_value)}")


def init_serial_port(relayport, relay_Baudrate, relay_timeout):
    try:
        obj = serial.Serial(relayport, relay_Baudrate, timeout=relay_timeout)
        obj.write(b'')
        obj.flush()
        obj.write_terminator = b'\r'
        print("Numato relay correctly connected")
        return obj
    except serial.SerialException:
        print("Numato relay NOT correctly connected")
        sys.exit(1)

Numato_device = init_serial_port(Relay_port, Relay_baudrate, Relay_timeout)


# ═══════════════════════════════════════════════════════════════════════════
#  FL droplet segmentation  –  no annotation required
# ═══════════════════════════════════════════════════════════════════════════

def segment_droplet_fl(
    raw_fl: np.ndarray,
    min_component_area: int = 50,
    max_electrode_gap: int = 50,
    min_area_ratio: float = 0.02,
) -> tuple:
    """
    Segment a droplet from a raw uint16 fluorescence image.

    The electrode(s) create dark bands that split the droplet into multiple
    bright fluorescent regions.  Because the electrode bands are identical
    in intensity to the background, thresholding alone cannot fill them.
    Instead we use the size and spatial relationship between bright regions:

      1. Otsu-threshold and collect all components above min_component_area.
      2. Discard any candidate smaller than min_area_ratio of the largest
         component - real electrode-split fragments are a substantial
         fraction of the droplet; stray droplets/debris are not.
      3. Starting from the largest component, greedily keep any remaining
         candidate that is "close and aligned" to the growing kept region
         (small gap on one axis, genuine overlap on the other) - the shape
         you'd expect from a droplet cut by a roughly straight electrode
         band. This chains through multiple electrode gaps while rejecting
         stray droplets that merely happen to sit nearby.
      4. Compute the convex hull over ALL bright pixels from the kept
         components.  This correctly fills the dark electrode bands and
         reconstructs the full droplet shape regardless of how many electrodes
         there are or how much the halves are horizontally offset.
      5. Light morphological closing to smooth the boundary.

    Parameters
    ----------
    raw_fl : np.ndarray uint16
        Raw fluorescence image returned by snap_EPI_image().
    min_component_area : int
        Components smaller than this (px²) are discarded before the
        proximity check (default 50).  Low-contrast fluorescence frames
        can produce hundreds of sub-50 px noise specks scattered across
        the whole frame; since the proximity check only looks at vertical
        gaps, dense noise specks can chain together and blow up the
        convex hull to cover the entire image.  50 clears that noise
        floor while still keeping genuine droplet fragments.
    max_electrode_gap : int
        Maximum gap in pixels, on whichever axis a candidate isn't
        overlapping the growing kept region, for it to still be chained in.
        Electrode bands are typically 25-35 px; 50 gives comfortable
        headroom.
    min_area_ratio : float
        Candidates smaller than this fraction of the largest component's
        area are discarded outright before the proximity check (default
        0.02, i.e. 2%).  This is what actually stops small stray droplets
        or debris: they're typically well under 1% of the main droplet's
        area, while a genuine secondary fragment left by another electrode
        band is a much larger share (~3%+ in practice).  Without this gate,
        a chain of many small-but-not-tiny noise specks can still bootstrap
        itself: each accepted speck grows the bounding box a little,
        making the next speck's gap easier to satisfy.

    Returns
    -------
    mask : np.ndarray bool
        Final cleaned binary mask of the full droplet.
    area_px : int
        Number of True pixels in the mask.
    overlay_bgr : np.ndarray uint8
        BGR image with orange mask overlay and cyan contour for saving.
    """
    # 1. Normalise to uint8 for thresholding
    norm = cv2.normalize(
        raw_fl.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX
    ).astype(np.uint8)

    # 2. Blur before Otsu – low-signal FL frames have enough read noise that
    #    thresholding the raw pixels produces hundreds of sub-threshold-area
    #    noise specks scattered across the whole frame, which then survive
    #    min_component_area and get chained into the hull below. Blurring
    #    smears isolated noise pixels below the Otsu cut while leaving the
    #    droplet's large, spatially coherent bright regions intact.
    blurred = cv2.GaussianBlur(norm, (9, 9), 0)
    _, binary = cv2.threshold(blurred, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3. Collect all components above the noise floor
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    component_areas = [
        (stats[i, cv2.CC_STAT_AREA], i)
        for i in range(1, n_labels)
        if stats[i, cv2.CC_STAT_AREA] >= min_component_area
    ]
    component_areas.sort(reverse=True)

    if not component_areas:
        # No components found – return empty mask
        return np.zeros_like(binary, dtype=bool), 0, cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)

    # 3b. Drop candidates that are too small relative to the largest
    #     component to plausibly be a real electrode-split fragment - this
    #     is what actually keeps small stray droplets/debris out, regardless
    #     of where they sit.
    seed_area = component_areas[0][0]
    min_area = max(min_component_area, min_area_ratio * seed_area)
    component_areas = [component_areas[0]] + [
        (area, i) for area, i in component_areas[1:] if area >= min_area
    ]

    # 4. Greedily keep components that are genuinely part of the same
    #    droplet as the growing kept-component region, chaining through
    #    multiple electrode bands. Seed with the largest component (main
    #    droplet body), then repeatedly absorb any remaining candidate that
    #    is "close and aligned" to the current union bounding box, until
    #    nothing new gets picked up.
    #
    #    "Close and aligned" means: within max_electrode_gap of the region
    #    on one axis AND genuinely overlapping it on the other axis - the
    #    shape you'd expect from a droplet cut by a roughly straight
    #    electrode band. Just checking "gap <= max_electrode_gap on both
    #    axes independently" is not enough: a stray droplet sitting
    #    diagonally offset (e.g. 45px away in x AND 45px away in y) would
    #    still pass despite being ~64px away in a straight line, and each
    #    such false accept grows the bounding box, making the next stray
    #    speck even easier to absorb.
    def _bbox(i):
        left = stats[i, cv2.CC_STAT_LEFT]
        top  = stats[i, cv2.CC_STAT_TOP]
        return (left, top,
                left + stats[i, cv2.CC_STAT_WIDTH],
                top  + stats[i, cv2.CC_STAT_HEIGHT])

    def _close_and_aligned(a, b, max_gap):
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        gap_x = max(0, bx0 - ax1, ax0 - bx1)
        gap_y = max(0, by0 - ay1, ay0 - by1)
        overlap_x = min(ax1, bx1) - max(ax0, bx0)
        overlap_y = min(ay1, by1) - max(ay0, by0)
        close_via_y = gap_y <= max_gap and overlap_x > 0
        close_via_x = gap_x <= max_gap and overlap_y > 0
        return close_via_y or close_via_x

    kept = [component_areas[0]]
    chain_bbox = _bbox(component_areas[0][1])
    remaining = component_areas[1:]

    changed = True
    while changed:
        changed = False
        still_remaining = []
        for area, i in remaining:
            cand_bbox = _bbox(i)
            if _close_and_aligned(chain_bbox, cand_bbox, max_electrode_gap):
                kept.append((area, i))
                chain_bbox = (
                    min(chain_bbox[0], cand_bbox[0]), min(chain_bbox[1], cand_bbox[1]),
                    max(chain_bbox[2], cand_bbox[2]), max(chain_bbox[3], cand_bbox[3]),
                )
                changed = True
            else:
                still_remaining.append((area, i))
        remaining = still_remaining

    # 5. Convex hull over all bright pixels from kept components.
    #    Wrapping the combined point cloud in a convex hull fills the dark
    #    electrode bands and any horizontal offset between halves in one step.
    all_bright = np.zeros_like(binary)
    for _, i in kept:
        all_bright = np.clip(all_bright + (labels == i).astype(np.uint8), 0, 1)

    pts = np.column_stack(np.where(all_bright))[:, ::-1].astype(np.int32)  # (x, y)
    hull = cv2.convexHull(pts)
    hull_mask = np.zeros_like(binary)
    cv2.fillPoly(hull_mask, [hull], 1)

    # 6. Light closing to smooth the boundary
    kernel_s = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    final = cv2.morphologyEx(hull_mask, cv2.MORPH_CLOSE, kernel_s).astype(bool)

    area_px = int(final.sum())

    # 7. BGR overlay for saving as a visual check
    bgr = cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)
    overlay = bgr.copy()
    overlay[final] = (
        overlay[final] * 0.5 + np.array([0, 80, 255]) * 0.5
    ).astype(np.uint8)
    contours_f, _ = cv2.findContours(
        final.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(overlay, contours_f, -1, (0, 255, 255), 2)

    return final, area_px, overlay


# Per-position operating modes for the FL-segmentation timelapse
MODE_UPCONC   = "Upconcentration"
MODE_SYNTH    = "Synthesis"
MODE_MAINTAIN = "Maintain"


def inlet_pair_is_legal(a: int, b: int) -> bool:
    """
    Two inlets can be opened together on the binary multiplexer only if
    they share a group-A valve (V1-V3) or a group-B valve (V4-V6);
    otherwise 4 distinct valves open and 4 inlets flow at once.
    """
    return (a - 1) // 3 == (b - 1) // 3 or (a - 1) % 3 == (b - 1) % 3


def legal_partner_inlets(a: int) -> list:
    return [b for b in range(1, 10) if inlet_pair_is_legal(a, b)]


def droplet_fluorescence(raw_fl: np.ndarray, mask: np.ndarray):
    """
    Background-subtracted droplet fluorescence:
        median(raw_fl inside mask) - median(raw_fl outside mask)

    Returns (fluo, median_inside, median_outside), or None if the mask is
    empty or covers the whole frame.
    """
    if not mask.any() or mask.all():
        return None
    med_in  = float(np.median(raw_fl[mask]))
    med_out = float(np.median(raw_fl[~mask]))
    return med_in - med_out, med_in, med_out


# Trigger a feed when droplet area drops below this fraction of initial
FL_AREA_THRESHOLD = 0.80


Microscope = {}
Microscope['mmc'] = CMMCorePlus.instance()
Microscope['mmc'].loadSystemConfiguration("C:\\MATLAB Microscope\\AmoghMMConfig_Hamamatsu.cfg")


# ─────────────────────────────────────────────
#  Console log (mirrors print() into the UI)
# ─────────────────────────────────────────────
class _LogEmitter(QtCore.QObject):
    message = pyqtSignal(str)


class _StreamToLog:
    """
    Drop-in replacement for sys.stdout/sys.stderr: forwards every write to
    the real stream (so the console/.bat window still shows it) and also
    emits it as a Qt signal so it can be mirrored into the on-screen log
    widgets. Qt auto-queues signal delivery across threads, so this is safe
    to write to from worker QThreads (DropletWorker, VideoThread) as well
    as the main thread.
    """
    def __init__(self, emitter, real_stream):
        self.emitter     = emitter
        self.real_stream = real_stream

    def write(self, text):
        if self.real_stream:
            self.real_stream.write(text)
        if text:
            self.emitter.message.emit(text)

    def flush(self):
        if self.real_stream:
            self.real_stream.flush()


class ExperimentStopped(Exception):
    """Raised inside an experiment run body when the user clicks Stop, so
    the worker's except/finally can tell a clean user-stop apart from a
    real error."""


class _ExperimentBridge(QtCore.QObject):
    """
    GUI-update signals for the handful of widget writes that happen inside
    code also called from a background experiment thread (control_valve,
    all_on_callback, _fl_status, the live_Button reset in
    _stop_live_video). Qt's AutoConnection delivers these synchronously
    when emitter and receiver share a thread (i.e. zero behavior change
    for existing GUI-thread callers like valve-grid button clicks) and
    auto-queues delivery onto the GUI thread otherwise - so the same
    emit-then-slot code path is safe regardless of which thread calls it.
    """
    valve_style_changed = pyqtSignal(int, bool)   # idx, state
    all_valves_reset     = pyqtSignal(bool)        # state applied to every valve
    status_text_changed = pyqtSignal(str, str)    # which label ("fl"/"fl_mode"), text
    live_button_reset   = pyqtSignal()
    error_dialog        = pyqtSignal(str, str)    # title, message


# ─────────────────────────────────────────────
#  Custom toggle button
# ─────────────────────────────────────────────
class QToggleButton(QPushButton):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.setStyleSheet(BTN_RED)


# ─────────────────────────────────────────────
#  Video thread
# ─────────────────────────────────────────────
class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    # Live view runs at a fixed rate, independent of whatever exposure is
    # configured for fluorescent snaps elsewhere in the UI. Exposure must be
    # comfortably under the frame interval to leave headroom for readout.
    LIVE_TARGET_FPS  = 100
    LIVE_EXPOSURE_MS = 8
    LIVE_INTERVAL_MS = 1000.0 / LIVE_TARGET_FPS   # 10 ms

    def __init__(self):
        super().__init__()
        self._run_flag    = True
        self._record_flag = False
        self._lock        = QtCore.QMutex()          # FIX: guards self.out across threads
        self.out          = None
        self.video_directory = "C:/Users/Cell Culture Scope/Downloads/Videos"
        self.video_filename  = self.get_unique_filename(self.video_directory)
        self.fourcc      = cv2.VideoWriter_fourcc(*'MJPG')
        self.fps         = self.LIVE_TARGET_FPS
        self.frame_size  = None
        self.mmc         = Microscope['mmc']
        self.camera      = self.mmc.getCameraDevice()
        self.DIAshutter  = 'TIDiaShutter'
        self.focus       = self.mmc.getFocusDevice()
        self.stage       = self.mmc.getXYStageDevice()
        self.PFS         = self.mmc.getAutoFocusDevice()
        self.EPIshutter  = 'TIEpiShutter'
        self.DIAlamp     = 'TIDiaLamp'
        self.scope       = 'TIScope'
        self.zoom        = 'TINosePiece'
        self.filter      = 'TIFilterBlock1'
        self.lightpath   = 'TILightPath'
        self.PFS_offset  = 'TIPFSOffset'
        self.core        = 'Core'
        self.camerapath  = '2-Left100'
        self.mmc.setProperty(self.camera, "CONVERSION FACTOR COEFF", "0.5")

    def run(self):
        self.mmc.setProperty(self.DIAshutter, 'State', 0)
        self.mmc.setProperty(self.EPIshutter,  'State', 0)
        # setExposure() (not just setProperty) is what actually pushes the
        # value to the camera AND updates MMCore's own cached exposure -
        # using setProperty alone left this camera's live exposure tracking
        # whatever a fluorescent snap had last set via setExposure().
        self.mmc.setExposure(self.camera, self.LIVE_EXPOSURE_MS)
        self.mmc.setProperty(self.core, 'Shutter', self.DIAshutter)
        self.mmc.setProperty(self.lightpath, 'Label', self.camerapath)
        self.mmc.initializeCircularBuffer()
        self.mmc.prepareSequenceAcquisition(self.camera)
        self.mmc.waitForDevice(self.DIAshutter)
        self.mmc.waitForDevice(self.camera)
        # Interval between frames, in ms - this is what actually sets the fps
        # (100 -> 10fps was the previous, unintended cap). LIVE_EXPOSURE_MS
        # must stay below this for the camera to keep up.
        self.mmc.startContinuousSequenceAcquisition(self.LIVE_INTERVAL_MS)
        while self._run_flag:
            # FIX: poll isSequenceRunning() every iteration instead of caching
            # a one-shot bool; catches camera timeout / buffer-overrun recovery
            if not self.mmc.isSequenceRunning():
                print("VideoThread: sequence stopped unexpectedly, exiting run loop")
                break
            if self.mmc.getRemainingImageCount() > 0:
                try:
                    liveimage    = self.mmc.getLastImage()
                    image_width  = self.mmc.getImageWidth()
                    image_height = self.mmc.getImageHeight()
                except Exception as e:
                    print(f"VideoThread: frame grab error – {e}")
                    continue
                self.final_image = self.convert_raw_np(liveimage, image_width, image_height, np.uint16)
                self.change_pixmap_signal.emit(self.final_image)
                # FIX: lock around all access to self.out so stop_recording()
                # called from the main thread cannot release the writer while
                # we are mid-write here in the worker thread
                self._lock.lock()
                try:
                    if self._record_flag:
                        if self.out is None:
                            self.video_filename = self.get_unique_filename(self.video_directory)
                            # FIX: derive frame_size from actual array shape, not
                            # from mmc width/height which can be stale after a
                            # circular-buffer overrun
                            h, w = self.final_image.shape[:2]
                            self.frame_size = (w, h)
                            self.out = cv2.VideoWriter(
                                self.video_filename, self.fourcc, self.fps,
                                self.frame_size, isColor=True)
                            if not self.out.isOpened():
                                print(f"VideoThread: failed to open writer at {self.video_filename}")
                                self.out = None
                        if self.out is not None and self.out.isOpened():
                            frame_rescaled = exposure.rescale_intensity(
                                self.final_image, in_range='image', out_range='uint8').astype(np.uint8)
                            frame_to_save = cv2.cvtColor(frame_rescaled, cv2.COLOR_GRAY2BGR)
                            # FIX: validate frame dimensions before writing to
                            # avoid VideoWriter crash on unexpected buffer size
                            if frame_to_save.shape[:2][::-1] == self.frame_size:
                                try:
                                    self.out.write(frame_to_save)
                                except Exception as e:
                                    print(f"VideoThread: write error – {e}")
                                    self._record_flag = False
                                    self.out.release(); self.out = None
                            else:
                                print(f"VideoThread: frame size mismatch "
                                      f"{frame_to_save.shape[:2][::-1]} vs {self.frame_size}, skipping")
                finally:
                    self._lock.unlock()
            else:
                QtCore.QThread.msleep(5)   # avoid busy-spin when buffer is empty
        self.mmc.stopSequenceAcquisition(self.camera)
        self.mmc.clearCircularBuffer()
        self._lock.lock()
        try:
            if self.out:
                self.out.release(); self.out = None
        finally:
            self._lock.unlock()

    def convert_raw_np(self, raw_img, img_width, img_height, pixel_Type):
        rawImage = np.frombuffer(raw_img, dtype=pixel_Type).reshape((img_height, img_width)).T
        return exposure.rescale_intensity(rawImage)

    def start_recording(self):
        # FIX: set flag under lock so the run loop sees a consistent state
        self._lock.lock()
        self._record_flag = True
        self._lock.unlock()

    def stop_recording(self):
        # FIX: acquire lock before touching self.out to prevent concurrent release
        self._lock.lock()
        try:
            self._record_flag = False
            if self.out:
                self.out.release(); self.out = None
        finally:
            self._lock.unlock()

    def get_unique_filename(self, directory, base="output", ext=".avi"):
        os.makedirs(directory, exist_ok=True)
        i, filename = 1, os.path.join(directory, f"{base}{ext}")
        while os.path.exists(filename):
            filename = os.path.join(directory, f"{base}_{i}{ext}"); i += 1
        return filename

    def stop(self):
        self._lock.lock()
        self._record_flag = False
        if self.out:
            self.out.release(); self.out = None
        self._lock.unlock()
        self._run_flag = False
        self.wait()



# ─────────────────────────────────────────────
#  Droplet worker thread
# ─────────────────────────────────────────────
class DropletWorker(QThread):
    def __init__(self, operation, input_1=None, input_2=None,
                 inlets=None,
                 purge_duration=0, flow_duration=0, drive_duration=0,
                 chemostat_number=4, PWM_duration1=0.05, PWM_duration2=0.05,
                 PWM_totalduration=5):
        super().__init__()
        self.Numato_port       = Numato_device
        self.operation         = operation
        self.input_1           = input_1
        self.input_2           = input_2
        self.inlets            = inlets if inlets is not None else []
        self.chemostat         = chemostat_number
        self.Purge_duration    = purge_duration
        self.Flow_duration     = flow_duration
        self.Drive_duration    = drive_duration
        self.PWM_duration1     = PWM_duration1
        self.PWM_duration2     = PWM_duration2
        self.PWM_totalduration = PWM_totalduration

    def run(self):
        ops = {
            "purge":        lambda: self.purge_inlet(*self.inlets),
            "generate": lambda: self.generate_droplet(*self.inlets),
            "drive":      lambda: self.drive_droplet(self.chemostat),
            "characterize": lambda: self.characterize_droplet(*self.inlets, self.chemostat),
            "wash":       lambda: self.wash_step(self.input_1, self.input_2),
        
        }

        ops.get(self.operation, lambda: print("Invalid operation"))()

    # ── valve helpers ──────────────────────────────────────
    def send_relay_command(self, command):
        if self.Numato_port and self.Numato_port.is_open:
            try:
                self.Numato_port.write(f"{command}\r".encode('utf-8'))
                time.sleep(0.005)
            except serial.SerialException:
                print('Worker thread failed to communicate with device')

    def get_relay_id(self, idx):
        return str(idx) if idx <= 9 else chr(ord('A') + (idx - 10))

    def control_valve(self, idx, state):
        relay_id = self.get_relay_id(idx)
        self.send_relay_command(f"relay {'off' if state else 'on'} {relay_id}")

    # ── operations ────────────────────────────────────────
    def characterize_droplet(self, inlet_1, inlet_2, chemostat_number):
        """
        Dummy run to verify purge / generate / drive timings end-to-end
        without a real experiment: purges both inlets, generates a droplet
        from them, then drives it into the given chemostat.
        """
        self.purge_inlet(inlet_1, inlet_2)        
        send_to_arduino(5)
        send_to_arduino(2)
        '''self.control_valve(11, state=False)        
        self.control_valve(chemostat_number + 11, state=True)
        time.sleep(4)
        self.control_valve(11, state=True)'''
        self.generate_droplet(inlet_1, inlet_2)
        self.drive_droplet(chemostat_number)
        send_to_arduino(3)

    def _inlet_to_valves(self, inlet: int) -> tuple:
        """
        Returns the (group_A_relay_idx, group_B_relay_idx) pair that opens
        the given inlet on the binary multiplexer, as 0-based relay indices
        - the same convention control_valve()/the V-button handlers use,
        where panel label V<n> is relay index n-1 (V1 = relay 0, etc).
        Inlets 1-9, valves V1-V3 (group A, relay idx 0-2) and V4-V6
        (group B, relay idx 3-5).
        """
        if not 1 <= inlet <= 9:
            raise ValueError(f"Inlet must be 1-9, got {inlet}")
        group_a = (inlet - 1) // 3            # 0, 1, or 2  -> V1, V2, V3
        group_b = (inlet - 1) %  3 + 3        # 3, 4, or 5  -> V4, V5, V6
        return group_a, group_b

    def open_inlet(self, inlet: int):
        """
        Open a single inlet on the binary multiplexer.

        Example:
            self.open_inlet(9)   # control_valve(2, False); control_valve(5, False)  (V3, V6)
        """
        a, b = self._inlet_to_valves(inlet)
        self.control_valve(a, state=False)
        self.control_valve(b, state=False)

    def close_inlet(self, inlet: int):
        """
        Close a single inlet on the binary multiplexer.

        Example:
            self.close_inlet(5)   # control_valve(1, True); control_valve(4, True)  (V2, V5)
        """
        a, b = self._inlet_to_valves(inlet)
        self.control_valve(a, state=True)
        self.control_valve(b, state=True)

    def shrink_droplet(self, Chemostat_number):
        self.control_valve(Chemostat_number + 11, state=True)
        time.sleep(self.Shrink_duration)
        self.control_valve(Chemostat_number + 11, state=False)

    def purge_inlet(self, *inlets: int):
        """
        Purge one or more inlets simultaneously.
        Opens only the valve pairs required for the requested inlets,
        purges, then closes them again.

        Example:
            self.purge_inlet(1, 5)   # purge inlets 1 and 5 simultaneously
            self.purge_inlet(3)      # purge inlet 3 alone
        """
        if not inlets:
            return

        # Resolve which valves need to be open for the requested inlets
        valves_to_open = set()
        for inlet in inlets:
            a, b = self._inlet_to_valves(inlet)
            valves_to_open.add(a)
            valves_to_open.add(b)

        # Open the required valves
        self.control_valve(6, state=False)
        for v in valves_to_open:
            self.control_valve(v, state=False)
        
        print("opened valves", valves_to_open)

        # Purge
        time.sleep(self.Purge_duration)

        # Close the valves again
        for v in valves_to_open:
            self.control_valve(v, state=True)
        self.control_valve(6, state=True)
        time.sleep(1)

    def generate_droplet(self, *inlets: int):
        """
        Generate a droplet from one or more inlets.
        Opens the valve pairs for each requested inlet plus the hardcoded
        downstream flow valves (8, 9), flows for Flow_duration, then closes.
        """
        if not inlets:
            return

        valves_to_open = set()
        for inlet in inlets:
            a, b = self._inlet_to_valves(inlet)
            valves_to_open.add(a)
            valves_to_open.add(b)

        self.control_valve(7,  state=True)
        self.control_valve(10, state=True)
      
        for v in valves_to_open:
            self.control_valve(v, state=False)
        print("generated valves", valves_to_open)
        time.sleep(0.1)
        self.control_valve(8,  state=False)   # hardcoded downstream flow valve
        self.control_valve(9,  state=False)   # hardcoded downstream flow valve

        time.sleep(self.Flow_duration)

        self.control_valve(8,  state=True)
        self.control_valve(9,  state=True)
        for v in valves_to_open:
            self.control_valve(v, state=True)
        time.sleep(0.2)


    def drive_droplet(self, Chemostat_number):
        self.control_valve(7, state=False)
        self.control_valve(10, state=False)
        send_to_arduino(5)
        self.control_valve(11, state=False)
        self.control_valve(Chemostat_number + 11, state=True)
        time.sleep(self.Drive_duration)
        send_to_arduino(4)
        self.control_valve(Chemostat_number + 11, state=False)
        self.control_valve(11, state=True)
        self.control_valve(9, state=False)
        time.sleep(3)
        self.control_valve(9, state=True)

    def wash_step(self, input_1, input_2):
        self.control_valve(input_1 + 11, state=False)
        self.control_valve(input_2 + 11, state=False)
        time.sleep(4)
        self.control_valve(input_2 + 11, state=True)
        self.control_valve(7, state=False)
        time.sleep(5)
        self.control_valve(input_1 + 11, state=True)
        self.control_valve(7, state=True)


# ─────────────────────────────────────────────
#  Experiment worker thread (generic)
# ─────────────────────────────────────────────
class ExperimentWorker(QThread):
    """
    Runs a single callable (one of the experiment run-bodies) on
    a background thread so the GUI event loop stays responsive for the
    entire (potentially many-hour) duration. Generic and dumb by design -
    per-experiment cleanup (closing valves/lamp/video to a safe state) lives
    in each run-body's own try/finally, not here, since the safe state
    differs per experiment type.

    self.exc holds the formatted traceback string if the target raised an
    exception other than ExperimentStopped (a clean, user-requested stop),
    so the GUI-thread "finished" slot can tell the two apart and surface a
    real failure without popping a dialog for a normal Stop click.
    """
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args   = args
        self.kwargs = kwargs
        self.exc    = None
        self.stopped = False

    def run(self):
        try:
            self.target(*self.args, **self.kwargs)
        except ExperimentStopped:
            self.stopped = True
            print("Experiment stopped by user.")
        except Exception:
            self.exc = traceback.format_exc()
            print(f"[ERROR] Experiment failed:\n{self.exc}")


# ═══════════════════════════════════════════════════════════
#  MAIN GUI
# ═══════════════════════════════════════════════════════════
class MicroscopeControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_console_log()
        self._setup_experiment_bridge()
        self.Numato_port  = Numato_device
        self.video_thread = None
        self.positions    = []
        self.Buffer_inlet = 9   # default buffer inlet (1-9); updated from UI
        self.selected_exposures = []
        self._experiment_stop_requested = False
        self._exp_worker = None
        self._init_microscope()
        self._build_ui()
        self.setWindowTitle('Microscope Control')
        self.resize(1400, 860)
        self.show()

    # ── experiment GUI-update bridge ───────────────────────
    def _setup_experiment_bridge(self):
        """
        Connect the _ExperimentBridge signals to the slots that actually
        touch widgets. control_valve/_fl_status/_stop_live_video
        emit through self._exp_bridge instead of writing widgets directly,
        so they're safe to call from either the GUI thread (synchronous,
        same-thread delivery) or a background ExperimentWorker thread
        (auto-queued onto the GUI thread).
        """
        self._exp_bridge = _ExperimentBridge()
        self._exp_bridge.valve_style_changed.connect(self._on_valve_style_changed)
        self._exp_bridge.all_valves_reset.connect(self._on_all_valves_reset)
        self._exp_bridge.status_text_changed.connect(self._on_status_text_changed)
        self._exp_bridge.live_button_reset.connect(self._on_live_button_reset)
        self._exp_bridge.error_dialog.connect(self._on_error_dialog)

    @pyqtSlot(int, bool)
    def _on_valve_style_changed(self, idx, state):
        self.controls[idx].setStyleSheet(BTN_GREEN if state else BTN_RED)

    @pyqtSlot(bool)
    def _on_all_valves_reset(self, state):
        style = BTN_GREEN if state else BTN_RED
        for ctrl in self.controls:
            ctrl.setStyleSheet(style)
            ctrl.setChecked(state)

    @pyqtSlot(str, str)
    def _on_status_text_changed(self, which, text):
        label = {
            "fl":      self.fl_status_label,
            "fl_mode": self.fl_mode_label,
        }[which]
        label.setText(text)

    @pyqtSlot()
    def _on_live_button_reset(self):
        if hasattr(self, 'live_Button'):
            self.live_Button.setChecked(False)
            self.live_Button.setStyleSheet(BTN_RED)

    @pyqtSlot(str, str)
    def _on_error_dialog(self, title, message):
        QMessageBox.critical(self, title, message)

    # ── console log ───────────────────────────────────────
    def _setup_console_log(self):
        """
        Redirect stdout/stderr so every print() (and uncaught traceback)
        also gets mirrored into the on-screen log widgets built in tab 1
        and the FL Segmentation tab, in addition to the real console. Installed before
        anything else so early startup prints (_init_microscope, etc.)
        are captured too - the widgets themselves don't exist yet at that
        point, so _append_log just buffers/drops them until _build_ui()
        creates console_log_tab1 / console_log_fl.
        """
        self._log_buffer = ""
        self._log_emitter = _LogEmitter()
        self._log_emitter.message.connect(self._append_log)
        self._real_stdout = sys.stdout
        self._real_stderr = sys.stderr
        sys.stdout = _StreamToLog(self._log_emitter, self._real_stdout)
        sys.stderr = _StreamToLog(self._log_emitter, self._real_stderr)

    def _append_log(self, text):
        self._log_buffer += text
        *complete_lines, self._log_buffer = self._log_buffer.split("\n")
        widgets = [w for w in (getattr(self, "console_log_tab1", None),
                                getattr(self, "console_log_fl", None)) if w is not None]
        for line in complete_lines:
            for widget in widgets:
                widget.appendPlainText(line)

    # ── microscope init ───────────────────────────────────
    def _init_microscope(self):
        self.mmc = Microscope['mmc']
        self.camera     = self.mmc.getCameraDevice()
        self.DIAshutter = self.mmc.getShutterDevice()
        self.focus      = self.mmc.getFocusDevice()
        self.stage      = self.mmc.getXYStageDevice()
        self.PFS        = self.mmc.getAutoFocusDevice()
        self.EPIshutter = 'TIEpiShutter'
        self.DIAlamp    = 'TIDiaLamp'
        self.scope      = 'TIScope'
        self.zoom       = 'TINosePiece'
        self.filter     = 'TIFilterBlock1'
        self.lightpath  = 'TILightPath'
        self.PFS_offset = 'TIPFSOffset'
        self.core       = 'Core'
        self.eyepath    = '1-Eye100'
        self.camerapath = '2-Left100'
        self.zoom4x  = '1-(Achromat) 4x NA 0.10 Dry'
        self.zoom10x = '2-(Achromat) 10x NA 0.25 Dry'
        self.zoom20x = '3-(Achromat) 20x NA 0.40 Dry'
        self.zoom40x = '4-S Plan Fluor 40x NA 0.60 Dry'
        self.zoom60x = '5-Plan Apo 60x NA 1.40 Oil'
        self.zoomempty = '6-Unknown'
        self.filterNames = {1:'1- BFP-A', 2:'2- FITC-Green', 3:'3- TexasRed',
                            4:'4- Cy5',  5:'5- Cy3',  6:'6- DIA'}
        # camera setup
        self.mmc.setProperty(self.camera, 'Sensor Cooler', 'ON')
        self.mmc.setProperty(self.camera, 'Exposure', 20)
        self.mmc.setProperty(self.camera, 'MINIMUM ACQUISITION TIMEOUT', 500)
        self.mmc.setProperty(self.camera, 'Binning', '4x4')
        self.mmc.setProperty(self.camera, 'ScanMode', 1)
        self.mmc.setProperty(self.camera, 'CONVERSION FACTOR COEFF', 0.5)
        self.mmc.setProperty(self.camera, 'PixelType', '16bit')
        self.mmc.setProperty(self.DIAlamp, 'ComputerControl', 'On')
        self.mmc.setProperty(self.DIAlamp, 'Intensity', 3)
        self.mmc.setProperty(self.DIAlamp, 'State', 0)
        self.mmc.setProperty(self.DIAshutter, 'State', 0)
        self.mmc.setProperty(self.EPIshutter,  'State', 0)
        self.mmc.setProperty(self.lightpath, 'Label', self.eyepath)
        os.chdir('C:/Users/Cell Culture Scope/Documents/MATLAB')

    # ══════════════════════════════════════════
    #  UI builder
    # ══════════════════════════════════════════
    def _build_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #aaa; padding: 6px 18px; border-radius: 4px 4px 0 0; }
            QTabBar::tab:selected { background: #555; color: white; }
        """)
        self.setCentralWidget(self.tabs)

        tab1 = QWidget(); self.tabs.addTab(tab1, "Microscope Control")

        fl_widget = QWidget()
        fl_layout = QVBoxLayout(fl_widget)
        self._build_fl_panel(fl_layout)
        self.tabs.addTab(fl_widget, "FL Segmentation")

        self._build_tab1(tab1)

    # ══════════════════════════════════════════
    #  TAB 1 — Microscope Control
    # ══════════════════════════════════════════
    def _build_tab1(self, parent):
        root = QHBoxLayout(parent)
        root.setSpacing(10)
        root.setContentsMargins(10, 10, 10, 10)

        # ── LEFT PANEL ─────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        # -- Illumination group
        illum_grid = QGridLayout()
        illum_grid.setSpacing(6)
        self.dialamponlight = QToggleButton("DIA Lamp")
        self.dialamponlight.clicked.connect(self.DIAlamp_ON)
        self.DIAshutterbutton = QToggleButton("DIA Shutter")
        self.DIAshutterbutton.clicked.connect(self.toggle_DIA_shutter)
        self.EPIshutterbutton = QToggleButton("EPI Shutter")
        self.EPIshutterbutton.clicked.connect(self.toggle_EPI_shutter)
        illum_grid.addWidget(self.dialamponlight,    0, 0)
        illum_grid.addWidget(self.DIAshutterbutton,  0, 1)
        illum_grid.addWidget(self.EPIshutterbutton,  0, 2)
        left.addWidget(group("Illumination", illum_grid))

        # -- Objective + light path
        obj_layout = QHBoxLayout()
        obj_layout.setSpacing(6)
        self.Zoom_list = QComboBox()
        self.Zoom_list.addItems([self.zoom4x, self.zoom10x, self.zoom20x,
                                  self.zoom40x, self.zoom60x, self.zoomempty])
        self.Zoom_list.currentTextChanged.connect(self.Set_zoom)
        self.eyepathlight    = QPushButton("→ Eye")
        self.camerapathlight = QPushButton("→ Camera")
        for btn in (self.eyepathlight, self.camerapathlight):
            btn.setStyleSheet(BTN_GREY)
            btn.clicked.connect(self.PathtoCamera)
        obj_layout.addWidget(self.Zoom_list, 2)
        obj_layout.addWidget(self.camerapathlight, 1)
        obj_layout.addWidget(self.eyepathlight,    1)
        left.addWidget(group("Objective & Light Path", obj_layout))

        # -- Filter buttons
        filter_grid = QGridLayout()
        filter_grid.setSpacing(4)
        for fk, fv in self.filterNames.items():
            btn = QPushButton(fv)
            if fk in FILTER_BUTTON_COLORS:
                btn.setStyleSheet(_colored_pressable_style(*FILTER_BUTTON_COLORS[fk]))
            else:
                btn.setStyleSheet(BTN_GREY)
            btn.clicked.connect(lambda checked, fn=fk: self.change_filter(fn))
            r, c = divmod(fk - 1, 3)
            filter_grid.addWidget(btn, r, c)
        left.addWidget(group("Filters", filter_grid))

        # -- Image viewer (fixed, never collapses)
        self.image_Live = QLabel()
        self.image_Live.setAlignment(Qt.AlignCenter)
        self.image_Live.setStyleSheet("background-color: #111111; border-radius: 4px;")
        self.image_Live.setMinimumSize(340, 260)
        self.image_Live.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_Live.setText("No image loaded")

        # -- Image capture buttons (always above the viewer)
        cap_layout = QHBoxLayout()
        cap_layout.setSpacing(6)
        self.snap_Button   = QPushButton("Snap Image")
        self.live_Button   = QToggleButton("Live Image")
        self.save_Button   = QPushButton("Save Image")
        self.record_button = QPushButton("Start Recording")
        self.record_button.setCheckable(True)
        for btn, style in [(self.snap_Button,   BTN_GREY),
                           (self.live_Button,   BTN_RED),
                           (self.save_Button,   BTN_GREY),
                           (self.record_button, BTN_RED)]:
            btn.setStyleSheet(style)
        self.snap_Button.clicked.connect(self.snap_DIA_image)
        self.live_Button.clicked.connect(self.startstoplive_imaging)
        self.save_Button.clicked.connect(self.save_image)
        self.record_button.clicked.connect(self.handle_record_button)
        for btn in (self.snap_Button, self.live_Button, self.save_Button, self.record_button):
            cap_layout.addWidget(btn)

        # -- Quick fluorescence snap: filter + exposure, then snap
        quick_fl_layout = QHBoxLayout()
        quick_fl_layout.setSpacing(6)
        self.quick_fl_filter = QSpinBox()
        self.quick_fl_filter.setRange(1, 6)
        self.quick_fl_filter.setValue(1)
        self.quick_fl_filter.setToolTip(
            "\n".join(self.filterNames[k] for k in sorted(self.filterNames)))
        self.quick_fl_exposure = QSpinBox()
        self.quick_fl_exposure.setRange(1, 10000)
        self.quick_fl_exposure.setValue(100)
        self.quick_fl_exposure.setSuffix(" ms")
        self.quick_fl_snap_button = QPushButton("Quick Fluorescence Snap")
        self.quick_fl_snap_button.setStyleSheet(BTN_GREY)
        self.quick_fl_snap_button.clicked.connect(self._quick_fl_snap)
        for lbl_text, w in (("Filter:", self.quick_fl_filter),
                            ("Exposure:", self.quick_fl_exposure)):
            lbl = QLabel(lbl_text); lbl.setStyleSheet("color:#aaa;")
            quick_fl_layout.addWidget(lbl)
            quick_fl_layout.addWidget(w)
        quick_fl_layout.addWidget(self.quick_fl_snap_button, 1)

        viewer_layout = QVBoxLayout()
        viewer_layout.setSpacing(4)
        viewer_layout.addLayout(cap_layout)
        viewer_layout.addLayout(quick_fl_layout)
        viewer_layout.addWidget(self.image_Live, 1)
        left.addWidget(group("Image Viewer", viewer_layout), 1)

        ''' # -- Stage controls
        stage_grid = QGridLayout()
        stage_grid.setSpacing(4)
        self.stagefast, self.stagemedium, self.stageslow = 1000, 100, 10
        self.stage_speed = self.stagefast
        self.stagespeedbutton = QComboBox()
        self.stagespeedbutton.addItems([str(self.stageslow), str(self.stagemedium), str(self.stagefast)])
        self.stagespeedbutton.setCurrentIndex(2)
        self.stagespeedbutton.currentTextChanged.connect(self.Set_stage_speed)
        self.Xplus  = QPushButton("X+"); self.Xminus = QPushButton("X−")
        self.Yplus  = QPushButton("Y+"); self.Yminus = QPushButton("Y−")
        self.Zplus  = QPushButton("Z+"); self.Zminus = QPushButton("Z−")
        for btn in (self.Xplus, self.Xminus, self.Yplus, self.Yminus, self.Zplus, self.Zminus):
            btn.setStyleSheet(BTN_GREY)
        self.Xplus.clicked.connect( lambda: self.mmc.setXYPosition(self.mmc.getXPosition(self.stage)+self.stage_speed, self.mmc.getYPosition(self.stage)))
        self.Xminus.clicked.connect(lambda: self.mmc.setXYPosition(self.mmc.getXPosition(self.stage)-self.stage_speed, self.mmc.getYPosition(self.stage)))
        self.Yplus.clicked.connect( lambda: self.mmc.setXYPosition(self.mmc.getXPosition(self.stage), self.mmc.getYPosition(self.stage)+self.stage_speed))
        self.Yminus.clicked.connect(lambda: self.mmc.setXYPosition(self.mmc.getXPosition(self.stage), self.mmc.getYPosition(self.stage)-self.stage_speed))
        self.Zplus.clicked.connect( lambda: self.mmc.setPosition(self.mmc.getPosition()+self.stage_speed))
        self.Zminus.clicked.connect(lambda: self.mmc.setPosition(self.mmc.getPosition()-self.stage_speed))
        speed_lbl = QLabel("Step (µm):"); speed_lbl.setStyleSheet("color:#aaa;")
        stage_grid.addWidget(self.Xplus,  0, 0); stage_grid.addWidget(self.Xminus, 0, 1)
        stage_grid.addWidget(self.Yplus,  1, 0); stage_grid.addWidget(self.Yminus, 1, 1)
        stage_grid.addWidget(self.Zplus,  2, 0); stage_grid.addWidget(self.Zminus, 2, 1)
        stage_grid.addWidget(speed_lbl,   3, 0); stage_grid.addWidget(self.stagespeedbutton, 3, 1)
        left.addWidget(group("Stage", stage_grid)) '''

        # ── RIGHT PANEL ────────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)

        # -- Saved positions
        pos_layout = QVBoxLayout()
        pos_layout.setSpacing(4)
        self.Positions_table = QTableWidget(self)
        self.Positions_table.setRowCount(8)
        self.Positions_table.setColumnCount(3)
        self.Positions_table.setHorizontalHeaderLabels(['X', 'Y', 'Z'])
        self.Positions_table.verticalHeader().setDefaultSectionSize(22)
        self.Positions_table.setMaximumHeight(220)
        #self.Positions_table.horizontalHeader().setStretchLastSection(True)
        pos_btns = QHBoxLayout()
        pos_btns.setSpacing(4)
        self.save_Position_button  = QPushButton("Add Position")
        self.replacePositionButton = QPushButton("Replace")
        self.clearButton           = QPushButton("Clear All")
        self.GoToPositionButton = QPushButton("Go to Position:")
        for btn, style in [(self.save_Position_button,  BTN_GREEN),
                           (self.replacePositionButton, BTN_GREY),
                           (self.GoToPositionButton, BTN_BLACK),
                           (self.clearButton, BTN_RED)]:
            btn.setStyleSheet(style)
        
        self.save_Position_button.clicked.connect(self.save_Position)
        #self.replacePositionButton.clicked.connect(self.replacePosition)
        self.Positions_spinbox  = QSpinBox(); self.Positions_spinbox.setRange(1, 8); self.Positions_spinbox.setValue(1)
        self.replacePositionButton.clicked.connect(lambda: self.replacePosition(self.Positions_spinbox.value()))
        self.GoToPositionButton.clicked.connect(lambda: self.GoToPosition(self.Positions_spinbox.value()))

        self.clearButton.clicked.connect(self.clearPositions)
        for btn in (self.GoToPositionButton, self.Positions_spinbox, self.replacePositionButton, self.save_Position_button, self.clearButton):
            pos_btns.addWidget(btn)
        pos_layout.addLayout(pos_btns)
        pos_layout.addWidget(self.Positions_table)
        right.addWidget(group("Saved Positions (max 8)", pos_layout))

        # -- Valve grid
        valve_grid = QGridLayout()
        valve_grid.setSpacing(4)
        self.controls = []
        for i in range(21):
            btn = QPushButton(f"V{i+1}")
            btn.setCheckable(True)
            btn.setStyleSheet(BTN_RED)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda state, idx=i: self.control_valve(idx, state))
            self.controls.append(btn)
            valve_grid.addWidget(btn, i // 7, i % 7)
        valve_btns = QHBoxLayout()
        self.stop_all_button = QPushButton("Stop All")
        self.stop_all_button.setStyleSheet(BTN_GREY)
        self.all_on_button   = QPushButton("All On")
        self.all_on_button.setStyleSheet(BTN_GREY)
        self.stop_all_button.clicked.connect(self.stop_all_callback)
        self.all_on_button.clicked.connect(self.all_on_callback)
        valve_btns.addWidget(self.stop_all_button)
        valve_btns.addWidget(self.all_on_button)
        full_valve = QVBoxLayout()
        full_valve.setSpacing(4)
        full_valve.addLayout(valve_grid)
        full_valve.addLayout(valve_btns)
        right.addWidget(group("Valve Controls", full_valve))

        # -- Droplet parameters
        dp_grid = QGridLayout()
        dp_grid.setSpacing(4)
        self.purge_duration_Input  = QLineEdit("0")
        self.flow_duration_Input   = QLineEdit("0")
        self.drive_duration_Input  = QLineEdit("0")
        self.inlet_Input           = QLineEdit("1")
        self.inlet1_Input          = QSpinBox()
        self.inlet1_Input.setRange(1, 9)
        self.inlet1_Input.setValue(1)
        self.inlet2_Input          = QSpinBox()
        self.inlet2_Input.setRange(1, 9)
        self.inlet2_Input.setValue(2)
        for row, (lbl, widget) in enumerate([
            ("Purge duration (s):",       self.purge_duration_Input),
            ("Aqueous flow duration (s):", self.flow_duration_Input),
            ("Drive duration (s):",        self.drive_duration_Input),
            ("Chemostat number:",          self.inlet_Input),
        ]):
            l = QLabel(lbl); l.setStyleSheet("color:#aaa;")
            dp_grid.addWidget(l, row, 0)
            dp_grid.addWidget(widget, row, 1)
        inlet1_lbl = QLabel("Inlet 1 (1-9):"); inlet1_lbl.setStyleSheet("color:#aaa;")
        inlet2_lbl = QLabel("Inlet 2 (1-9):"); inlet2_lbl.setStyleSheet("color:#aaa;")
        self.Generate_drop_button = QPushButton("Generate Droplet")
        self.Generate_drop_button.setStyleSheet(BTN_GREEN)
        self.Generate_drop_button.clicked.connect(
            lambda: self.Characterize_Droplet(
                self.inlet1_Input.value(), self.inlet2_Input.value()))

        inlet1_box = QHBoxLayout()
        inlet1_box.addWidget(inlet1_lbl)
        inlet1_box.addWidget(self.inlet1_Input)

        inlet2_box = QHBoxLayout()
        inlet2_box.addWidget(inlet2_lbl)
        inlet2_box.addWidget(self.inlet2_Input)

        inlet_row = QHBoxLayout()
        inlet_row.setSpacing(8)
        inlet_row.addLayout(inlet1_box, 1)
        inlet_row.addLayout(inlet2_box, 1)
        inlet_row.addWidget(self.Generate_drop_button, 1)
        dp_grid.addLayout(inlet_row, 4, 0, 1, 2)
        right.addWidget(group("Droplet Parameters", dp_grid))

        # -- Voltage
        volt_layout = QVBoxLayout(); volt_layout.setSpacing(6)
        volt_row = QHBoxLayout()
        v_lbl = QLabel("Operating voltage (V):"); v_lbl.setStyleSheet("color:#aaa;")
        self.voltagevalues = QComboBox()
        self.voltagevalues.addItems(['High', 'Low'])
        self.voltagevalues.currentTextChanged.connect(set_voltage)
        volt_row.addWidget(v_lbl); volt_row.addWidget(self.voltagevalues)
        self.TurnOnVolts = QPushButton("Voltage Signal")
        self.TurnOnVolts.setCheckable(True)
        self.TurnOnVolts.setStyleSheet(BTN_RED)
        self.TurnOnVolts.clicked.connect(self.alter_Arduino_state)
        volt_layout.addLayout(volt_row)
        volt_layout.addWidget(self.TurnOnVolts)
        right.addWidget(group("Voltage", volt_layout))

        # -- Buffer inlet selector
        buf_layout = QHBoxLayout()
        buf_lbl = QLabel("Buffer inlet (1-9):")
        buf_lbl.setStyleSheet("color:#aaa;")
        self.buffer_inlet_Input = QSpinBox()
        self.buffer_inlet_Input.setRange(1, 9)
        self.buffer_inlet_Input.setValue(9)
        self.buffer_inlet_Input.valueChanged.connect(
            lambda v: setattr(self, "Buffer_inlet", v)
        )
        buf_layout.addWidget(buf_lbl)
        buf_layout.addWidget(self.buffer_inlet_Input)
        right.addWidget(group("Buffer Inlet", buf_layout))

        # -- Console log
        self.console_log_tab1 = QPlainTextEdit()
        self.console_log_tab1.setReadOnly(True)
        self.console_log_tab1.setMaximumBlockCount(2000)
        self.console_log_tab1.setStyleSheet(CONSOLE_LOG_STYLE)
        self.console_log_tab1.setFixedHeight(160)
        log_layout1 = QVBoxLayout()
        log_layout1.addWidget(self.console_log_tab1)
        right.addWidget(group("Console Log", log_layout1))

        right.addStretch()

        root.addLayout(left, 3)
        root.addLayout(right, 2)

    # ══════════════════════════════════════════
    #  Microscope slots
    # ══════════════════════════════════════════
    def startstoplive_imaging(self):
        if self.live_Button.isChecked():
            self.live_Button.setStyleSheet(BTN_GREEN)
            self.video_thread = VideoThread()
            self.video_thread.change_pixmap_signal.connect(self.update_image)
            self.video_thread.start()
        else:
            if self.video_thread:
                self.video_thread.stop()
            self.live_Button.setStyleSheet(BTN_RED)

    def handle_record_button(self):
        if self.record_button.isChecked():
            self.record_button.setText("● Recording")
            self.record_button.setStyleSheet(BTN_GREEN)
            if self.video_thread:
                self.video_thread.start_recording()
        else:
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet(BTN_RED)
            if self.video_thread:
                self.video_thread.stop_recording()

    def _stop_live_video(self):
        """
        Stop the live-imaging thread if it's running, and wait for it to
        fully release the camera (VideoThread.stop() blocks until its run()
        loop calls stopSequenceAcquisition()). A direct snapImage() call, or
        an experiment loop driving the camera itself, crashes mmcore if the
        live thread's continuous sequence acquisition is still active.
        """
        if self.video_thread is not None and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread = None
        # Routed through the bridge (see _ExperimentBridge) since this is
        # called from inside snap_DIA_image/snap_EPI_image, which the
        # experiment methods call heavily from a background thread.
        self._exp_bridge.live_button_reset.emit()

    def snap_DIA_image(self):
        self._stop_live_video()
        self.mmc.setProperty(self.core, 'Shutter', self.DIAshutter)
        self.mmc.waitForSystem()
        self.mmc.setExposure(self.camera, 10)
        self.mmc.setProperty(self.camera, 'CONVERSION FACTOR COEFF', 0.5)
        self.mmc.setProperty(self.lightpath, 'Label', self.camerapath)
        self.mmc.waitForDevice(self.filter)
        self.mmc.waitForSystem()
        self.mmc.setAutoShutter(True)
        self.mmc.snapImage()
        rawImage    = self.mmc.getImage()
        image_width = self.mmc.getImageWidth()
        image_height = self.mmc.getImageHeight()

        rawImage = np.frombuffer(rawImage, dtype=np.uint16).reshape((image_height, image_width)).T
        self.adjusted_image = exposure.rescale_intensity(rawImage)
        raw_data = self.adjusted_image.tobytes()
        self.myQImage = QImage(raw_data, image_width, image_height, QImage.Format_Grayscale16)
        self.image_Live.setPixmap(QPixmap.fromImage(self.myQImage).scaled(
            self.image_Live.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return rawImage      # ← add this one line

    def snap_EPI_image(self, Filter, Exposure_value):
        self._stop_live_video()
        self.mmc.setProperty(self.core, 'Shutter', self.EPIshutter)
        self.mmc.waitForSystem()
        self.change_filter(Filter)
        self.mmc.setExposure(self.camera, Exposure_value)
        self.mmc.setProperty(self.lightpath, 'Label', self.camerapath)
        self.mmc.waitForDevice(self.filter)
        self.mmc.waitForSystem()
        self.mmc.snapImage()
        rawImage = self.mmc.getImage()
        image_width  = self.mmc.getImageWidth()
        image_height = self.mmc.getImageHeight()

        rawImage = np.frombuffer(rawImage, dtype=np.uint16).reshape((image_height, image_width)).T
        self.adjusted_image = exposure.rescale_intensity(rawImage)
        raw_data_rescaled = self.adjusted_image.tobytes()
        self.myQImage = QImage(raw_data_rescaled, image_width, image_height, QImage.Format_Grayscale16)
        self.myQImage.save('C:\\Users\\Cell Culture Scope\\Pictures\\image_Qimage.png')
        self.image_Live.setPixmap(QPixmap.fromImage(self.myQImage).scaled(
            self.image_Live.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return rawImage    # ← raw uint16, not self.adjusted_image

    def _quick_fl_snap(self):
        """Tab 1 Quick Fluorescence Snap: snap_EPI_image with the chosen
        filter/exposure; snap_EPI_image shows the result in image_Live."""
        filt = self.quick_fl_filter.value()
        exp  = self.quick_fl_exposure.value()
        print(f"Quick fluorescence snap: {self.filterNames.get(filt, filt)}, {exp} ms")
        try:
            self.snap_EPI_image(filt, exp)
        except Exception as e:
            QMessageBox.critical(self, "Snap failed",
                                 f"Quick fluorescence snap failed:\n\n{e}")

    def save_image(self):
        if not self.image_Live.pixmap():
            print("No image to save")
            return

        folder = self.directory_input.text().strip()
        if not folder:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder to Save Images")
            if not folder:
                print("No folder selected; image not saved")
                return
            self.directory_input.setText(folder)

        self.image_path = os.path.join(folder, "image.png")
        self.image_Live.pixmap().save(self.image_path)
        print(f"Image saved to {self.image_path}")



    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        h, w = cv_img.shape
        raw_data = cv_img.tobytes()
        qimg = QImage(raw_data, w, h, QImage.Format_Grayscale16)
        self.image_Live.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.image_Live.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def DIAlamp_ON(self):
        if self.dialamponlight.isChecked():
            self.mmc.setProperty(self.DIAlamp, 'State', 1)
            self.dialamponlight.setStyleSheet(BTN_GREEN)
        else:
            self.mmc.setProperty(self.DIAlamp, 'State', 0)
            self.dialamponlight.setStyleSheet(BTN_RED)
    
    def DIALamp_activate(self):
        self.mmc.setProperty(self.DIAlamp, 'State', 1)
        time.sleep(1)

    def DIALamp_deactivate(self):
        self.mmc.setProperty(self.DIAlamp, 'State', 0)
        time.sleep(1)

    def save_Position(self):
        if len(self.positions) < 8:
            self.positions.append(list(self.get_new_position()))
            self.updateTable()
        else:
            QMessageBox.warning(self, 'Limit Reached', 'Cannot save more than 8 positions.')

    def get_new_position(self):
        return (self.mmc.getXPosition(self.stage),
                self.mmc.getYPosition(self.stage),
                self.mmc.getPosition())

    def updateTable(self):
        for row, (x, y, z) in enumerate(self.positions):
            self.Positions_table.setItem(row, 0, QTableWidgetItem(f'{x:.2f}'))
            self.Positions_table.setItem(row, 1, QTableWidgetItem(f'{y:.2f}'))
            self.Positions_table.setItem(row, 2, QTableWidgetItem(f'{z:.2f}'))
        for row in range(len(self.positions), 8):
            for col in range(3):
                self.Positions_table.setItem(row, col, QTableWidgetItem(''))

    def clearPositions(self):
        self.positions = []
        self.updateTable()

    def replacePosition(self, position_number):
        if not self.positions:
            QMessageBox.warning(self, 'No Positions', 'No positions available to replace.')
            return
        
        idx = position_number - 1
        if idx < len(self.positions):
            self.positions[idx] = list(self.get_new_position())
            self.updateTable()
    
    def GoToPosition(self, position_number):
        
        idx = position_number - 1
        if idx < len(self.positions):
            self.mmc.setXYPosition(self.positions[idx][0], self.positions[idx][1])
            self.mmc.setPosition(self.positions[idx][2])
            self.mmc.waitForSystem(); time.sleep(0.5)

    def PathtoCamera(self):
        self.mmc.setProperty(self.lightpath, 'Label', self.camerapath)

    def Set_zoom(self, item):
        self.mmc.setProperty(self.zoom, 'Label', item)

    def change_filter(self, filter_name):
        self.mmc.setProperty(self.filter, 'State', filter_name - 1)

    def Set_stage_speed(self, item):
        self.stage_speed = int(item)

    def toggle_DIA_shutter(self):
        if self.DIAshutterbutton.isChecked():
            self.mmc.setProperty(self.DIAshutter, 'State', 1)
            self.DIAshutterbutton.setStyleSheet(BTN_GREEN)
        else:
            self.mmc.setProperty(self.DIAshutter, 'State', 0)
            self.DIAshutterbutton.setStyleSheet(BTN_RED)

    def toggle_EPI_shutter(self):
        if self.EPIshutterbutton.isChecked():
            self.mmc.setProperty(self.EPIshutter, 'State', 1)
            self.EPIshutterbutton.setStyleSheet(BTN_GREEN)
        else:
            self.mmc.setProperty(self.EPIshutter, 'State', 0)
            self.EPIshutterbutton.setStyleSheet(BTN_RED)

    # ── valve slots ───────────────────────────
    def get_relay_id(self, idx):
        return str(idx) if idx <= 9 else chr(ord('A') + (idx - 10))

    def control_valve(self, idx, state):
        relay_id = self.get_relay_id(idx)
        # Emitted through the bridge (not a direct widget write) so this is
        # safe to call from a background ExperimentWorker thread as well as
        # the GUI thread - see _ExperimentBridge.
        self._exp_bridge.valve_style_changed.emit(idx, state)
        if state:
            self.send_relay_command(f"relay off {relay_id}")
        else:
            self.send_relay_command(f"relay on {relay_id}")

    def _inlet_to_valves(self, inlet: int) -> tuple:
        """
        Returns the (group_A_relay_idx, group_B_relay_idx) pair that opens
        the given inlet on the binary multiplexer, as 0-based relay indices
        - the same convention control_valve()/the V-button handlers use,
        where panel label V<n> is relay index n-1 (V1 = relay 0, etc).
        Inlets 1-9, valves V1-V3 (group A, relay idx 0-2) and V4-V6
        (group B, relay idx 3-5).
        """
        if not 1 <= inlet <= 9:
            raise ValueError(f"Inlet must be 1-9, got {inlet}")
        group_a = (inlet - 1) // 3            # 0, 1, or 2  -> V1, V2, V3
        group_b = (inlet - 1) %  3 + 3        # 3, 4, or 5  -> V4, V5, V6
        return group_a, group_b

    def open_inlet(self, inlet: int):
        """
        Open a single inlet on the binary multiplexer.

        Example:
            self.open_inlet(9)   # control_valve(2, False); control_valve(5, False)  (V3, V6)
        """
        a, b = self._inlet_to_valves(inlet)
        self.control_valve(a, state=False)
        self.control_valve(b, state=False)

    def close_inlet(self, inlet: int):
        """
        Close a single inlet on the binary multiplexer.

        Example:
            self.close_inlet(5)   # control_valve(1, True); control_valve(4, True)  (V2, V5)
        """
        a, b = self._inlet_to_valves(inlet)
        self.control_valve(a, state=True)
        self.control_valve(b, state=True)

    def stop_all_callback(self):
        for i, ctrl in enumerate(self.controls):
            ctrl.setStyleSheet(BTN_RED); ctrl.setChecked(False)
            self.send_relay_command(f"relay on {self.get_relay_id(i)}")
        self.send_relay_command('open all')

    def all_on_callback(self):
        # Widget touches routed through the bridge (not direct) so this is
        # safe to call from a background ExperimentWorker thread as well as
        # the GUI thread - see _safe_shutdown_valves, which calls this at
        # an experiment's safe checkpoint (Stop or an unhandled exception).
        self._exp_bridge.all_valves_reset.emit(True)
        for i in range(len(self.controls)):
            self.send_relay_command(f"relay off {self.get_relay_id(i)}")
        self.send_relay_command('close all')

    def _safe_shutdown_valves(self):
        """
        Best-effort safe-state reset. Called from the finally: block of
        every experiment run-body - on normal completion, on Stop, and on
        any unhandled exception - so there is exactly one cleanup path
        instead of separate "normal tail" vs. "exception" cleanup code
        that could drift out of sync. Turns the DIA lamp off, closes both
        shutters, stops the live-view thread if one is running, and resets
        every valve via all_on_callback() - the same reset closeEvent
        already uses on normal app shutdown - which is itself safe to call
        from either the GUI thread or a background ExperimentWorker thread.
        """
        try:
            self.mmc.setProperty(self.DIAlamp, 'State', 0)
            self.mmc.setProperty(self.EPIshutter, 'State', 0)
            self.mmc.setProperty(self.DIAshutter, 'State', 0)
        except Exception:
            print(f"[WARN] _safe_shutdown_valves: failed to reset lamp/shutters:\n{traceback.format_exc()}")
        if self.video_thread is not None and self.video_thread.isRunning():
            try:
                self.video_thread.stop()
            except Exception:
                print(f"[WARN] _safe_shutdown_valves: failed to stop video thread:\n{traceback.format_exc()}")
            self.video_thread = None
        try:
            self.all_on_callback()
        except Exception:
            print(f"[WARN] _safe_shutdown_valves: failed to reset valves via all_on_callback:\n{traceback.format_exc()}")

    def send_relay_command(self, command):
        if self.Numato_port and self.Numato_port.is_open:
            try:
                self.Numato_port.write(f"{command}\r".encode('utf-8'))
                time.sleep(0.005)
            except serial.SerialException:
                # print (thread-safe via the console log) instead of a
                # direct QMessageBox.critical - this runs continuously from
                # a background ExperimentWorker during an experiment, and a
                # modal dialog is not safe to pop from a non-GUI thread.
                print(f"[ERROR] Failed to communicate with relay device: {command!r}")
                self._exp_bridge.error_dialog.emit(
                    'Error', 'Failed to communicate with the relay device')

    # ── droplet slots ─────────────────────────
    def Characterize_Droplet(self, inlet_1, inlet_2):
        self.Characterize_Droplet_thread = DropletWorker(
            "characterize", inlets=[inlet_1, inlet_2],
            purge_duration   = float(self.purge_duration_Input.text()),
            flow_duration    = float(self.flow_duration_Input.text()),
            drive_duration   = float(self.drive_duration_Input.text()),
            chemostat_number = int(self.inlet_Input.text()))
        self.Characterize_Droplet_thread.start()

    def PWM_droplet(self, input_1=12, input_2=13):
        self.PWM_thread = DropletWorker(
            "PWM", input_1, input_2,
            PWM_duration1    = float(self.PWM_duration1_Input.text()),
            PWM_duration2    = float(self.PWM_duration2_Input.text()),
            PWM_totalduration = float(self.PWM_totalduration_Input.text()))
        self.PWM_thread.start()

    def alter_Arduino_state(self, checked):
        if checked:
            self.TurnOnVolts.setText('Volts ON')
            self.TurnOnVolts.setStyleSheet(BTN_GREEN)
            send_to_arduino(2)
        else:
            self.TurnOnVolts.setText('Voltage Signal')
            self.TurnOnVolts.setStyleSheet(BTN_RED)
            send_to_arduino(3)

    # ── timelapse slots ───────────────────────
    def read_Exposure_values(self):
        self.selected_exposures = []
        for row in range(self.Exposures_table.rowCount()):
            filter = self.Exposures_table.cellWidget(row, 0).value()
            exposure = self.Exposures_table.cellWidget(row, 1).value()
            if exposure > 0:
                self.selected_exposures.append([filter, exposure])
        self.interval = int(self.cycle_Interval_Input.text())
        self.cycles   = int(self.cycle_Input.text())
        print("Exposures:", self.selected_exposures, "| Interval:", self.interval, "| Experiment duration:", self.cycles)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            os.chdir(folder)
            self.directory_input.setText(folder)

    # ── experiment stop/cancellation ───────────────────────
    def _on_stop_experiment(self):
        """Stop button handler. Sets a flag the running experiment checks
        at its next safe checkpoint (between ticks, positions, or chemostat
        steps) - it does not interrupt mid valve-sequence. The actual
        all_on_callback() valve reset happens there too, via
        _safe_shutdown_valves(), once the worker actually unwinds."""
        self._experiment_stop_requested = True
        print("Stop requested - will halt at next safe checkpoint.")

    def _check_stop_and_sleep_chunked(self, total_seconds):
        """
        Sleep for total_seconds, but in ~1s chunks, checking the stop flag
        each time - so Stop takes effect within ~1s instead of requiring
        the full (potentially many-minutes) wait to elapse. Raises
        ExperimentStopped as soon as the flag is seen set.
        """
        remaining = total_seconds
        while remaining > 0:
            if self._experiment_stop_requested:
                raise ExperimentStopped()
            chunk = min(1.0, remaining)
            time.sleep(chunk)
            remaining -= chunk
        if self._experiment_stop_requested:
            raise ExperimentStopped()

    def _fl_status(self, msg: str):
        """Update the FL segmentation status label and print to console."""
        print(f"[FL-SEG] {msg}")
        if hasattr(self, "fl_status_label"):
            # Emitted through the bridge so this is safe to call from a
            # background ExperimentWorker thread as well as the GUI thread.
            # No QApplication.processEvents() needed anymore - the caller
            # no longer blocks the event loop, so it repaints on its own.
            self._exp_bridge.status_text_changed.emit("fl", f"Status: {msg}")

    def _build_fl_panel(self, parent_layout):
        """Build the FL Segmentation tab."""
        root = QHBoxLayout()
        root.setSpacing(10)
        parent_layout.addLayout(root)
        left  = QVBoxLayout(); left.setSpacing(8)
        right = QVBoxLayout(); right.setSpacing(8)

        info = QLabel(
            "No pre-experiment annotation needed.\n\n"
            "Every imaging interval:\n"
            "  • FL image taken at every position (first filter/exposure\n"
            "    from the exposure table is used for segmentation;\n"
            "    all filters are saved)\n"
            "  • Droplet segmented via Otsu threshold + electrode bridge\n"
            f"  • Chemostat triggered if area < "
            f"{FL_AREA_THRESHOLD * 100:.0f}% of initial area\n\n"
            "Only the positions ticked below are fed. Each starts in\n"
            "Upconcentration mode and is fed from the Upconcentration inlets.\n"
            "Droplet fluorescence (median inside mask − median outside) is\n"
            "measured each round; once it exceeds the position's own\n"
            "Up-concentration Factor (F1-F3, picked next to its tick box)\n"
            "× initial, the position switches to Synthesis: its next\n"
            "replenishment uses the Synthesis inlets, after which it switches\n"
            "to Maintain and is fed from the Maintain inlet for the rest of\n"
            "the experiment. Two inlets are mixed into one droplet.\n\n"
            "Each position tracks its own loop counter independently.\n"
            "Set imaging interval, total duration and Up-concentration\n"
            "Factors F1-F3 in the Timing panel."
        )
        info.setStyleSheet("color:#aaa; font-size:12px;")
        info.setWordWrap(True)
        left.addWidget(info)

        # -- Fluorescence Imaging: filter / exposure table
        fe_layout = QVBoxLayout()
        fe_layout.setSpacing(4)
        fe_top = QHBoxLayout()
        filter_list_layout = QVBoxLayout()
        filter_list_layout.setSpacing(2)
        for fk, fv in self.filterNames.items():
            lbl = QLabel(fv); lbl.setStyleSheet("color:#aaa; font-size:11px;")
            filter_list_layout.addWidget(lbl)
        self.Exposures_table = QTableWidget(len(self.filterNames), 2)
        self.Exposures_table.setHorizontalHeaderLabels(["Filter (1-6)", "Exposure (ms)"])
        self.Exposures_table.verticalHeader().setDefaultSectionSize(24)
        self.Exposures_table.setMaximumHeight(180)
        for row in range(len(self.filterNames)):
            sb1 = QSpinBox(); sb1.setRange(1, 6); sb1.setValue(row + 1)
            sb2 = QSpinBox(); sb2.setRange(0, 1000); sb2.setValue(0)
            self.Exposures_table.setCellWidget(row, 0, sb1)
            self.Exposures_table.setCellWidget(row, 1, sb2)
        self.Exposures_table.horizontalHeader().setStretchLastSection(True)
        fe_top.addLayout(filter_list_layout)
        fe_top.addWidget(self.Exposures_table, 1)
        fe_bottom = QHBoxLayout()
        self.Save_Exposures_button = QPushButton("Save Values")
        self.Save_Exposures_button.setStyleSheet(BTN_GREEN)
        self.Save_Exposures_button.clicked.connect(self.read_Exposure_values)
        self.quick_EPI_filter   = QSpinBox(); self.quick_EPI_filter.setRange(1,6); self.quick_EPI_filter.setValue(4)
        self.quick_EPI_exposure = QLineEdit("100")
        self.snap_EPI_button    = QPushButton("Snap Fluorescent Image")
        self.snap_EPI_button.setStyleSheet(BTN_GREY)
        self.snap_EPI_button.clicked.connect(
            lambda: self.snap_EPI_image(self.quick_EPI_filter.value(), int(self.quick_EPI_exposure.text())))
        quick_lbl_f = QLabel("Filter:"); quick_lbl_f.setStyleSheet("color:#aaa;")
        quick_lbl_e = QLabel("Exposure:");quick_lbl_e.setStyleSheet("color:#aaa;")
        fe_bottom.addWidget(self.Save_Exposures_button)
        fe_bottom.addWidget(quick_lbl_f)
        fe_bottom.addWidget(self.quick_EPI_filter)
        fe_bottom.addWidget(quick_lbl_e)
        fe_bottom.addWidget(self.quick_EPI_exposure)
        fe_bottom.addWidget(self.snap_EPI_button)
        fe_layout.addLayout(fe_top)
        fe_layout.addLayout(fe_bottom)
        left.addWidget(group("Fluorescence Imaging", fe_layout))

        # Mode table: one row under the headers
        #   Positions | Upconcentration | Synthesis | Maintain
        self.fl_mode_table = QTableWidget(1, 4)
        self.fl_mode_table.setHorizontalHeaderLabels(
            ["Positions", MODE_UPCONC, MODE_SYNTH, MODE_MAINTAIN])
        self.fl_mode_table.verticalHeader().setVisible(False)
        self.fl_mode_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.fl_mode_table.setFocusPolicy(Qt.NoFocus)

        # Positions: checkboxes 1-8 (1-6 ticked by default), each with the
        # Up-concentration Factor it uses (F1-F3 from the Timing panel;
        # F1 by default).
        pos_cell = QWidget()
        pos_grid = QGridLayout(pos_cell)
        pos_grid.setContentsMargins(4, 2, 4, 2)
        pos_grid.setHorizontalSpacing(8); pos_grid.setVerticalSpacing(2)
        self.fl_position_checks = []
        self.fl_position_factor_choice = []   # QComboBox per position, index 0-2
        for p in range(8):
            cb = QCheckBox(str(p + 1)); cb.setChecked(p < 6)
            factor_cb = QComboBox()
            factor_cb.addItems(["F1", "F2", "F3"])
            factor_cb.setToolTip(f"Up-concentration Factor for position {p + 1}")
            r, c = p % 4, (p // 4) * 2
            pos_grid.addWidget(cb, r, c)
            pos_grid.addWidget(factor_cb, r, c + 1)
            self.fl_position_checks.append(cb)
            self.fl_position_factor_choice.append(factor_cb)
        self.fl_mode_table.setCellWidget(0, 0, pos_cell)

        # Inlet spinboxes per mode (0 = unused). Upconcentration and
        # Synthesis take one or two inlets, Maintain takes one.
        self.fl_mode_inlets = {}         # mode -> [QSpinBox, ...]
        self._fl_mode_warn_labels = {}   # mode -> QLabel
        for col, (mode, n_inlets) in enumerate(
                [(MODE_UPCONC, 2), (MODE_SYNTH, 2), (MODE_MAINTAIN, 1)], start=1):
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(4, 2, 4, 2); cell_layout.setSpacing(2)
            row = QHBoxLayout(); row.setSpacing(4)
            boxes = []
            for k in range(n_inlets):
                sb = QSpinBox(); sb.setRange(0, 9)
                sb.setSpecialValueText("—")
                sb.setToolTip("Inlet 1-9 (— = unused)")
                row.addWidget(sb); boxes.append(sb)
            cell_layout.addLayout(row)
            warn = QLabel(""); warn.setWordWrap(True)
            warn.setStyleSheet("font-size:10px;")
            cell_layout.addWidget(warn)
            self.fl_mode_table.setCellWidget(0, col, cell)
            self.fl_mode_inlets[mode] = boxes
            self._fl_mode_warn_labels[mode] = warn
            for sb in boxes:
                sb.valueChanged.connect(
                    lambda _v, m=mode: self._update_fl_inlet_warning(m))
        self.fl_mode_inlets[MODE_UPCONC][0].setValue(1)
        for mode in self.fl_mode_inlets:
            self._update_fl_inlet_warning(mode)

        self.fl_mode_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        self.fl_mode_table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents)
        self.fl_mode_table.verticalHeader().setDefaultSectionSize(124)
        self.fl_mode_table.setFixedHeight(124 + 30)
        mode_layout = QVBoxLayout()
        mode_layout.addWidget(self.fl_mode_table)
        left.addWidget(group("Feeding Modes", mode_layout))
        left.addStretch()

        # ── RIGHT COLUMN ───────────────────────
        # -- Timing
        timing_grid = QGridLayout(); timing_grid.setSpacing(6)
        self.cycle_Interval_Input = QLineEdit("0")
        self.cycle_Input          = QLineEdit("0")
        # Up to 3 Up-concentration Factors (F1 required, F2/F3 optional).
        # A position switches Upconcentration -> Synthesis once
        # Fluo_Pos#_##min / Fluo_Pos#_initial exceeds the factor chosen for
        # it in the Feeding Modes table.
        self.upconc_factor_Inputs = []
        for k, default in enumerate(["10", "", ""]):
            le = QLineEdit(default)
            validator = QtGui.QDoubleValidator(1.0, 50.0, 2, le)
            validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
            le.setValidator(validator)
            le.setToolTip("1 – 50" + ("" if k == 0 else " (optional)"))
            if k:
                le.setPlaceholderText("optional")
            le.textChanged.connect(self._update_factor_choice_labels)
            self.upconc_factor_Inputs.append(le)
        for r, (lbl, w) in enumerate([
            ("Cycle interval (min):",      self.cycle_Interval_Input),
            ("Total duration (min):",      self.cycle_Input),
            ("Up-concentration Factor F1:", self.upconc_factor_Inputs[0]),
            ("Up-concentration Factor F2:", self.upconc_factor_Inputs[1]),
            ("Up-concentration Factor F3:", self.upconc_factor_Inputs[2]),
        ]):
            l = QLabel(lbl); l.setStyleSheet("color:#aaa;")
            timing_grid.addWidget(l, r, 0)
            timing_grid.addWidget(w, r, 1)
        self.interval = 0; self.cycles = 0
        right.addWidget(group("Timing", timing_grid))
        self._update_factor_choice_labels()

        # -- Save Directory
        dir_layout = QHBoxLayout(); dir_layout.setSpacing(4)
        self.directory_input = QLineEdit()
        self.directory_input.setPlaceholderText("Save directory…")
        self.browse_button   = QPushButton("Browse")
        self.browse_button.setStyleSheet(BTN_GREY)
        self.browse_button.clicked.connect(self.browse_folder)
        dir_layout.addWidget(self.directory_input, 1)
        dir_layout.addWidget(self.browse_button)
        right.addWidget(group("Save Directory", dir_layout))

        # -- Experiment control
        exp_layout = QVBoxLayout(); exp_layout.setSpacing(6)
        self.fl_start_button = QPushButton("▶  Start FL-segmentation timelapse")
        self.fl_start_button.setStyleSheet(BTN_GREEN)
        self.fl_start_button.setMinimumHeight(38)
        self.fl_start_button.clicked.connect(
            lambda: self._start_fl_experiment(
                interval_min=int(self.cycle_Interval_Input.text()),
                total_min=int(self.cycle_Input.text()),
            )
        )
        self.stop_experiment_button = QPushButton("■  Stop Experiment")
        self.stop_experiment_button.setStyleSheet(BTN_RED)
        self.stop_experiment_button.setMinimumHeight(38)
        self.stop_experiment_button.setEnabled(False)
        self.stop_experiment_button.clicked.connect(self._on_stop_experiment)
        exp_layout.addWidget(self.fl_start_button)
        exp_layout.addWidget(self.stop_experiment_button)

        self.fl_status_label = QLabel("Status: idle")
        self.fl_status_label.setStyleSheet("color:#ffcc44; font-size:11px;")
        self.fl_status_label.setWordWrap(True)
        exp_layout.addWidget(self.fl_status_label)

        self.fl_mode_label = QLabel("Modes: —")
        self.fl_mode_label.setStyleSheet("color:#66ccff; font-size:11px;")
        self.fl_mode_label.setWordWrap(True)
        exp_layout.addWidget(self.fl_mode_label)
        right.addWidget(group("Experiment Control", exp_layout))

        # -- Console log
        self.console_log_fl = QPlainTextEdit()
        self.console_log_fl.setReadOnly(True)
        self.console_log_fl.setMaximumBlockCount(2000)
        self.console_log_fl.setStyleSheet(CONSOLE_LOG_STYLE)
        self.console_log_fl.setMinimumHeight(160)
        log_layout = QVBoxLayout()
        log_layout.addWidget(self.console_log_fl)
        right.addWidget(group("Console Log", log_layout), 1)

        root.addLayout(left,  3)
        root.addLayout(right, 2)

    def _fl_mode_inlet_values(self, mode: str) -> list:
        """Inlets (1-9) chosen for `mode` in the Feeding Modes table, deduplicated."""
        inlets = []
        for sb in self.fl_mode_inlets[mode]:
            if sb.value() and sb.value() not in inlets:
                inlets.append(sb.value())
        return inlets

    def _fl_inlet_problem(self, mode: str):
        """Return a warning string for `mode`'s inlet choice, or None if OK."""
        inlets = self._fl_mode_inlet_values(mode)
        if not inlets:
            return "No inlet selected"
        if len(inlets) == 2 and not inlet_pair_is_legal(*inlets):
            a, b = inlets
            return (f"Illegal pair {a}+{b}: opens 4 valves "
                    f"(valid with {a}: {legal_partner_inlets(a)})")
        return None

    def _update_fl_inlet_warning(self, mode: str):
        label = self._fl_mode_warn_labels[mode]
        problem = self._fl_inlet_problem(mode)
        if problem:
            label.setText(f"⚠ {problem}")
            label.setStyleSheet("color:#ff6666; font-size:10px;")
        else:
            label.setText("OK")
            label.setStyleSheet("color:#2ac555; font-size:10px;")

    def _upconc_factor_values(self) -> list:
        """[F1, F2, F3] from the Timing panel: float if valid (1-50),
        None if blank, or the raw text if invalid."""
        values = []
        for le in self.upconc_factor_Inputs:
            text = le.text().strip()
            if not text:
                values.append(None)
                continue
            try:
                v = float(text)
            except ValueError:
                v = None
            values.append(v if v is not None and 1.0 <= v <= 50.0 else text)
        return values

    def _update_factor_choice_labels(self):
        """Show each factor's current value in the per-position drop-downs."""
        if len(getattr(self, "upconc_factor_Inputs", [])) < 3:
            return   # still building the Timing panel
        for k, v in enumerate(self._upconc_factor_values()):
            if isinstance(v, float):
                text = f"F{k + 1} = {v:g}"
            else:
                text = f"F{k + 1} (unset)" if v is None else f"F{k + 1} (invalid)"
            for combo in self.fl_position_factor_choice:
                combo.setItemText(k, text)

    def _fl_report_modes(self, pos_mode: dict):
        """Push the per-position mode summary to the FL tab (thread-safe)."""
        text = "Modes: " + "  |  ".join(
            f"Pos {i + 1}: {pos_mode[i]}" for i in sorted(pos_mode))
        self._exp_bridge.status_text_changed.emit("fl_mode", text)

    def _fl_update_fluorescence(self, idx, raw_fl, mask, tick_number,
                                time_tag_min, fluo_values, pos_mode,
                                upconc_factors, fluo_csv):
        """
        Measure droplet fluorescence for one position, store it in
        fluo_values as Fluo_Pos#_initial (tick 1) or Fluo_Pos#_##min, append
        it to fluo_csv, and switch an addressed position (one in pos_mode)
        from Upconcentration to Synthesis once
        Fluo_Pos#_##min / Fluo_Pos#_initial exceeds that position's factor
        in upconc_factors.
        """
        pos_num  = idx + 1
        init_key = f"Fluo_Pos{pos_num}_initial"
        key = init_key if tick_number == 1 else f"Fluo_Pos{pos_num}_{time_tag_min:.0f}min"

        factor = upconc_factors.get(idx)   # None for unaddressed positions
        result = droplet_fluorescence(raw_fl, mask)
        if result is None:
            print(f"  Pos {pos_num}: no droplet mask - {key} not measured")
            return
        fluo, med_in, med_out = result
        fluo_values[key] = fluo

        ratio = None
        initial = fluo_values.get(init_key)
        if tick_number > 1 and initial is not None:
            if initial > 0:
                ratio = fluo / initial
            else:
                print(f"  Pos {pos_num}: {init_key} = {initial:.1f} <= 0 - "
                      f"cannot compute up-concentration ratio")

        print(f"  Pos {pos_num}: {key} = {fluo:.1f}  "
              f"(in {med_in:.1f} - out {med_out:.1f})"
              + (f"  ratio {ratio:.2f}" if ratio is not None else "")
              + (f" / factor {factor:g}" if ratio is not None and factor else ""))

        if (ratio is not None and factor is not None and ratio > factor
                and pos_mode.get(idx) == MODE_UPCONC):
            pos_mode[idx] = MODE_SYNTH
            self._fl_status(
                f"Pos {pos_num} -> SYNTHESIS mode "
                f"(ratio {ratio:.2f} > {factor:g})")
            self._fl_report_modes(pos_mode)

        with open(fluo_csv, "a", newline="") as f:
            csv.writer(f).writerow([
                key, pos_num, f"{time_tag_min:.0f}", f"{med_in:.2f}",
                f"{med_out:.2f}", f"{fluo:.2f}",
                "" if ratio is None else f"{ratio:.4f}",
                "" if factor is None else factor,
                pos_mode.get(idx, "not addressed"),
            ])

    def _fl_feed_droplet(self, rn, inlets, positions, flow_dur, drive_dur):
        """Move to position rn, generate one droplet from `inlets` (one or a
        legal pair, opened together) and drive it into chemostat rn+1,
        recording the drive on the VideoThread."""
        px, py, pz = positions[rn]
        self.mmc.setTimeoutMs(30000)
        self.mmc.setXYPosition(px, py)
        self.mmc.waitForDevice(self.mmc.getXYStageDevice())
        self.mmc.setPosition(pz)
        self.mmc.waitForDevice(self.mmc.getFocusDevice())
        self.mmc.setTimeoutMs(5000)
        time.sleep(0.3)

        gw = DropletWorker("generate", inlets=list(inlets), flow_duration=flow_dur)
        gw.start(); gw.wait()

        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.start_recording()
        else:
            print(f"WARNING: VideoThread not running at "
                  f"position {rn+1} – skipping recording")
            return

        dw = DropletWorker(
            "drive", inlets[0],
            drive_duration=drive_dur,
            chemostat_number=rn + 1,
        )
        dw.start(); dw.wait()

        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop_recording()
        QtCore.QThread.msleep(200)

    def _fl_flush_buffer(self):
        """Flush the buffer inlet after a feed step."""
        self.open_inlet(self.Buffer_inlet)
        self.control_valve(6,  state=False)
        time.sleep(1)
        self.close_inlet(self.Buffer_inlet)
        self.control_valve(6,  state=True)

    def _start_fl_experiment(self, interval_min: int, total_min: int):
        """
        GUI-thread entry point for the FL-segmentation timelapse: does the
        validation (QMessageBox dialogs are not safe from a worker thread)
        and snapshots widget/shared-state reads into plain locals, then
        hands off to _run_fl_experiment_body on a background
        ExperimentWorker. See _run_fl_experiment_body's docstring for what
        the experiment actually does.
        """
        if not self.positions:
            QMessageBox.warning(self, "No positions",
                                "Save at least one stage position first.")
            return
        if not self.selected_exposures:
            QMessageBox.warning(self, "No exposures",
                                "Set at least one filter/exposure in the "
                                "FL Segmentation tab and click Save Values.")
            return
        if interval_min <= 0 or total_min <= 0:
            QMessageBox.warning(self, "Invalid timing",
                                "Set a non-zero interval and total duration.")
            return
        factors = self._upconc_factor_values()
        bad = [f"F{k + 1}" for k, v in enumerate(factors)
               if v is not None and not isinstance(v, float)]
        if factors[0] is None or bad:
            QMessageBox.warning(self, "Invalid Up-concentration Factor",
                                "F1 is required and every Up-concentration "
                                "Factor that is filled in must be between "
                                "1 and 50."
                                + (f"\n\nInvalid: {', '.join(bad)}" if bad else ""))
            return

        # Feeding Modes table
        problems = [f"{mode}: {self._fl_inlet_problem(mode)}"
                    for mode in (MODE_UPCONC, MODE_SYNTH, MODE_MAINTAIN)
                    if self._fl_inlet_problem(mode)]
        if problems:
            QMessageBox.warning(self, "Invalid inlets",
                                "Fix the Feeding Modes inlets:\n\n"
                                + "\n".join(problems))
            return
        mode_inlets = {mode: self._fl_mode_inlet_values(mode)
                       for mode in (MODE_UPCONC, MODE_SYNTH, MODE_MAINTAIN)}

        addressed = [p for p, cb in enumerate(self.fl_position_checks)
                     if cb.isChecked()]
        if not addressed:
            QMessageBox.warning(self, "No positions addressed",
                                "Tick at least one position in the Feeding "
                                "Modes table.")
            return
        missing = [p + 1 for p in addressed if p >= len(self.positions)]
        if missing:
            answer = QMessageBox.question(
                self, "Positions not saved",
                f"Position(s) {', '.join(map(str, missing))} are ticked but "
                f"only {len(self.positions)} stage position(s) are saved.\n"
                f"They will be skipped. Continue?")
            if answer != QMessageBox.Yes:
                return
            addressed = [p for p in addressed if p < len(self.positions)]
            if not addressed:
                return

        # Up-concentration Factor per addressed position
        upconc_factors = {}
        unset = []
        for p in addressed:
            k = self.fl_position_factor_choice[p].currentIndex()
            if factors[k] is None:
                unset.append(f"Pos {p + 1} → F{k + 1}")
            upconc_factors[p] = factors[k]
        if unset:
            QMessageBox.warning(self, "Up-concentration Factor not set",
                                "These positions use a factor that is "
                                "blank in the Timing panel:\n\n"
                                + "\n".join(unset))
            return

        base      = self.directory_input.text().strip() or "."
        purge_dur = float(self.purge_duration_Input.text())
        flow_dur  = float(self.flow_duration_Input.text())
        drive_dur = float(self.drive_duration_Input.text())

        self._launch_experiment_worker(
            self._run_fl_experiment_body,
            interval_min, total_min, base, purge_dur, flow_dur, drive_dur,
            # Snapshot into fresh lists - see the fallback path's launch
            # for why (the user can still click Save/Clear Position or Add
            # Step while this worker thread is running).
            list(self.positions), list(self.selected_exposures),
            upconc_factors, mode_inlets, addressed,
        )

    def _run_fl_experiment_body(self, interval_min, total_min, base,
                                 purge_dur, flow_dur, drive_dur,
                                 positions, selected_exposures,
                                 upconc_factors, mode_inlets, addressed):
        """
        FL-segmentation timelapse — no pre-annotation required.
        Runs on a background ExperimentWorker thread (see _start_fl_experiment).

        Every `interval_min` minutes for `total_min` total minutes:
          1. Move to every position and snap FL images for all filters
             defined in the exposure table.
             The FIRST filter/exposure entry is used for segmentation;
             all filter images are saved as raw uint16 TIFFs.
          2. segment_droplet_fl() segments the droplet and measures its area.
             The segmentation overlay is saved alongside the TIFF for inspection.
          3. Initial area is recorded on the very first tick.
          4. Droplet fluorescence (median inside mask − median outside) is
             recorded as Fluo_Pos#_initial on tick 1 and Fluo_Pos#_##min
             afterwards, logged to <base>/fluorescence_upconcentration.csv.
             Every addressed position starts in Upconcentration mode; once
             Fluo_Pos#_##min / Fluo_Pos#_initial > its own factor
             (upconc_factors, chosen per position from F1-F3) it switches
             to Synthesis mode.
          5. From tick 2 onwards, if an addressed position's
             area < AREA_THRESHOLD × initial, it gets one droplet generated
             from its current mode's inlets (mode_inlets; a pair is opened
             together) and its loop counter increments:
               – Upconcentration: Upconcentration inlets.
               – Synthesis: Synthesis inlets once, then the position
                 switches to Maintain for the rest of the experiment.
               – Maintain: Maintain inlet.

        Folder / file naming
        ────────────────────
        <base>/
          Position_1/
            FL/
              Pos1_Loop1_filt1_100ms_3min.tiff        ← raw uint16
              Pos1_Loop1_filt1_100ms_3min_mask.png    ← segmentation overlay
              Pos1_Loop1_filt2_50ms_3min.tiff
              …
        """
        try:
            self._run_fl_experiment_body_inner(
                interval_min, total_min, base, purge_dur, flow_dur, drive_dur,
                positions, selected_exposures,
                upconc_factors, mode_inlets, addressed)
        except Exception:
            # Stop (ExperimentStopped) or a real failure mid-run: reset to a
            # known-safe state before propagating. Normal completion does
            # NOT go through here - it has its own deliberate final
            # valve-7 state at the end, which this must not stomp on.
            self._safe_shutdown_valves()
            raise

    def _run_fl_experiment_body_inner(self, interval_min, total_min, base,
                                       purge_dur, flow_dur, drive_dur,
                                       positions, selected_exposures,
                                       upconc_factors, mode_inlets, addressed):
        interval_sec = interval_min * 60
        total_sec    = total_min    * 60

        # Per-position state — all local
        initial_areas  = {}   # {idx: int px}  – recorded on tick 1
        pos_loop_count = {}   # {idx: int}      – completed loops (0 → Loop 1)
        # Fluorescence values keyed "Fluo_Pos#_initial" / "Fluo_Pos#_##min"
        fluo_values    = {}
        # Mode of each addressed position (0-based idx); unaddressed
        # positions are imaged and logged but never fed.
        pos_mode       = {idx: MODE_UPCONC for idx in addressed}
        self._fl_report_modes(pos_mode)

        os.makedirs(base, exist_ok=True)
        fluo_csv = os.path.join(base, "fluorescence_upconcentration.csv")
        if not os.path.exists(fluo_csv):
            with open(fluo_csv, "w", newline="") as f:
                csv.writer(f).writerow([
                    "name", "position", "time_min", "median_inside",
                    "median_outside", "fluo", "ratio_to_initial",
                    "upconc_factor", "mode",
                ])

        # Initialise valves
        init_states = [
            (0, True), (1, True),  (2, True), (3, True),  (4, True),  (5, True),
            (6, True), (7, False),  (8, True), (9, True), (10, False), (11, True),
            (12, False), (13, False), (14, False), (15, False), (16, False), (17, False),
        ]
        for v, s in init_states:
            self.control_valve(v, state=s)

        experiment_start = time.time()
        tick_number      = 0

        self._fl_status(
            f"Experiment started — interval {interval_min} min / "
            f"total {total_min} min"
        )
        print(f"\n{'='*62}")
        print(f"  FL-SEG TIMELAPSE  |  interval {interval_min} min  "
              f"|  total {total_min} min")
        print(f"{'='*62}")

        # ── outer timing loop ─────────────────────────────────────────────
        while True:
            elapsed_sec = time.time() - experiment_start
            if elapsed_sec >= total_sec:
                break

            wait_for = tick_number * interval_sec - elapsed_sec
            if wait_for > 0:
                self._fl_status(f"Waiting {wait_for:.0f} s until next imaging round …")
                self._check_stop_and_sleep_chunked(wait_for)

            tick_number        += 1
            tick_wall_start     = time.time()
            elapsed_min         = (tick_wall_start - experiment_start) / 60.0
            time_tag_min        = round(elapsed_min / interval_min) * interval_min
            time_tag_str        = f"{time_tag_min:.0f}min"

            print(f"\n{'─'*62}")
            print(f"  Tick {tick_number}  |  ~{time_tag_min:.0f} min elapsed")
            print(f"{'─'*62}")

            triggered_positions = []

            # ── Phase 1: first row of exposure table → area check, all positions ──
            # selected_exposures[0] is the first row the user filled in —
            # whichever filter/exposure that happens to be.
            seg_filt, seg_exp = selected_exposures[0]

            for idx, (px, py, pz) in enumerate(positions):
                if self._experiment_stop_requested:
                    raise ExperimentStopped()
                pos_num  = idx + 1
                pos_loop = pos_loop_count.get(idx, 0) + 1
                initial  = initial_areas.get(idx, 0)

                fl_dir = os.path.join(base, f"Position_{pos_num}", "FL")
                os.makedirs(fl_dir, exist_ok=True)

                self._fl_status(
                    f"Area check – Pos {pos_num}  Loop {pos_loop}  "
                    f"filt {seg_filt}  {seg_exp}ms  @ {time_tag_str}"
                )
                self.mmc.setTimeoutMs(30000)
                self.mmc.setXYPosition(px, py)
                self.mmc.waitForDevice(self.mmc.getXYStageDevice())
                self.mmc.setPosition(pz)
                self.mmc.waitForDevice(self.mmc.getFocusDevice())
                self.mmc.setTimeoutMs(5000)
                time.sleep(0.1)

                raw_fl = self.snap_EPI_image(seg_filt, seg_exp)

                # Save raw uint16 TIFF
                # e.g. Pos1_Loop2_filt3_30ms_6min.tiff
                fl_fname = (
                    f"Pos{pos_num}_Loop{pos_loop}"
                    f"_filt{seg_filt}_{seg_exp}ms_{time_tag_str}.tiff"
                )
                tiff.imwrite(os.path.join(fl_dir, fl_fname), raw_fl)

                # Segment and save overlay PNG for visual inspection
                # e.g. Pos1_Loop2_filt3_30ms_6min_mask.png
                seg_mask, seg_area, seg_overlay = segment_droplet_fl(raw_fl)
                overlay_fname = (
                    f"Pos{pos_num}_Loop{pos_loop}"
                    f"_filt{seg_filt}_{seg_exp}ms_{time_tag_str}_mask.png"
                )
                cv2.imwrite(os.path.join(fl_dir, overlay_fname), seg_overlay)
                time.sleep(0.2)

                # Droplet fluorescence → Upconcentration/Synthesis switch
                self._fl_update_fluorescence(
                    idx, raw_fl, seg_mask, tick_number, time_tag_min,
                    fluo_values, pos_mode, upconc_factors, fluo_csv)

                # Record initial area on the very first tick
                if tick_number == 1:
                    initial_areas[idx] = seg_area
                    print(f"  Pos {pos_num}: initial area recorded = {seg_area} px")
                else:
                    ratio = seg_area / initial if initial > 0 else 1.0
                    print(
                        f"  Pos {pos_num}  Loop {pos_loop}: "
                        f"area = {seg_area} px  ({ratio * 100:.1f}% of initial  "
                        f"[threshold {FL_AREA_THRESHOLD * 100:.0f}%])"
                    )
                    if (idx in pos_mode and initial > 0
                            and seg_area < FL_AREA_THRESHOLD * initial):
                        triggered_positions.append(idx)
                        self._fl_status(
                            f"⚠ Pos {pos_num} TRIGGERED "
                            f"({ratio * 100:.1f}% < "
                            f"{FL_AREA_THRESHOLD * 100:.0f}%)"
                        )

            # ── no triggers this tick ─────────────────────────────────────────────
            if not triggered_positions:
                print("  ✓ All droplets within acceptable size.")
                self._fl_status(
                    f"Tick {tick_number}: all areas OK. "
                    f"Next in ~{interval_min} min."
                )
                continue

            names = [f"Pos {i + 1}" for i in triggered_positions]
            print(f"\n  ⚠ Triggered: {', '.join(names)}")

            # ── Phase 2: remaining rows of exposure table → all positions ─────────
            # Only runs when at least one position was triggered this tick.
            # Row 0 was already imaged in Phase 1, so we start from row 1.
            if len(selected_exposures) > 1:
                # Reset shutter state after chemostat protocol before imaging.
                # The chemostat sequence leaves the hardware in an uncertain
                # shutter state; explicitly closing both shutters and waiting
                # prevents waitForSystem() timing out on TIEpiShutter.
                self.mmc.setProperty(self.EPIshutter, 'State', 0)
                self.mmc.setProperty(self.DIAshutter, 'State', 0)
                self.mmc.waitForSystem()
                time.sleep(1.0)
                self._fl_status("Full exposure table imaging of all positions …")
                for idx, (px, py, pz) in enumerate(positions):
                    if self._experiment_stop_requested:
                        raise ExperimentStopped()
                    pos_num  = idx + 1
                    pos_loop = pos_loop_count.get(idx, 0) + 1

                    fl_dir = os.path.join(base, f"Position_{pos_num}", "FL")
                    os.makedirs(fl_dir, exist_ok=True)

                    self.mmc.setTimeoutMs(30000)
                    self.mmc.setXYPosition(px, py)
                    self.mmc.waitForDevice(self.mmc.getXYStageDevice())
                    self.mmc.setPosition(pz)
                    self.mmc.waitForDevice(self.mmc.getFocusDevice())
                    self.mmc.setTimeoutMs(5000)
                    time.sleep(0.3)

                    for filt, exp in selected_exposures[1:]:
                        self._fl_status(
                            f"FL snap – Pos {pos_num}  Loop {pos_loop}  "
                            f"filt {filt}  {exp}ms  @ {time_tag_str}"
                        )
                        raw_fl = self.snap_EPI_image(filt, exp)
                        fl_fname = (
                            f"Pos{pos_num}_Loop{pos_loop}"
                            f"_filt{filt}_{exp}ms_{time_tag_str}.tiff"
                        )
                        tiff.imwrite(os.path.join(fl_dir, fl_fname), raw_fl)
                        time.sleep(0.2)

            print(f"\n  ⚠ Triggered: {', '.join(names)}")

            # ── feed triggered positions according to their current mode ───
            # Each mode group: purge that mode's inlets once, then one droplet
            # (inlets opened together) per triggered position, then flush.
            # Synthesis is fed once, after which the position goes to Maintain.
            if triggered_positions:
                self._fl_status("Feeding triggered positions …")

                self.open_inlet(self.Buffer_inlet)
                time.sleep(2)
                self.close_inlet(self.Buffer_inlet)

                self.mmc.setProperty(self.DIAlamp, "State", 1)
                if self.video_thread is not None and self.video_thread.isRunning():
                    self.video_thread.stop()
                    self.video_thread = None
                self.video_thread = VideoThread()
                self.video_thread.start()
                QtCore.QThread.msleep(300)

                # ── HOLD DROPLETS IN PLACE ────────────
                send_to_arduino(2)
                send_to_arduino(4)

                for mode in (MODE_UPCONC, MODE_SYNTH, MODE_MAINTAIN):
                    group_idx = [i for i in triggered_positions
                                 if pos_mode[i] == mode]
                    if not group_idx:
                        continue
                    inlets = mode_inlets[mode]
                    if self._experiment_stop_requested:
                        raise ExperimentStopped()

                    pw = DropletWorker("purge", inlets=inlets, purge_duration=purge_dur)
                    pw.start(); pw.wait()

                    for rn in group_idx:
                        if self._experiment_stop_requested:
                            raise ExperimentStopped()
                        self._fl_status(
                            f"{mode} feed – Pos {rn + 1}  "
                            f"inlet(s) {'+'.join(map(str, inlets))}")
                        self._fl_feed_droplet(rn, inlets, positions,
                                              flow_dur, drive_dur)
                        if mode == MODE_SYNTH:
                            pos_mode[rn] = MODE_MAINTAIN
                            print(f"  Pos {rn + 1}: synthesis feed done "
                                  f"-> MAINTAIN mode")

                    self._fl_flush_buffer()
                self._fl_report_modes(pos_mode)

                self.video_thread.stop()
                self.video_thread = None
                self.mmc.setProperty(self.DIAlamp, "State", 0)

                # ── STOP FLOW TO DROPLETS ────────────
                self.control_valve(11, state=True)
                send_to_arduino(4)
                send_to_arduino(3)

            # ── increment loop counters for triggered positions ───────────
            for idx in triggered_positions:
                pos_loop_count[idx] = pos_loop_count.get(idx, 0) + 1
                print(
                    f"  Pos {idx + 1}: entering Loop {pos_loop_count[idx] + 1}"
                )

        # ── experiment complete ───────────────────────────────────────────
        self.mmc.setTimeoutMs(5000)
        send_to_arduino(3)
        self.control_valve(7, state=True)
        print("\n=== FL-segmentation timelapse complete ===")
        self._fl_status("Experiment complete.")

    def _launch_experiment_worker(self, target, *args, **kwargs):
        """
        Shared launch path for the FL experiment's Start button:
        guards against starting a second experiment while one is already
        running, resets the stop flag, flips Start/Stop button state, and
        runs `target(*args, **kwargs)` on a background ExperimentWorker so
        the GUI stays responsive for the run's full duration.

        Returns True if launched, False if an experiment was already running
        (in which case the caller should not proceed with its own setup).
        """
        if self._exp_worker is not None and self._exp_worker.isRunning():
            print("An experiment is already running - ignoring Start.")
            return False
        self._experiment_stop_requested = False
        self._set_experiment_controls_enabled(False)
        self._exp_worker = ExperimentWorker(target, *args, **kwargs)
        self._exp_worker.finished.connect(self._on_experiment_worker_finished)
        self._exp_worker.start()
        return True

    def _set_experiment_controls_enabled(self, enabled: bool):
        """
        Enable/disable every control that would race a running
        ExperimentWorker if clicked mid-run: the FL experiment
        entry point (so a second experiment can't be started concurrently),
        Live/Record (self.video_thread is shared with the worker), and the
        position/exposure/timing/feeding-mode editing controls (editing them
        mid-run wouldn't affect the already-snapshotted running worker, but
        would misleadingly suggest it does).
        """
        self.stop_experiment_button.setEnabled(not enabled)
        for widget in (
            self.fl_start_button, self.live_Button, self.record_button,
            self.quick_fl_snap_button,
            self.save_Position_button, self.replacePositionButton,
            self.clearButton, self.GoToPositionButton, self.Save_Exposures_button,
            self.fl_mode_table, *self.upconc_factor_Inputs, self.Exposures_table,
            self.cycle_Interval_Input, self.cycle_Input,
            self.directory_input, self.browse_button,
        ):
            widget.setEnabled(enabled)

    @pyqtSlot()
    def _on_experiment_worker_finished(self):
        self._set_experiment_controls_enabled(True)
        worker = self._exp_worker
        self._exp_worker = None
        if worker is not None and worker.exc:
            QMessageBox.critical(
                self, "Experiment failed",
                f"The experiment stopped due to an error:\n\n{worker.exc}")



    def closeEvent(self, event):
        self.all_on_callback()
        if self.Numato_port and self.Numato_port.is_open:
            self.Numato_port.close()
        arduino.close()
        sys.stdout = self._real_stdout
        sys.stderr = self._real_stderr
        event.accept()
# ─────────────────────────────────────────────
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setPalette(make_dark_palette())
    app.setStyleSheet(WIDGET_STYLE)
    window = MicroscopeControlGUI()
    sys.exit(app.exec_())
