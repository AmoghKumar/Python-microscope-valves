import os
import time
from pymmcore_plus import CMMCorePlus
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QScrollArea, QTabWidget, QFileDialog,
    QRadioButton, QFrame, QSpinBox, QLineEdit, QCheckBox, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QInputDialog, QGridLayout, QSizePolicy,
    QGroupBox, QSplitter, QDialog, QSlider
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
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.widgets import RectangleSelector
import tifffile as tiff
import shutil
import json
import threading
import queue

# ─────────────────────────────────────────────
#  Hardware constants
# ─────────────────────────────────────────────
Arduino_port      = "COM4"
Arduino_baud_rate = 115200
Arduino_timeout   = 0.1


# ─────────────────────────────────────────────
#  Style helpers
# ─────────────────────────────────────────────
BTN_RED    = "background-color: #bb283a; color: white; border-radius: 4px; padding: 4px 8px;"
BTN_GREEN  = "background-color: #2ac555; color: white; border-radius: 4px; padding: 4px 8px;"
BTN_BLUE   = "background-color: #3a6bc9; color: white; border-radius: 4px; padding: 4px 8px;"
BTN_YELLOW = "background-color: #d4a017; color: black; border-radius: 4px; padding: 4px 8px;"
BTN_BLACK  = "background-color: #222222; color: white; border-radius: 4px; padding: 4px 8px;"
BTN_PURPLE = "background-color: #6a3db8; color: white; border-radius: 4px; padding: 4px 8px;"

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


def roi_mean_stats(raw_frame, extents, img_w, img_h):
    """
    Shared by define_roi() and the stack calibration dialog: clamps a
    RectangleSelector's (xmin, xmax, ymin, ymax) extents to the frame bounds
    and computes mean/min/max/std on the *raw* pixel values inside it - the
    same raw counts EpiMonitorThread's mean-intensity metric computes on, so
    numbers read here are directly comparable to real detection thresholds.

    Returns (x0, y0, x1, y1, mean, info_str), or None if the clamped ROI has
    zero width or height.
    """
    xmin, xmax, ymin, ymax = extents
    x0, y0 = int(max(0, xmin)), int(max(0, ymin))
    x1, y1 = int(min(img_w, xmax)), int(min(img_h, ymax))
    if x1 <= x0 or y1 <= y0:
        return None
    roi_raw  = raw_frame[y0:y1, x0:x1]
    mean_val = float(roi_raw.mean())
    info_str = (f"ROI: x={x0}, y={y0}, w={x1 - x0}, h={y1 - y0}   |   "
                f"mean={mean_val:.1f}  min={int(roi_raw.min())}  "
                f"max={int(roi_raw.max())}  std={roi_raw.std():.1f}")
    return x0, y0, x1, y1, mean_val, info_str


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

def send_to_arduino(data):
    # No sleep/readline here on purpose: the response is never used (this
    # was previously write() -> sleep(0.1) -> readline(), which blocks for
    # up to ~0.2s per call - readline() alone can block up to Arduino_timeout
    # waiting for a line). Called from EpiMonitorThread's acquisition loop on
    # every sort pulse, that latency stalled frame grabbing and froze the
    # live feed for the duration of every trigger.
    arduino.write(f"{data}\n".encode())

def set_voltage(set_value):
    if str(set_value) == 'High':
        send_to_arduino(5)
    elif str(set_value) == 'Low':
        send_to_arduino(4)

    print(f"Voltage set to: {str(set_value)}")


# ═══════════════════════════════════════════════════════════════════════════
#  FL droplet segmentation  –  static-frame Otsu segmentation (used for
#  one-off snaps/inspection; the real-time sorter uses a cheaper per-frame
#  metric instead, see EpiMonitorThread below)
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

Microscope = {}
Microscope['mmc'] = CMMCorePlus.instance()
Microscope['mmc'].loadSystemConfiguration("C:\\MATLAB Microscope\\AmoghMMConfig_Hamamatsu.cfg")


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

    def __init__(self, exposure_ms=50):
        super().__init__()
        self._run_flag    = True
        self._record_flag = False
        self._lock        = QtCore.QMutex()          # FIX: guards self.out across threads
        self.out          = None
        self.video_directory = "C:/Users/Cell Culture Scope/Downloads/Videos"
        self.video_filename  = self.get_unique_filename(self.video_directory)
        self.fourcc      = cv2.VideoWriter_fourcc(*'MJPG')
        self.exposure_ms = exposure_ms
        # Declared playback fps for the AVI - derived from exposure so the
        # written file's timing roughly matches the real capture rate. Actual
        # rate also includes readout/overhead so this is an approximation,
        # capped so a very short exposure doesn't imply an absurd fps value.
        self.fps         = min(60.0, 1000.0 / max(self.exposure_ms, 1.0))
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
        self.mmc.setProperty(self.camera, 'Exposure', self.exposure_ms)
        self.mmc.setProperty(self.core, 'Shutter', self.DIAshutter)
        self.mmc.setProperty(self.lightpath, 'Label', self.camerapath)
        self.mmc.initializeCircularBuffer()
        self.mmc.prepareSequenceAcquisition(self.camera)
        self.mmc.waitForDevice(self.DIAshutter)
        self.mmc.waitForDevice(self.camera)
        # 0 = acquire as fast as the camera can produce frames (limited only
        # by exposure + readout), not a fixed interval. The previous value of
        # 100 told MMCore to only deliver a frame every 100ms - a 10fps cap
        # independent of and on top of the exposure setting.
        self.mmc.startContinuousSequenceAcquisition(0)
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
                            # self.final_image already went through the same single
                            # exposure.rescale_intensity() call used by snap_DIA_image /
                            # snap_EPI_image (see convert_raw_np below) - do NOT re-stretch
                            # it here with a second, independent rescale_intensity call,
                            # since that maps this frame's own min/max a second time and
                            # decouples the video's pixel values from the snap's. The video
                            # codec still needs 8-bit, so just bit-shift down - a fixed,
                            # deterministic mapping from the exact same 16-bit values a
                            # snap would show, not an adaptive re-stretch.
                            frame_8bit = (self.final_image >> 8).astype(np.uint8)
                            frame_to_save = cv2.cvtColor(frame_8bit, cv2.COLOR_GRAY2BGR)
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
#  Real-time EPI fluorescence monitor / sorter
# ─────────────────────────────────────────────
class EpiMonitorThread(QThread):
    """
    Continuously acquires FL frames on the EPI light path, evaluates a
    per-frame metric inside a fixed ROI, and fires the Arduino sort
    electrode the instant a fluorescent droplet is detected.

    Detection uses a two-threshold hysteresis state machine biased toward
    recall (see _state below): once metric >= detect_threshold the pulse
    fires immediately with no confirmation delay, and the only suppression
    is "don't re-fire while the same droplet is still bright" (metric stays
    >= reset_threshold). There is deliberately no minimum-consecutive-frames
    gate, since that could suppress a real, brief detection.
    """
    change_pixmap_signal = pyqtSignal(np.ndarray)
    metric_signal    = pyqtSignal(float, int, str)         # metric value, frame index, state
    detection_signal = pyqtSignal(np.ndarray, float, int)  # frame, metric value, frame index
    status_signal    = pyqtSignal(str)

    def __init__(self, filter_index, exposure_ms, roi_rect, metric, pixel_cutoff,
                 detect_threshold, reset_threshold, pulse_duration_s, save_dir,
                 coverage_trigger_pct=20.0, coverage_reset_pct=10.0):
        super().__init__()
        self._run_flag  = True
        self._sort_lock = QtCore.QMutex()
        self._log_lock  = threading.Lock()

        self.mmc        = Microscope['mmc']
        self.camera     = self.mmc.getCameraDevice()
        self.core       = 'Core'
        self.EPIshutter = 'TIEpiShutter'
        self.filter     = 'TIFilterBlock1'
        self.lightpath  = 'TILightPath'
        self.camerapath = '2-Left100'

        self.filter_index     = filter_index
        self.exposure_ms      = exposure_ms
        self.roi_rect         = roi_rect       # (x, y, w, h) in full-frame pixel coords
        self.metric           = metric         # "mean" / "max" / "pct_above_thresh" / "pct_above_detect"
        self.pixel_cutoff     = pixel_cutoff
        self.detect_threshold = detect_threshold
        self.reset_threshold  = reset_threshold
        self.pulse_duration_s = pulse_duration_s
        self.save_dir         = save_dir

        # "pct_above_detect": reuses detect_threshold as the per-pixel
        # brightness cutoff (the same calibrated value used by Mean/Max
        # mode), and requires coverage_trigger_pct % of the ROI's pixels to
        # individually clear it before firing - more robust than a plain
        # mean against a partially-filled ROI (a few very bright pixels
        # can't drag a low-coverage frame over the line, and a large dim
        # smear can't fake a small bright droplet). Since detect_threshold
        # is used INSIDE this metric rather than as the outer trigger point,
        # the outer trigger/reset comparison uses these dedicated coverage
        # percentages instead - see _trigger_level/_reset_level below.
        self.coverage_trigger_pct = coverage_trigger_pct
        self.coverage_reset_pct   = coverage_reset_pct
        if self.metric == "pct_above_detect":
            self._trigger_level = coverage_trigger_pct
            self._reset_level   = coverage_reset_pct
        else:
            self._trigger_level = detect_threshold
            self._reset_level   = reset_threshold

        self.frame_index = 0
        self.event_count = 0
        self.run_dir     = None
        self._state      = "IDLE"

        # Optional video recording, start/stoppable independently of the
        # monitoring session itself (monitoring keeps running either way).
        # Encoding/writing happens on a SEPARATE background thread fed by a
        # queue, not inline in the acquisition loop: JPEG-encoding and disk
        # I/O are real per-frame costs, and this loop is time-critical for
        # detection - doing that work here would compete with (and delay)
        # the sort pulse the same way the old inline TIFF-save-before-
        # trigger bug did. The acquisition loop only ever does a fast,
        # non-blocking queue.put().
        self._record_flag    = False
        self._video_queue    = queue.Queue()
        self._video_thread   = None
        self.video_fourcc    = cv2.VideoWriter_fourcc(*'MJPG')
        self.video_fps       = min(60.0, 1000.0 / max(self.exposure_ms, 1.0))

    # ── detection metric ────────────────────────────────────────────────
    def _compute_metric(self, roi):
        if self.metric == "max":
            return float(roi.max())
        if self.metric == "pct_above_thresh":
            return float((roi > self.pixel_cutoff).mean() * 100.0)
        if self.metric == "pct_above_detect":
            return float((roi > self.detect_threshold).mean() * 100.0)
        return float(roi.mean())   # default: mean intensity

    # ── Arduino sort pulse ───────────────────────────────────────────────
    def fire_sort_pulse(self):
        """
        Drives the sort electrode voltage HIGH for pulse_duration_s, then
        back LOW - voltage itself is the trigger signal during monitoring
        (idle/not-triggered = LOW, triggered = HIGH), not a separate TTL
        gate held at a constant voltage. Guarded by _sort_lock so overlapping
        auto-detections can't interleave (only relevant if a pulse is still
        finishing when the next one fires).

        Blocks for the full pulse_duration_s - that hold time is the actual
        electrode-on duration and can't be removed, so this must never be
        called directly from the acquisition loop (see fire_sort_pulse_async).
        """
        self._sort_lock.lock()
        try:
            send_to_arduino(5)   # VOLTAGE_high
            time.sleep(self.pulse_duration_s)
            send_to_arduino(4)   # VOLTAGE_low
        finally:
            self._sort_lock.unlock()

    def fire_sort_pulse_async(self):
        """
        Runs fire_sort_pulse() on a plain background thread instead of
        inline in run()'s frame-grab loop. fire_sort_pulse() blocks for
        pulse_duration_s (the required electrode hold time) - calling it
        directly from run() froze the live feed for that whole duration
        every time a droplet triggered, since no new frames could be
        grabbed/emitted while the loop was stuck in that sleep. Firing it
        on a separate thread lets acquisition keep running during the pulse.
        """
        threading.Thread(target=self.fire_sort_pulse, daemon=True).start()

    # ── optional video recording during monitoring ──────────────────────
    def _video_writer_loop(self, video_filename):
        """
        Runs entirely on its own background thread: pulls frames off
        _video_queue and does the actual JPEG encode + disk write, so this
        work never shares a thread with frame-grabbing/detection. A None
        item is the stop sentinel.
        """
        out = None
        frame_size = None
        try:
            while True:
                display = self._video_queue.get()
                if display is None:
                    break
                if out is None:
                    h, w = display.shape[:2]
                    frame_size = (w, h)
                    out = cv2.VideoWriter(video_filename, self.video_fourcc,
                                           self.video_fps, frame_size, isColor=True)
                    if not out.isOpened():
                        self.status_signal.emit(f"failed to open video writer at {video_filename}")
                        out = None
                        continue
                frame_8bit   = (display >> 8).astype(np.uint8)
                frame_to_save = cv2.cvtColor(frame_8bit, cv2.COLOR_GRAY2BGR)
                if frame_to_save.shape[:2][::-1] == frame_size:
                    out.write(frame_to_save)
        finally:
            if out is not None:
                out.release()

    def start_recording(self):
        if self._video_thread is not None and self._video_thread.is_alive():
            return
        video_filename = os.path.join(self.run_dir, f"video_{time.strftime('%Y%m%d_%H%M%S')}.avi")
        self._video_thread = threading.Thread(
            target=self._video_writer_loop, args=(video_filename,), daemon=True)
        self._video_thread.start()
        self._record_flag = True

    def stop_recording(self):
        self._record_flag = False
        if self._video_thread is not None:
            self._video_queue.put(None)   # stop sentinel
            self._video_thread.join()
            self._video_thread = None

    # ── save + log on detection ──────────────────────────────────────────
    def _write_run_config(self):
        os.makedirs(self.run_dir, exist_ok=True)
        config = {
            "roi_rect":            self.roi_rect,
            "metric":              self.metric,
            "pixel_cutoff":        self.pixel_cutoff,
            "detect_threshold":    self.detect_threshold,
            "reset_threshold":     self.reset_threshold,
            "coverage_trigger_pct": self.coverage_trigger_pct,
            "coverage_reset_pct":   self.coverage_reset_pct,
            "filter_index":        self.filter_index,
            "exposure_ms":         self.exposure_ms,
            "pulse_duration_s":    self.pulse_duration_s,
            "start_time":          time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(os.path.join(self.run_dir, "config.json"), "w") as f:
            json.dump(config, f, indent=2)
        with open(os.path.join(self.run_dir, "events.csv"), "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "frame_index", "roi_metric_value", "threshold_used",
                 "pulse_duration_s", "image_filename"])

    def _log_event(self, metric_value, image_filename):
        row = [time.strftime("%Y-%m-%d %H:%M:%S"), self.frame_index, metric_value,
               self._trigger_level, self.pulse_duration_s, image_filename]
        with self._log_lock:
            with open(os.path.join(self.run_dir, "events.csv"), "a", newline="") as f:
                csv.writer(f).writerow(row)

    def _save_and_log_async(self, frame, fname, metric_value):
        """
        Runs the TIFF save + CSV log on a background thread. Disk I/O here
        (opening/writing/flushing a file) can easily cost tens of ms - doing
        it inline in run()'s loop, even after firing the pulse, would still
        stall the NEXT frame grab by that much, which matters if droplets
        follow each other closely. This keeps the acquisition loop free to
        grab the next frame immediately after firing.
        """
        def _worker():
            tiff.imwrite(os.path.join(self.run_dir, fname), frame)
            self._log_event(metric_value, fname)
        threading.Thread(target=_worker, daemon=True).start()

    # ── main loop ────────────────────────────────────────────────────────
    def run(self):
        self.run_dir = os.path.join(self.save_dir, "run_" + time.strftime("%Y%m%d_%H%M%S"))
        self._write_run_config()

        send_to_arduino(2)    # TTL_Signal_ON - enables the voltage generator itself; without
                              # this, toggling amplitude High/Low has no effect at the electrodes
        set_voltage('Low')    # idle/not-triggered baseline - fire_sort_pulse() drives it High per detection

        self.mmc.setProperty(self.core, 'Shutter', self.EPIshutter)
        self.mmc.setProperty(self.filter, 'State', self.filter_index - 1)
        self.mmc.setExposure(self.camera, self.exposure_ms)
        self.mmc.setProperty(self.lightpath, 'Label', self.camerapath)
        self.mmc.waitForDevice(self.filter)
        self.mmc.waitForSystem()

        self.mmc.initializeCircularBuffer()
        self.mmc.prepareSequenceAcquisition(self.camera)
        self.mmc.waitForDevice(self.EPIshutter)
        self.mmc.waitForDevice(self.camera)
        # 0 = as fast as possible, not a fixed interval - see VideoThread.run()
        # for why a nonzero value here silently caps fps below what a shorter
        # exposure could otherwise achieve.
        self.mmc.startContinuousSequenceAcquisition(0)

        x, y, w, h = self.roi_rect

        while self._run_flag:
            if not self.mmc.isSequenceRunning():
                self.status_signal.emit("EPI sequence stopped unexpectedly, exiting run loop")
                break
            if self.mmc.getRemainingImageCount() > 0:
                try:
                    raw_buf      = self.mmc.getLastImage()
                    image_width  = self.mmc.getImageWidth()
                    image_height = self.mmc.getImageHeight()
                except Exception as e:
                    self.status_signal.emit(f"frame grab error - {e}")
                    continue

                # raw uint16, native orientation (same convention as VideoThread)
                frame = np.frombuffer(raw_buf, dtype=np.uint16).reshape((image_height, image_width)).T
                self.frame_index += 1

                roi = frame[y:y + h, x:x + w]
                metric_value = self._compute_metric(roi)

                if self._state == "IDLE" and metric_value >= self._trigger_level:
                    self._state = "TRIGGERED"
                    self.event_count += 1
                    # Fire FIRST, before any disk I/O - this is the only
                    # latency-critical action. Saving the TIFF and logging
                    # the CSV row used to happen inline here, ahead of the
                    # trigger; that disk I/O could add tens of ms in front
                    # of the electrode command, which was enough for a
                    # droplet to pass the trap before it fired.
                    self.fire_sort_pulse_async()
                    fname = f"frame_{self.frame_index:06d}_{time.strftime('%Y%m%d_%H%M%S')}.tiff"
                    self._save_and_log_async(frame, fname, metric_value)
                    self.detection_signal.emit(frame, metric_value, self.frame_index)
                elif self._state == "TRIGGERED" and metric_value < self._reset_level:
                    self._state = "IDLE"

                self.metric_signal.emit(metric_value, self.frame_index, self._state)
                # Reused for both live display AND recording below - same
                # single rescale_intensity() call snap_EPI_image() uses, so
                # a recorded video frame is a fixed, deterministic function
                # of what's on screen, not a second independent stretch.
                display = exposure.rescale_intensity(frame)
                self.change_pixmap_signal.emit(display)

                if self._record_flag:
                    # Only a fast, non-blocking enqueue here - the actual
                    # JPEG encode + disk write happens on _video_writer_loop's
                    # own thread (see start_recording), so recording can
                    # never compete with or delay detection/the sort pulse.
                    self._video_queue.put(display.copy())
            else:
                QtCore.QThread.msleep(5)   # avoid busy-spin when buffer is empty

        if self._record_flag:
            self.stop_recording()

        self.mmc.stopSequenceAcquisition(self.camera)
        self.mmc.clearCircularBuffer()
        self.mmc.setProperty(self.EPIshutter, 'State', 0)
        set_voltage('Low')     # back to idle baseline in case we stopped mid-pulse
        send_to_arduino(3)     # TTL_Signal_OFF - disable the voltage generator when monitoring stops

    def stop(self):
        self._run_flag = False
        self.wait()


# ─────────────────────────────────────────────
#  Calibration stack recorder
# ─────────────────────────────────────────────
class StackRecorderThread(QThread):
    """
    Records a burst of raw EPI frames at the configured filter/exposure for
    duration_s and saves them as a single multi-page TIFF stack - the same
    kind of file Fiji opens natively as a scrollable stack. Used to capture
    a representative sample of droplets flowing past so the user can step
    through slices afterward and pick ROI / detect / reset threshold values
    without needing droplets to be flowing live at that moment.
    """
    change_pixmap_signal = pyqtSignal(np.ndarray)
    progress_signal = pyqtSignal(int)     # frames captured so far

    def __init__(self, filter_index, exposure_ms, duration_s, save_path):
        super().__init__()
        self._run_flag = True
        # Result is published as an attribute rather than via a custom
        # "finished" signal emitted from inside run(). A signal emitted from
        # run() fires while the thread is STILL RUNNING, so a handler that
        # drops the last reference to this object lets Python GC a live
        # QThread ("QThread: Destroyed while thread is still running" ->
        # crash). Callers read saved_path from QThread's built-in finished
        # signal instead, which is emitted only after run() has returned.
        self.saved_path = ""

        self.mmc        = Microscope['mmc']
        self.camera     = self.mmc.getCameraDevice()
        self.core       = 'Core'
        self.EPIshutter = 'TIEpiShutter'
        self.filter     = 'TIFilterBlock1'
        self.lightpath  = 'TILightPath'
        self.camerapath = '2-Left100'

        self.filter_index = filter_index
        self.exposure_ms  = exposure_ms
        self.duration_s   = duration_s
        self.save_path    = save_path
        self.frames       = []

    def run(self):
        self.mmc.setProperty(self.core, 'Shutter', self.EPIshutter)
        self.mmc.setProperty(self.filter, 'State', self.filter_index - 1)
        self.mmc.setExposure(self.camera, self.exposure_ms)
        self.mmc.setProperty(self.lightpath, 'Label', self.camerapath)
        self.mmc.waitForDevice(self.filter)
        self.mmc.waitForSystem()

        self.mmc.initializeCircularBuffer()
        self.mmc.prepareSequenceAcquisition(self.camera)
        self.mmc.waitForDevice(self.EPIshutter)
        self.mmc.waitForDevice(self.camera)
        self.mmc.startContinuousSequenceAcquisition(0)   # as fast as possible, not a fixed interval

        start_time = time.time()
        while self._run_flag and (time.time() - start_time) < self.duration_s:
            if not self.mmc.isSequenceRunning():
                break
            if self.mmc.getRemainingImageCount() > 0:
                try:
                    raw_buf      = self.mmc.getLastImage()
                    image_width  = self.mmc.getImageWidth()
                    image_height = self.mmc.getImageHeight()
                except Exception:
                    continue
                frame = np.frombuffer(raw_buf, dtype=np.uint16).reshape((image_height, image_width)).T
                self.frames.append(frame.copy())
                self.change_pixmap_signal.emit(exposure.rescale_intensity(frame))
                self.progress_signal.emit(len(self.frames))
            else:
                QtCore.QThread.msleep(5)

        self.mmc.stopSequenceAcquisition(self.camera)
        self.mmc.clearCircularBuffer()
        self.mmc.setProperty(self.EPIshutter, 'State', 0)

        if self.frames:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            tiff.imwrite(self.save_path, np.stack(self.frames, axis=0), photometric='minisblack')
            self.saved_path = self.save_path

    def stop(self):
        self._run_flag = False
        self.wait()


# ═══════════════════════════════════════════════════════════
#  MAIN GUI
# ═══════════════════════════════════════════════════════════
class MicroscopeControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_thread = None
        self.epi_thread   = None
        self.stack_thread = None
        self.roi_rect     = None   # (x, y, w, h) in full-frame pixel coords, set via ROI dialog
        self._init_microscope()
        self._build_ui()
        self.setWindowTitle('Microscope Control')
        self.resize(1700, 900)
        self.show()

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
        self.filterNames = {1:'1- FITC', 2:'2- DAPI', 3:'3- BFP-A',
                            4:'4- Cy5',  5:'5- Cy3',  6:'6- DIA'}
        # camera setup
        self.mmc.setProperty(self.camera, 'Sensor Cooler', 'ON')
        self.mmc.setProperty(self.camera, 'Exposure', 20)
        self.mmc.setProperty(self.camera, 'MINIMUM ACQUISITION TIMEOUT', 500)
        self.mmc.setProperty(self.camera, 'Binning', '4x4')
        self.mmc.setProperty(self.camera, 'ScanMode', 1)
        self.mmc.setProperty(self.camera, 'CONVERSION FACTOR COEFF', 0.5)
        self.mmc.setProperty(self.camera, 'PixelType', '16bit')
        # Print the camera's real exposure range once at startup, so it's
        # visible in the console without needing a separate script/console
        # to query it - see getPropertyLowerLimit/getPropertyUpperLimit below.
        self.dia_exposure_min = 1.0
        if self.mmc.hasPropertyLimits(self.camera, 'Exposure'):
            self.dia_exposure_min = self.mmc.getPropertyLowerLimit(self.camera, 'Exposure')
            exp_hi = self.mmc.getPropertyUpperLimit(self.camera, 'Exposure')
            print(f"[Camera] '{self.camera}' Exposure range: {self.dia_exposure_min} - {exp_hi} ms")
        else:
            print(f"[Camera] '{self.camera}' Exposure property has no queryable limits on this adapter.")
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
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(10, 10, 10, 10)

        scope_widget   = QWidget()
        sorting_widget = QWidget()

        self._build_microscope_panel(scope_widget)
        self._build_fl_sorting_panel(sorting_widget)

        root.addWidget(scope_widget,   1)
        root.addWidget(sorting_widget, 1)

    # ══════════════════════════════════════════
    #  Microscope Control panel
    # ══════════════════════════════════════════
    def _build_microscope_panel(self, parent):
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
            btn.setStyleSheet(BTN_BLUE)
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
            btn.setStyleSheet(BTN_PURPLE)
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
        for btn, style in [(self.snap_Button,   BTN_BLUE),
                           (self.live_Button,   BTN_RED),
                           (self.save_Button,   BTN_BLUE),
                           (self.record_button, BTN_RED)]:
            btn.setStyleSheet(style)
        self.snap_Button.clicked.connect(self.snap_DIA_image)
        self.live_Button.clicked.connect(self.startstoplive_imaging)
        self.save_Button.clicked.connect(self.save_image)
        self.record_button.clicked.connect(self.handle_record_button)
        for btn in (self.snap_Button, self.live_Button, self.save_Button, self.record_button):
            cap_layout.addWidget(btn)

        # -- Video recording exposure (dynamically adjustable, not hardcoded)
        video_exp_row = QHBoxLayout()
        video_exp_lbl = QLabel(f"Video exposure (ms, camera min {self.dia_exposure_min:.2f}):")
        video_exp_lbl.setStyleSheet("color:#aaa;")
        self.dia_exposure_input = QLineEdit("50")
        video_exp_row.addWidget(video_exp_lbl)
        video_exp_row.addWidget(self.dia_exposure_input)

        viewer_layout = QVBoxLayout()
        viewer_layout.setSpacing(4)
        viewer_layout.addLayout(cap_layout)
        viewer_layout.addLayout(video_exp_row)
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
            btn.setStyleSheet(BTN_BLUE)
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

        root.addLayout(left, 1)

    # ══════════════════════════════════════════
    #  FL Sorting panel
    # ══════════════════════════════════════════
    def _build_fl_sorting_panel(self, parent):
        root = QHBoxLayout(parent)
        root.setSpacing(10)
        root.setContentsMargins(10, 10, 10, 10)

        # ── LEFT COLUMN ────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        # -- Channel & exposure
        ce_layout = QHBoxLayout(); ce_layout.setSpacing(6)
        self.quick_EPI_filter   = QSpinBox(); self.quick_EPI_filter.setRange(1, 6); self.quick_EPI_filter.setValue(4)
        self.quick_EPI_exposure = QLineEdit("100")
        self.snap_EPI_button    = QPushButton("Snap Fluorescent Image")
        self.snap_EPI_button.setStyleSheet(BTN_BLUE)
        self.snap_EPI_button.clicked.connect(
            lambda: self.snap_EPI_image(self.quick_EPI_filter.value(), int(self.quick_EPI_exposure.text())))
        ce_lbl_f = QLabel("Filter:"); ce_lbl_f.setStyleSheet("color:#aaa;")
        ce_lbl_e = QLabel("Exposure (ms):"); ce_lbl_e.setStyleSheet("color:#aaa;")
        ce_layout.addWidget(ce_lbl_f)
        ce_layout.addWidget(self.quick_EPI_filter)
        ce_layout.addWidget(ce_lbl_e)
        ce_layout.addWidget(self.quick_EPI_exposure)
        ce_layout.addWidget(self.snap_EPI_button)
        left.addWidget(group("Channel & Exposure", ce_layout))

        # -- ROI
        roi_layout = QVBoxLayout(); roi_layout.setSpacing(4)
        self.roi_button = QPushButton("Define ROI…")
        self.roi_button.setStyleSheet(BTN_BLUE)
        self.roi_button.clicked.connect(self.define_roi)
        self.roi_label = QLabel("ROI: not set")
        self.roi_label.setStyleSheet("color:#aaa;")
        roi_layout.addWidget(self.roi_button)
        roi_layout.addWidget(self.roi_label)
        left.addWidget(group("Region of Interest", roi_layout))

        # -- Calibration stack: record a burst of frames and browse them
        # slice-by-slice (like a Fiji stack) to pick ROI/thresholds offline.
        cal_layout = QVBoxLayout(); cal_layout.setSpacing(4)
        cal_dur_row = QHBoxLayout()
        cal_dur_lbl = QLabel("Duration (s):"); cal_dur_lbl.setStyleSheet("color:#aaa;")
        self.stack_duration_input = QLineEdit("10")
        cal_dur_row.addWidget(cal_dur_lbl)
        cal_dur_row.addWidget(self.stack_duration_input)
        cal_layout.addLayout(cal_dur_row)

        cal_btn_row = QHBoxLayout()
        self.record_stack_button = QPushButton("Record Calibration Stack")
        self.stop_stack_button   = QPushButton("Stop")
        self.record_stack_button.setStyleSheet(BTN_GREEN)
        self.stop_stack_button.setStyleSheet(BTN_RED)
        self.stop_stack_button.setEnabled(False)
        self.record_stack_button.clicked.connect(self.record_calibration_stack)
        self.stop_stack_button.clicked.connect(self.stop_calibration_stack_recording)
        cal_btn_row.addWidget(self.record_stack_button)
        cal_btn_row.addWidget(self.stop_stack_button)
        cal_layout.addLayout(cal_btn_row)

        self.browse_stack_button = QPushButton("Browse Stack for Calibration…")
        self.browse_stack_button.setStyleSheet(BTN_BLUE)
        self.browse_stack_button.clicked.connect(self.browse_stack_for_calibration)
        cal_layout.addWidget(self.browse_stack_button)
        left.addWidget(group("Calibration Stack", cal_layout))

        # -- Detection settings
        det_grid = QGridLayout(); det_grid.setSpacing(4)
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([
            "Mean intensity", "Max intensity", "% pixels above threshold",
            "% of ROI ≥ Detect Threshold",
        ])
        self.detect_threshold_input   = QLineEdit("500")
        self.reset_threshold_input    = QLineEdit("300")
        self.pixel_cutoff_input       = QLineEdit("500")
        self.coverage_trigger_input   = QLineEdit("20")
        self.coverage_reset_input     = QLineEdit("10")
        self.pulse_duration_input     = QLineEdit("0.5")
        for row, (lbl, w) in enumerate([
            ("Metric:",                     self.metric_combo),
            ("Detect threshold:",           self.detect_threshold_input),
            ("Reset threshold:",            self.reset_threshold_input),
            ("Per-pixel intensity cutoff (used by % metric only):", self.pixel_cutoff_input),
            ("Coverage % to trigger (≥ Detect Thresh. mode only):", self.coverage_trigger_input),
            ("Coverage % to reset (≥ Detect Thresh. mode only):",   self.coverage_reset_input),
            ("Pulse duration (s):",         self.pulse_duration_input),
        ]):
            l = QLabel(lbl); l.setStyleSheet("color:#aaa;")
            det_grid.addWidget(l, row, 0)
            det_grid.addWidget(w, row, 1)
        left.addWidget(group("Detection Settings", det_grid))

        # -- Save directory
        dir_layout = QHBoxLayout(); dir_layout.setSpacing(4)
        self.directory_input = QLineEdit()
        self.directory_input.setPlaceholderText("Save directory…")
        self.browse_button   = QPushButton("Browse")
        self.browse_button.setStyleSheet(BTN_BLUE)
        self.browse_button.clicked.connect(self.browse_folder)
        dir_layout.addWidget(self.directory_input, 1)
        dir_layout.addWidget(self.browse_button)
        left.addWidget(group("Save Directory", dir_layout))

        left.addStretch()

        # ── RIGHT COLUMN ───────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)

        # -- Run control
        run_layout = QVBoxLayout(); run_layout.setSpacing(6)
        self.start_monitor_button = QPushButton("▶  Start Monitoring")
        self.stop_monitor_button  = QPushButton("■  Stop Monitoring")
        self.start_monitor_button.setStyleSheet(BTN_GREEN)
        self.stop_monitor_button.setStyleSheet(BTN_RED)
        self.start_monitor_button.setMinimumHeight(36)
        self.stop_monitor_button.setMinimumHeight(36)
        self.stop_monitor_button.setEnabled(False)
        self.start_monitor_button.clicked.connect(self.start_monitoring)
        self.stop_monitor_button.clicked.connect(self.stop_monitoring)
        run_layout.addWidget(self.start_monitor_button)
        run_layout.addWidget(self.stop_monitor_button)

        # Video recording, start/stoppable independently while monitoring
        # keeps running - saved into the same run folder as everything else.
        self.start_record_epi_button = QPushButton("● Start Recording")
        self.stop_record_epi_button  = QPushButton("■ Stop Recording")
        self.start_record_epi_button.setStyleSheet(BTN_BLUE)
        self.stop_record_epi_button.setStyleSheet(BTN_RED)
        self.start_record_epi_button.setEnabled(False)
        self.stop_record_epi_button.setEnabled(False)
        self.start_record_epi_button.clicked.connect(self.start_epi_recording)
        self.stop_record_epi_button.clicked.connect(self.stop_epi_recording)
        run_layout.addWidget(self.start_record_epi_button)
        run_layout.addWidget(self.stop_record_epi_button)

        self.sorting_status_label = QLabel("Status: idle")
        self.sorting_status_label.setStyleSheet("color:#ffcc44; font-size:11px;")
        run_layout.addWidget(self.sorting_status_label)
        right.addWidget(group("Run Control", run_layout))

        # -- Manual Arduino actuation
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
        right.addWidget(group("Manual Arduino Actuation", volt_layout))

        # -- Live readout
        live_layout = QVBoxLayout(); live_layout.setSpacing(4)
        self.metric_value_label = QLabel("Metric: —   State: IDLE")
        self.metric_value_label.setStyleSheet("color:#ccc;")
        live_layout.addWidget(self.metric_value_label)

        self.metric_fig = Figure(figsize=(4, 2.2))
        self.metric_canvas = FigureCanvas(self.metric_fig)
        self.metric_ax = self.metric_fig.add_subplot(111)
        self.metric_ax.set_facecolor("#1e1e1e")
        self.metric_fig.patch.set_facecolor("#1e1e1e")
        self.metric_ax.tick_params(colors="#aaaaaa", labelsize=8)
        for spine in self.metric_ax.spines.values():
            spine.set_color("#555555")
        self._metric_history = []
        self._metric_line, = self.metric_ax.plot([], [], color="#2ac555", linewidth=1)
        self._detect_line = self.metric_ax.axhline(0, color="#bb283a", linewidth=1, linestyle="--")
        self._reset_line  = self.metric_ax.axhline(0, color="#d4a017", linewidth=1, linestyle="--")
        live_layout.addWidget(self.metric_canvas)
        right.addWidget(group("Live Readout", live_layout), 1)

        right.addStretch()

        root.addLayout(left,  1)
        root.addLayout(right, 1)

    # ══════════════════════════════════════════
    #  Microscope slots
    # ══════════════════════════════════════════
    def startstoplive_imaging(self):
        if self.live_Button.isChecked():
            try:
                exposure_ms = float(self.dia_exposure_input.text())
            except ValueError:
                QMessageBox.warning(self, "Invalid input", "Video exposure must be a number.")
                self.live_Button.setChecked(False)
                return
            self.live_Button.setStyleSheet(BTN_GREEN)
            self.video_thread = VideoThread(exposure_ms=exposure_ms)
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
        if hasattr(self, 'live_Button'):
            self.live_Button.setChecked(False)
            self.live_Button.setStyleSheet(BTN_RED)

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

    def define_roi(self):
        """
        Blocking dialog: snap one EPI frame at the configured filter/exposure
        and let the user drag out a rectangle with matplotlib's
        RectangleSelector. Shows a live ImageJ-style mean/min/max/std readout
        of the *raw* (unstretched) pixel values inside the current rectangle -
        the same raw counts EpiMonitorThread's mean-intensity metric computes
        on - so "Use as Detect/Reset Threshold" copies a number that's
        directly comparable to what the detector will actually see. On
        accept, stores self.roi_rect = (x, y, w, h) in full-frame pixel
        coordinates for EpiMonitorThread to crop against.
        """
        filt = self.quick_EPI_filter.value()
        exp  = int(self.quick_EPI_exposure.text())
        raw  = self.snap_EPI_image(filt, exp)
        display = exposure.rescale_intensity(raw)
        img_h, img_w = raw.shape[:2]

        dialog = QDialog(self)
        dialog.setWindowTitle("Define ROI — drag to draw a rectangle, Enter to accept")
        dialog.resize(800, 900)
        layout = QVBoxLayout(dialog)

        fig    = Figure(figsize=(7, 7))
        canvas = FigureCanvas(fig)
        ax     = fig.add_subplot(111)
        ax.imshow(display, cmap="gray")
        ax.set_title("Drag to draw the ROI rectangle, then press Enter or Accept")
        layout.addWidget(canvas)

        info = QLabel("No rectangle drawn yet.")
        info.setStyleSheet("color:#aaa; font-size:11px;")
        layout.addWidget(info)

        stats_row = QHBoxLayout()
        set_detect_btn = QPushButton("Use mean as Detect Threshold")
        set_reset_btn  = QPushButton("Use mean as Reset Threshold")
        set_cutoff_btn = QPushButton("Use mean as Pixel Cutoff")
        set_detect_btn.setStyleSheet(BTN_BLUE)
        set_reset_btn.setStyleSheet(BTN_BLUE)
        set_cutoff_btn.setStyleSheet(BTN_BLUE)
        set_detect_btn.setEnabled(False)
        set_reset_btn.setEnabled(False)
        set_cutoff_btn.setEnabled(False)
        stats_row.addWidget(set_detect_btn)
        stats_row.addWidget(set_reset_btn)
        stats_row.addWidget(set_cutoff_btn)
        layout.addLayout(stats_row)

        accept_btn = QPushButton("Accept ROI (or press Enter)")
        accept_btn.setStyleSheet(BTN_GREEN)
        accept_btn.clicked.connect(dialog.accept)
        layout.addWidget(accept_btn)

        extents = [None]
        result_box = [None]   # holds the last roi_mean_stats() tuple

        def _onselect(eclick, erelease):
            extents[0] = selector.extents
            stats = roi_mean_stats(raw, selector.extents, img_w, img_h)
            result_box[0] = stats
            if stats is None:
                info.setText("ROI too small.")
                set_detect_btn.setEnabled(False)
                set_reset_btn.setEnabled(False)
                set_cutoff_btn.setEnabled(False)
                return
            info.setText(stats[5])
            set_detect_btn.setEnabled(True)
            set_reset_btn.setEnabled(True)
            set_cutoff_btn.setEnabled(True)

        selector = RectangleSelector(
            ax, _onselect, useblit=True,
            button=[1], minspanx=5, minspany=5,
            spancoords='pixels', interactive=True,
        )

        def _use_as_detect():
            if result_box[0] is not None:
                self.detect_threshold_input.setText(f"{result_box[0][4]:.1f}")
        def _use_as_reset():
            if result_box[0] is not None:
                self.reset_threshold_input.setText(f"{result_box[0][4]:.1f}")
        def _use_as_cutoff():
            if result_box[0] is not None:
                self.pixel_cutoff_input.setText(f"{result_box[0][4]:.1f}")
        set_detect_btn.clicked.connect(_use_as_detect)
        set_reset_btn.clicked.connect(_use_as_reset)
        set_cutoff_btn.clicked.connect(_use_as_cutoff)

        def _onkey(ev):
            if ev.key == "enter":
                dialog.accept()
        fig.canvas.mpl_connect("key_press_event", _onkey)

        result = dialog.exec_()
        if result != QDialog.Accepted or result_box[0] is None:
            QMessageBox.warning(self, "ROI not set", "No rectangle was drawn; ROI unchanged.")
            return

        x0, y0, x1, y1, _mean, _info = result_box[0]
        self.roi_rect = (x0, y0, x1 - x0, y1 - y0)
        self.roi_label.setText(f"ROI: x={x0}, y={y0}, w={x1 - x0}, h={y1 - y0}")

    # ══════════════════════════════════════════
    #  Calibration stack (record + browse like a Fiji stack)
    # ══════════════════════════════════════════
    def record_calibration_stack(self):
        if self.stack_thread is not None and self.stack_thread.isRunning():
            return
        try:
            duration    = float(self.stack_duration_input.text())
            exposure_ms = int(self.quick_EPI_exposure.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Duration and exposure must be numbers.")
            return
        if duration <= 0:
            QMessageBox.warning(self, "Invalid duration", "Duration must be a positive number of seconds.")
            return

        save_dir = self.directory_input.text().strip()
        if not save_dir:
            QMessageBox.warning(self, "No save directory", "Choose a save directory first.")
            return

        self._stop_live_video()

        stack_dir = os.path.join(save_dir, "calibration_stacks")
        fname     = f"stack_{time.strftime('%Y%m%d_%H%M%S')}.tiff"
        save_path = os.path.join(stack_dir, fname)

        self.stack_thread = StackRecorderThread(
            filter_index=self.quick_EPI_filter.value(),
            exposure_ms=exposure_ms,
            duration_s=duration,
            save_path=save_path,
        )
        self.stack_thread.change_pixmap_signal.connect(self.update_image)
        self.stack_thread.progress_signal.connect(self.on_stack_progress)
        # QThread.finished (not a custom signal emitted from run()) so the
        # handler can safely release the thread - see StackRecorderThread.
        self.stack_thread.finished.connect(self.on_stack_recorded)
        self.stack_thread.start()

        self.record_stack_button.setEnabled(False)
        self.stop_stack_button.setEnabled(True)
        self.browse_stack_button.setEnabled(False)
        self.start_monitor_button.setEnabled(False)
        self.live_Button.setEnabled(False)
        self.snap_Button.setEnabled(False)
        self.record_button.setEnabled(False)
        self.sorting_status_label.setText("Status: recording calibration stack…")

    def stop_calibration_stack_recording(self):
        if self.stack_thread is not None and self.stack_thread.isRunning():
            self.stack_thread.stop()

    @pyqtSlot(int)
    def on_stack_progress(self, count):
        self.sorting_status_label.setText(f"Status: recording calibration stack… {count} frames")

    @pyqtSlot()
    def on_stack_recorded(self):
        # Runs on QThread.finished, i.e. after run() has fully returned, so
        # releasing self.stack_thread here can't GC a live thread. Holding a
        # local ref also keeps the object alive for the whole handler.
        thread = self.stack_thread
        if thread is None:
            return
        # Frame count / duration give the actual achieved fps - the direct,
        # empirical answer to "is this exposure too slow" rather than a guess.
        n_frames = len(thread.frames)
        duration = thread.duration_s
        path     = thread.saved_path
        self.stack_thread = None
        self.record_stack_button.setEnabled(True)
        self.stop_stack_button.setEnabled(False)
        self.browse_stack_button.setEnabled(True)
        self.start_monitor_button.setEnabled(True)
        self.live_Button.setEnabled(True)
        self.snap_Button.setEnabled(True)
        self.record_button.setEnabled(True)

        if not path:
            self.sorting_status_label.setText("Status: calibration recording failed (no frames captured)")
            return

        achieved_fps = n_frames / duration if duration > 0 else 0.0
        self.sorting_status_label.setText(
            f"Status: calibration stack saved ({n_frames} frames, {achieved_fps:.1f} fps) to {path}")

        reply = QMessageBox.question(
            self, "Stack recorded",
            f"Saved {path}\n\n{n_frames} frames in {duration:.1f}s  =  {achieved_fps:.1f} fps.\n\n"
            f"Open it now to pick ROI/thresholds?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self._open_stack_calibration(path)

    def browse_stack_for_calibration(self):
        start_dir = self.directory_input.text().strip() or "."
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Stack for Calibration", start_dir,
            "TIFF stacks (*.tif *.tiff);;All Files (*)")
        if path:
            self._open_stack_calibration(path)

    def _open_stack_calibration(self, path):
        """
        Blocking dialog: load a multi-page TIFF stack and let the user step
        through slices with a slider (like Fiji's stack scrollbar) while a
        RectangleSelector ROI stays fixed across slices - the readout below
        updates live for whichever slice is showing, so you can watch a
        single ROI's mean intensity rise and fall as a droplet passes
        through, and pick detect/reset thresholds directly off that.
        """
        try:
            stack = tiff.imread(path)
        except Exception as e:
            QMessageBox.critical(self, "Failed to open stack", str(e))
            return
        if stack.ndim == 2:
            stack = stack[np.newaxis, ...]
        if stack.ndim != 3:
            QMessageBox.critical(self, "Invalid stack",
                                  f"Expected a 2-D or 3-D TIFF stack, got shape {stack.shape}.")
            return

        n_frames = stack.shape[0]
        img_h, img_w = stack.shape[1:]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Calibrate from stack — {os.path.basename(path)} ({n_frames} slices)")
        dialog.resize(850, 950)
        layout = QVBoxLayout(dialog)

        fig    = Figure(figsize=(7, 7))
        canvas = FigureCanvas(fig)
        ax     = fig.add_subplot(111)
        im = ax.imshow(exposure.rescale_intensity(stack[0]), cmap="gray")
        ax.set_title("Drag to draw ROI. Step through slices with the slider or arrow keys.")
        layout.addWidget(canvas)

        slice_row   = QHBoxLayout()
        prev_btn    = QPushButton("◀ Prev")
        slider      = QSlider(Qt.Horizontal)
        next_btn    = QPushButton("Next ▶")
        slice_label = QLabel(f"Slice: 1 / {n_frames}")
        slice_label.setStyleSheet("color:#aaa;")
        slider.setRange(0, n_frames - 1)
        slider.setValue(0)
        slice_row.addWidget(prev_btn)
        slice_row.addWidget(slider, 1)
        slice_row.addWidget(next_btn)
        slice_row.addWidget(slice_label)
        layout.addLayout(slice_row)

        info = QLabel("No rectangle drawn yet.")
        info.setStyleSheet("color:#aaa; font-size:11px;")
        layout.addWidget(info)

        stats_row = QHBoxLayout()
        set_detect_btn = QPushButton("Use mean as Detect Threshold")
        set_reset_btn  = QPushButton("Use mean as Reset Threshold")
        set_cutoff_btn = QPushButton("Use mean as Pixel Cutoff")
        set_detect_btn.setStyleSheet(BTN_BLUE)
        set_reset_btn.setStyleSheet(BTN_BLUE)
        set_cutoff_btn.setStyleSheet(BTN_BLUE)
        set_detect_btn.setEnabled(False)
        set_reset_btn.setEnabled(False)
        set_cutoff_btn.setEnabled(False)
        stats_row.addWidget(set_detect_btn)
        stats_row.addWidget(set_reset_btn)
        stats_row.addWidget(set_cutoff_btn)
        layout.addLayout(stats_row)

        accept_btn = QPushButton("Accept ROI (or press Enter)")
        accept_btn.setStyleSheet(BTN_GREEN)
        accept_btn.clicked.connect(dialog.accept)
        layout.addWidget(accept_btn)

        extents    = [None]
        result_box = [None]
        cur_idx    = [0]

        def _refresh_stats():
            if extents[0] is None:
                return
            stats = roi_mean_stats(stack[cur_idx[0]], extents[0], img_w, img_h)
            result_box[0] = stats
            if stats is None:
                info.setText("ROI too small.")
                set_detect_btn.setEnabled(False)
                set_reset_btn.setEnabled(False)
                set_cutoff_btn.setEnabled(False)
                return
            info.setText(f"Slice {cur_idx[0] + 1}/{n_frames}   {stats[5]}")
            set_detect_btn.setEnabled(True)
            set_reset_btn.setEnabled(True)
            set_cutoff_btn.setEnabled(True)

        def _onselect(eclick, erelease):
            extents[0] = selector.extents
            _refresh_stats()

        selector = RectangleSelector(
            ax, _onselect, useblit=True,
            button=[1], minspanx=5, minspany=5,
            spancoords='pixels', interactive=True,
        )

        def _goto_slice(idx):
            idx = max(0, min(n_frames - 1, idx))
            cur_idx[0] = idx
            im.set_data(exposure.rescale_intensity(stack[idx]))
            slice_label.setText(f"Slice: {idx + 1} / {n_frames}")
            slider.blockSignals(True)
            slider.setValue(idx)
            slider.blockSignals(False)
            canvas.draw_idle()
            _refresh_stats()

        slider.valueChanged.connect(_goto_slice)
        prev_btn.clicked.connect(lambda: _goto_slice(cur_idx[0] - 1))
        next_btn.clicked.connect(lambda: _goto_slice(cur_idx[0] + 1))

        def _use_as_detect():
            if result_box[0] is not None:
                self.detect_threshold_input.setText(f"{result_box[0][4]:.1f}")
        def _use_as_reset():
            if result_box[0] is not None:
                self.reset_threshold_input.setText(f"{result_box[0][4]:.1f}")
        def _use_as_cutoff():
            if result_box[0] is not None:
                self.pixel_cutoff_input.setText(f"{result_box[0][4]:.1f}")
        set_detect_btn.clicked.connect(_use_as_detect)
        set_reset_btn.clicked.connect(_use_as_reset)
        set_cutoff_btn.clicked.connect(_use_as_cutoff)

        def _onkey(ev):
            if ev.key == "enter":
                dialog.accept()
            elif ev.key == "right":
                _goto_slice(cur_idx[0] + 1)
            elif ev.key == "left":
                _goto_slice(cur_idx[0] - 1)
        fig.canvas.mpl_connect("key_press_event", _onkey)

        result = dialog.exec_()
        if result != QDialog.Accepted or result_box[0] is None:
            return

        x0, y0, x1, y1, _mean, _info = result_box[0]
        self.roi_rect = (x0, y0, x1 - x0, y1 - y0)
        self.roi_label.setText(f"ROI: x={x0}, y={y0}, w={x1 - x0}, h={y1 - y0}")

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
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.image_Live.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if self.roi_rect is not None:
            self._draw_roi_overlay(pixmap, w, h)
        self.image_Live.setPixmap(pixmap)

    def _draw_roi_overlay(self, pixmap, orig_w, orig_h):
        """Draws self.roi_rect on top of an already-scaled pixmap, in place."""
        x, y, w, h = self.roi_rect
        scale_x = pixmap.width()  / orig_w
        scale_y = pixmap.height() / orig_h
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(QtGui.QColor(255, 200, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(int(x * scale_x), int(y * scale_y),
                          int(w * scale_x), int(h * scale_y))
        painter.end()

    # ══════════════════════════════════════════
    #  FL Sorting slots
    # ══════════════════════════════════════════
    def start_monitoring(self):
        if self.roi_rect is None:
            QMessageBox.warning(self, "No ROI", "Define an ROI before starting monitoring.")
            return
        if self.epi_thread is not None and self.epi_thread.isRunning():
            return

        try:
            detect_threshold = float(self.detect_threshold_input.text())
            reset_threshold  = float(self.reset_threshold_input.text())
            pixel_cutoff     = float(self.pixel_cutoff_input.text())
            coverage_trigger = float(self.coverage_trigger_input.text())
            coverage_reset   = float(self.coverage_reset_input.text())
            pulse_duration   = float(self.pulse_duration_input.text())
            exposure_ms      = int(self.quick_EPI_exposure.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid input",
                                 "Thresholds, pixel cutoff, coverage %, exposure, and pulse duration must be numbers.")
            return

        metric_map = {0: "mean", 1: "max", 2: "pct_above_thresh", 3: "pct_above_detect"}
        metric_key = metric_map[self.metric_combo.currentIndex()]

        if metric_key == "pct_above_detect":
            if coverage_reset >= coverage_trigger:
                QMessageBox.warning(self, "Invalid thresholds",
                                     "Coverage % to reset must be lower than coverage % to trigger.")
                return
            trigger_line_val, reset_line_val = coverage_trigger, coverage_reset
        else:
            if reset_threshold >= detect_threshold:
                QMessageBox.warning(self, "Invalid thresholds",
                                     "Reset threshold must be lower than detect threshold.")
                return
            trigger_line_val, reset_line_val = detect_threshold, reset_threshold

        save_dir = self.directory_input.text().strip()
        if not save_dir:
            QMessageBox.warning(self, "No save directory", "Choose a save directory first.")
            return

        self._stop_live_video()

        self._metric_history = []
        self._detect_line.set_ydata([trigger_line_val, trigger_line_val])
        self._reset_line.set_ydata([reset_line_val, reset_line_val])

        self.epi_thread = EpiMonitorThread(
            filter_index=self.quick_EPI_filter.value(),
            exposure_ms=exposure_ms,
            roi_rect=self.roi_rect,
            metric=metric_key,
            pixel_cutoff=pixel_cutoff,
            detect_threshold=detect_threshold,
            reset_threshold=reset_threshold,
            pulse_duration_s=pulse_duration,
            save_dir=save_dir,
            coverage_trigger_pct=coverage_trigger,
            coverage_reset_pct=coverage_reset,
        )
        self.epi_thread.change_pixmap_signal.connect(self.update_image)
        self.epi_thread.metric_signal.connect(self.on_metric_update)
        self.epi_thread.detection_signal.connect(self.on_detection)
        self.epi_thread.status_signal.connect(self.on_sorting_status)
        self.epi_thread.finished.connect(self._on_monitor_stopped_ui)
        self.epi_thread.start()

        self.start_monitor_button.setEnabled(False)
        self.stop_monitor_button.setEnabled(True)
        self.start_record_epi_button.setEnabled(True)
        self.stop_record_epi_button.setEnabled(False)
        self.record_stack_button.setEnabled(False)
        self.browse_stack_button.setEnabled(False)
        self.live_Button.setEnabled(False)
        self.snap_Button.setEnabled(False)
        self.record_button.setEnabled(False)
        self.sorting_status_label.setText("Status: monitoring")

    def stop_monitoring(self):
        if self.epi_thread is not None and self.epi_thread.isRunning():
            self.epi_thread.stop()   # releases any open video writer as part of its own cleanup
        self.epi_thread = None
        self._on_monitor_stopped_ui()

    def _on_monitor_stopped_ui(self):
        self.start_monitor_button.setEnabled(True)
        self.stop_monitor_button.setEnabled(False)
        self.start_record_epi_button.setEnabled(False)
        self.stop_record_epi_button.setEnabled(False)
        self.record_stack_button.setEnabled(True)
        self.browse_stack_button.setEnabled(True)
        self.live_Button.setEnabled(True)
        self.snap_Button.setEnabled(True)
        self.record_button.setEnabled(True)
        self.sorting_status_label.setText("Status: idle")

    def start_epi_recording(self):
        if self.epi_thread is not None and self.epi_thread.isRunning():
            self.epi_thread.start_recording()
            self.start_record_epi_button.setEnabled(False)
            self.stop_record_epi_button.setEnabled(True)
            self.sorting_status_label.setText("Status: monitoring (recording video)")

    def stop_epi_recording(self):
        if self.epi_thread is not None and self.epi_thread.isRunning():
            self.epi_thread.stop_recording()
        self.start_record_epi_button.setEnabled(True)
        self.stop_record_epi_button.setEnabled(False)
        self.sorting_status_label.setText("Status: monitoring")

    def alter_Arduino_state(self, checked):
        if checked:
            self.TurnOnVolts.setText('Volts ON')
            self.TurnOnVolts.setStyleSheet(BTN_GREEN)
            send_to_arduino(2)
        else:
            self.TurnOnVolts.setText('Voltage Signal')
            self.TurnOnVolts.setStyleSheet(BTN_RED)
            send_to_arduino(3)

    @pyqtSlot(float, int, str)
    def on_metric_update(self, value, frame_idx, state):
        self.metric_value_label.setText(f"Metric: {value:.1f}   State: {state}")
        self._metric_history.append(value)
        if len(self._metric_history) > 200:
            self._metric_history = self._metric_history[-200:]
        xs = list(range(len(self._metric_history)))
        self._metric_line.set_data(xs, self._metric_history)
        self.metric_ax.set_xlim(0, max(10, len(xs)))
        ymax = max(self._metric_history + [self._detect_line.get_ydata()[0]]) * 1.1
        self.metric_ax.set_ylim(0, max(ymax, 1))
        if frame_idx % 3 == 0:
            self.metric_canvas.draw_idle()

    @pyqtSlot(np.ndarray, float, int)
    def on_detection(self, frame, value, frame_idx):
        self.sorting_status_label.setText(f"Status: TRIGGERED (metric={value:.1f} @ frame {frame_idx})")
        self.image_Live.setStyleSheet(
            "background-color: #111111; border: 3px solid #2ac555; border-radius: 4px;")
        QTimer.singleShot(400, self._clear_detection_flash)

    def _clear_detection_flash(self):
        self.image_Live.setStyleSheet("background-color: #111111; border-radius: 4px;")

    @pyqtSlot(str)
    def on_sorting_status(self, msg):
        print(f"[FL-SORT] {msg}")
        self.sorting_status_label.setText(f"Status: {msg}")

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


    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            os.chdir(folder)
            self.directory_input.setText(folder)

    def closeEvent(self, event):
        if self.epi_thread is not None and self.epi_thread.isRunning():
            self.epi_thread.stop()   # blocks until its own cleanup (shutter/voltage) finishes
        if self.stack_thread is not None and self.stack_thread.isRunning():
            self.stack_thread.stop()
        # Belt-and-suspenders: force voltage low and shutter closed even if
        # the monitor thread never ran or exited abnormally. TTL_Signal_OFF
        # covers the separate manual actuation panel, in case it was left on.
        send_to_arduino(4)     # VOLTAGE_low
        send_to_arduino(3)     # TTL_Signal_OFF
        self.mmc.setProperty(self.EPIshutter, 'State', 0)
        arduino.close()
        event.accept()
# ─────────────────────────────────────────────
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setPalette(make_dark_palette())
    app.setStyleSheet(WIDGET_STYLE)
    window = MicroscopeControlGUI()
    sys.exit(app.exec_())



