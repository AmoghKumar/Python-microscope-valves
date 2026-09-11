import os
import time
from pymmcore_plus import CMMCorePlus
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QScrollArea, QTabWidget, QFileDialog,
    QRadioButton, QFrame, QSpinBox, QLineEdit, QCheckBox, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QInputDialog, QGridLayout, QSizePolicy,
    QGroupBox, QSplitter
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
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import copy
import tifffile as tiff
import torch
import shutil
from glob import glob
from sam2.build_sam import build_sam2_video_predictor

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
    arduino.write(f"{data}\n".encode())
    time.sleep(0.1)
    response = arduino.readline().decode().strip()
    print(f"Arduino Response: {response}" if response else "No response received.")

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
#  SAM2Config  –  edit paths / thresholds before use
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
#  FL droplet segmentation  –  no SAM2, no annotation required
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


class SAM2Config:
    CHECKPOINT     = "C:\SAM2/sam2.1_hiera_base_plus.pt"
    MODEL_CONFIG   = "C:\SAM2/sam2.1_hiera_b+.yaml"
    DEVICE         = "cuda" if torch.cuda.is_available() else "cpu"
    OBJ_ID         = 1
    MIN_COMP_AREA  = 200    # px² – discard mask fragments smaller than this
    AREA_THRESHOLD = 0.80   # trigger chemostat when area < 70 % of initial
    BF_EXPOSURE_MS = 20     # ms – brightfield snap exposure


# ═══════════════════════════════════════════════════════════════════════════
#  SAM2Manager  –  all SAM2 logic, completely decoupled from the GUI
# ═══════════════════════════════════════════════════════════════════════════

class SAM2Manager:
    """
    Owns the SAM2 video predictor and all per-position tracking state.

    Per-position state (dicts keyed by 0-based position index):
        ref_image_path  – path to the initial BF TIFF used during annotation
        ref_mask        – cleaned boolean ndarray produced by annotation
        initial_area    – droplet area (px) recorded from ref_mask
        loop_bf_paths   – ordered list of BF TIFFs snapped in the *current*
                          loop; reset to [] after each trigger
        pos_loop_count  – number of completed loops (0 = never triggered,
                          so currently in "Loop 1")
    """

    def __init__(self):
        self.predictor      = None   # loaded lazily on first use
        self.base_dir       = "."

        self.ref_image_path = {}   # {idx: str}
        self.ref_mask       = {}   # {idx: np.ndarray bool}
        self.initial_area   = {}   # {idx: int px}
        self.loop_bf_paths  = {}   # {idx: list[str]}
        self.pos_loop_count = {}   # {idx: int}

    # ── predictor ──────────────────────────────────────────────────────────
    def load_predictor(self):
        if self.predictor is None:
            print("[SAM2] Loading predictor …")
            self.predictor = build_sam2_video_predictor(
                SAM2Config.MODEL_CONFIG,
                SAM2Config.CHECKPOINT,
                device=SAM2Config.DEVICE,
            )
            print("[SAM2] Predictor ready.")

    # ── image helpers ───────────────────────────────────────────────────────
    @staticmethod
    def load_gray_uint8(path: str) -> np.ndarray:
        """Read any TIFF/PNG → normalised uint8 grayscale 2-D array."""
        img = tiff.imread(path)
        if img.ndim > 2:
            img = img[..., 0]
        img = img.astype(np.float32)
        return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    @staticmethod
    def write_sam2_frame_folder(image_paths: list, folder: str) -> str:
        """
        Write a numbered JPG sequence into `folder` that SAM2 expects.
        The folder is wiped and rebuilt each call so frame indices always
        match the supplied image_paths list exactly.
        """
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
        for i, p in enumerate(image_paths):
            gray = SAM2Manager.load_gray_uint8(p)
            rgb  = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            cv2.imwrite(
                os.path.join(folder, f"{i:05d}.jpg"),
                cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
            )
        return folder

    # ── mask post-processing ────────────────────────────────────────────────
    def clean_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        1. Remove connected components smaller than MIN_COMP_AREA.
        2. Bridge electrode-split regions with a convex hull.
        3. Morphological closing to smooth edges.
        Returns a boolean array.
        """
        u8 = mask.astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(u8, 8)
        cleaned = np.zeros_like(u8)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] >= SAM2Config.MIN_COMP_AREA:
                cleaned[labels == i] = 1

        contours, _ = cv2.findContours(
            cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return cleaned.astype(bool)
        hull   = cv2.convexHull(np.vstack(contours))
        filled = np.zeros_like(cleaned)
        cv2.drawContours(filled, [hull], -1, 1, -1)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        filled = cv2.morphologyEx(filled, cv2.MORPH_CLOSE, kernel)
        return filled.astype(bool)

    # ── interactive annotation ──────────────────────────────────────────────
    def annotate_frame_interactive(self, gray: np.ndarray, inference_state) -> np.ndarray:
        """
        Blocking matplotlib window for point-click annotation.
          Left-click   = positive point (droplet interior)
          Middle-click = negative point (background / electrode)
          Right-click  = undo last point
          Enter        = accept mask and close

        Returns the cleaned boolean mask.
        Raises RuntimeError if closed without any annotation.
        """
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        import matplotlib.pyplot as plt

        predictor = self.predictor
        points    = []
        labels    = []
        cur_mask  = [None]
        mask_art  = [None]
        pt_arts   = []

        # ── build dialog ──────────────────────────────────────────
        dialog = QDialog()
        dialog.setWindowTitle("Annotate droplet – Left=droplet  Middle=background  Right=undo  Enter=accept")
        dialog.resize(900, 900)
        layout = QVBoxLayout(dialog)

        fig    = Figure(figsize=(8, 8))
        canvas = FigureCanvas(fig)
        ax     = fig.add_subplot(111)
        ax.imshow(gray, cmap="gray")
        ax.set_title("Left = droplet  |  Middle = background  |  Right = undo  |  Enter = accept")
        layout.addWidget(canvas)

        info = QLabel("Click to annotate. Press Enter to accept.")
        info.setStyleSheet("color:#aaa; font-size:11px;")
        layout.addWidget(info)

        accept_btn = QPushButton("Accept mask (or press Enter)")
        accept_btn.setStyleSheet("background-color:#2ac555; color:white; padding:6px;")
        accept_btn.clicked.connect(dialog.accept)
        layout.addWidget(accept_btn)

        # ── annotation helpers ────────────────────────────────────
        def _redraw_points():
            for a in pt_arts:
                a.remove()
            pt_arts.clear()
            for (x, y), lab in zip(points, labels):
                pt_arts.append(
                    ax.plot(x, y, "go" if lab == 1 else "ro", markersize=7)[0]
                )

        def _run_sam2():
            if not points:
                return
            pt_arr = np.array(points, dtype=np.float32)
            lb_arr = np.array(labels, dtype=np.int32)
            ctx = (
                torch.autocast("cuda", dtype=torch.bfloat16)
                if SAM2Config.DEVICE == "cuda"
                else torch.autocast("cpu", enabled=False)
            )
            with torch.inference_mode(), ctx:
                _, _, logits = predictor.add_new_points_or_box(
                    inference_state=inference_state,
                    frame_idx=0,
                    obj_id=SAM2Config.OBJ_ID,
                    points=pt_arr,
                    labels=lb_arr,
                )
            raw = (logits[0] > 0).cpu().numpy()
            cur_mask[0] = np.squeeze(raw).astype(bool)

            if mask_art[0] is not None:
                mask_art[0].remove()
            ov = np.zeros((*cur_mask[0].shape, 4), dtype=np.float32)
            ov[cur_mask[0]] = [1.0, 0.35, 0.0, 0.45]
            mask_art[0] = ax.imshow(ov)
            _redraw_points()
            canvas.draw()

        def _onclick(ev):
            if ev.inaxes != ax or ev.xdata is None:
                return
            x, y = float(ev.xdata), float(ev.ydata)
            if ev.button == 1:
                points.append([x, y]); labels.append(1)
            elif ev.button == 2:
                points.append([x, y]); labels.append(0)
            elif ev.button == 3:
                if not points:
                    return
                points.pop(); labels.pop()
                if not points:
                    if mask_art[0] is not None:
                        mask_art[0].remove(); mask_art[0] = None
                    _redraw_points(); canvas.draw(); return
            _run_sam2()

        def _onkey(ev):
            if ev.key == "enter":
                dialog.accept()

        fig.canvas.mpl_connect("button_press_event", _onclick)
        fig.canvas.mpl_connect("key_press_event",    _onkey)

        # ── run the dialog (blocks inside the existing Qt event loop) ──
        result = dialog.exec_()

        if cur_mask[0] is None:
            raise RuntimeError("No annotation given – add at least one positive point.")
        return self.clean_mask(cur_mask[0])

    # ── SAM2 propagation helpers ────────────────────────────────────────────
    def _autocast_ctx(self):
        if SAM2Config.DEVICE == "cuda":
            return torch.autocast("cuda", dtype=torch.bfloat16)
        return torch.autocast("cpu", enabled=False)

    def _seed_state_with_mask(self, state, frame_idx: int, mask: np.ndarray):
        with torch.inference_mode(), self._autocast_ctx():
            self.predictor.add_new_mask(
                inference_state=state,
                frame_idx=frame_idx,
                obj_id=SAM2Config.OBJ_ID,
                mask=mask,   # full boolean mask, not just centroid
            )

    def measure_area_with_context(
        self, pos_idx: int, new_bf_path: str
    ) -> tuple:
        """
        Measure the droplet area in `new_bf_path` using a SAM2 inference
        context built from:

            frame 0          →  initial BF  (seeded with ref_mask centroid)
            frames 1 … N     →  all BF images already in current loop
            frame N+1        →  new_bf_path  (the frame we want to predict)

        The initial frame is always frame 0 and always seeded with the
        reference mask, regardless of how many loop frames have accumulated.

        Returns (cleaned_mask: np.ndarray[bool], area_px: int).
        """
        self.load_predictor()

        ref_img   = self.ref_image_path[pos_idx]
        ref_mask  = self.ref_mask[pos_idx]
        loop_imgs = self.loop_bf_paths.get(pos_idx, [])

        # Full ordered frame list  [initial] + [loop so far] + [new frame]
        all_frames      = [ref_img] + loop_imgs + [new_bf_path]
        query_frame_idx = len(all_frames) - 1

        # Write the numbered JPG folder SAM2 needs
        tmp_dir = os.path.join(self.base_dir, f"_sam2_tmp_pos{pos_idx}")
        self.write_sam2_frame_folder(all_frames, tmp_dir)

        state = self.predictor.init_state(video_path=tmp_dir)

        # Seed frame 0 (initial BF) with the reference mask centroid
        self._seed_state_with_mask(state, frame_idx=0, mask=ref_mask)

        # Propagate forward; keep only the prediction at the query frame
        final_mask = None
        with torch.inference_mode(), self._autocast_ctx():
            for out_idx, _, out_logits in self.predictor.propagate_in_video(
                state,
                start_frame_idx=0,
                max_frame_num_to_track=len(all_frames),
            ):
                if out_idx == query_frame_idx:
                    raw        = (out_logits[0] > 0).cpu().numpy()
                    final_mask = np.squeeze(raw).astype(bool)

        if final_mask is None:
            return np.zeros_like(ref_mask, dtype=bool), 0

        cleaned = self.clean_mask(final_mask)
        return cleaned, int(cleaned.sum())

    # ── context management ──────────────────────────────────────────────────
    def append_loop_bf(self, pos_idx: int, path: str):
        """Add a newly captured BF to this position's current-loop list."""
        self.loop_bf_paths.setdefault(pos_idx, []).append(path)

    def reset_loop_context(self, pos_idx: int):
        """
        Called after a trigger.  Discards all current-loop BF images so the
        next loop starts with only the initial frame as context.
        """
        self.loop_bf_paths[pos_idx] = []



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

    def __init__(self):
        super().__init__()
        self._run_flag    = True
        self._record_flag = False
        self._lock        = QtCore.QMutex()          # FIX: guards self.out across threads
        self.out          = None
        self.video_directory = "C:/Users/Cell Culture Scope/Downloads/Videos"
        self.video_filename  = self.get_unique_filename(self.video_directory)
        self.fourcc      = cv2.VideoWriter_fourcc(*'MJPG')
        self.fps         = 10
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
        self.mmc.setProperty(self.camera, 'Exposure', 50)
        self.mmc.setProperty(self.core, 'Shutter', self.DIAshutter)
        self.mmc.setProperty(self.lightpath, 'Label', self.camerapath)
        self.mmc.initializeCircularBuffer()
        self.mmc.prepareSequenceAcquisition(self.camera)
        self.mmc.waitForDevice(self.DIAshutter)
        self.mmc.waitForDevice(self.camera)
        self.mmc.startContinuousSequenceAcquisition(100)
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



# ═══════════════════════════════════════════════════════════
#  MAIN GUI
# ═══════════════════════════════════════════════════════════
class MicroscopeControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.Numato_port  = Numato_device
        self.video_thread = None
        self.positions    = []
        self.sam2_mgr     = SAM2Manager()
        self.Buffer_inlet = 9   # default buffer inlet (1-9); updated from UI
        self.selected_exposures = []
        self.Chemostat_protocol_steps = []
        self.current_protocol_table_step = 0
        self._init_microscope()
        self._build_ui()
        self.setWindowTitle('Microscope Control')
        self.resize(1400, 860)
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
        tab2 = QWidget(); self.tabs.addTab(tab2, "Timelapse Setup")

        sam2_widget = QWidget()
        sam2_layout = QVBoxLayout(sam2_widget)
        self._build_sam2_panel(sam2_layout)
        self.tabs.addTab(sam2_widget, "SAM2 Tracking")

        fl_widget = QWidget()
        fl_layout = QVBoxLayout(fl_widget)
        self._build_fl_panel(fl_layout)
        self.tabs.addTab(fl_widget, "FL Segmentation")

        self._build_tab1(tab1)
        self._build_tab2(tab2)

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

        viewer_layout = QVBoxLayout()
        viewer_layout.setSpacing(4)
        viewer_layout.addLayout(cap_layout)
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
                           (self.replacePositionButton, BTN_BLUE),
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
        self.stop_all_button.setStyleSheet(BTN_BLACK)
        self.all_on_button   = QPushButton("All On")
        self.all_on_button.setStyleSheet(BTN_BLUE)
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

        right.addStretch()

        root.addLayout(left, 3)
        root.addLayout(right, 2)

    # ══════════════════════════════════════════
    #  TAB 2 — Timelapse Setup
    # ══════════════════════════════════════════
    def _build_tab2(self, parent):
        root = QHBoxLayout(parent)
        root.setSpacing(10)
        root.setContentsMargins(10, 10, 10, 10)

        # ── LEFT COLUMN ────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        # -- Filter / exposure table
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
        self.snap_EPI_button.setStyleSheet(BTN_BLUE)
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

        # -- Protocol definition
        proto_top = QHBoxLayout()
        proto_top.setSpacing(10)

        # inputs spinboxes
        # Valid inlet pairs for the binary multiplexer:
        # Two inlets are safe to combine only if they share at least one valve
        # (same group-A valve OR same group-B valve). If they differ in both
        # groups, 4 distinct valves open, inadvertently activating 4 inlets.
        self._valid_inlet_pairs = {
            1: [1, 2, 3, 4, 7],
            2: [1, 2, 3, 5, 8],
            3: [1, 2, 3, 6, 9],
            4: [1, 4, 5, 6, 7],
            5: [2, 4, 5, 6, 8],
            6: [3, 4, 5, 6, 9],
            7: [1, 4, 7, 8, 9],
            8: [2, 5, 7, 8, 9],
            9: [3, 6, 7, 8, 9],
        }

        inp_layout = QGridLayout(); inp_layout.setSpacing(4)
        self.Chemostat_inputs = []
        for i in range(4):
            lbl = QLabel(f"Input {i+1}:"); lbl.setStyleSheet("color:#aaa;")
            sb  = QSpinBox(); sb.setRange(0, 9); sb.setValue(0)
            inp_layout.addWidget(lbl, i, 0)
            inp_layout.addWidget(sb,  i, 1)
            self.Chemostat_inputs.append(sb)

        # Label that shows which input2 values are valid given current input1
        self._valid_i2_label = QLabel("Valid input 2: —")
        self._valid_i2_label.setStyleSheet("color:#ffcc44; font-size:11px;")
        self._valid_i2_label.setWordWrap(True)
        inp_layout.addWidget(self._valid_i2_label, 4, 0, 1, 2)

        def _update_valid_i2_label(val):
            if val == 0:
                self._valid_i2_label.setText("Valid input 2: —")
            else:
                valid = self._valid_inlet_pairs.get(val, [])
                self._valid_i2_label.setText(f"Valid input 2: {valid}")
        self.Chemostat_inputs[0].valueChanged.connect(_update_valid_i2_label)

        proto_top.addWidget(group("Inputs", inp_layout))

        # chemostat checkboxes
        chem_layout = QVBoxLayout(); chem_layout.setSpacing(2)
        self.Chemostats = []
        for i in range(8):
            cb = QCheckBox(f"Chemostat {i+1}"); cb.setStyleSheet("color:#ccc;")
            chem_layout.addWidget(cb); self.Chemostats.append(cb)
        proto_top.addWidget(group("Chemostats", chem_layout))

        # step buttons
        step_btn_layout = QVBoxLayout(); step_btn_layout.setSpacing(6)
        self.add_Step_button    = QPushButton("Add Step");        self.add_Step_button.setStyleSheet(BTN_GREEN)
        self.clear_last_button  = QPushButton("Clear Last Step"); self.clear_last_button.setStyleSheet(BTN_BLUE)
        self.clear_Steps_button = QPushButton("Clear All Steps"); self.clear_Steps_button.setStyleSheet(BTN_RED)
        self.export_button      = QPushButton("Export to CSV");   self.export_button.setStyleSheet(BTN_BLACK)
        self.add_Step_button.clicked.connect(self.add_loading_step)
        self.clear_last_button.clicked.connect(self.clear_last_step)
        self.clear_Steps_button.clicked.connect(self.clear_all_steps)
        self.export_button.clicked.connect(self.export_to_csv)
        for btn in (self.add_Step_button, self.clear_last_button, self.clear_Steps_button, self.export_button):
            step_btn_layout.addWidget(btn)
        step_btn_layout.addStretch()
        proto_top.addWidget(group("Actions", step_btn_layout))
        left.addWidget(group("Protocol Definition", proto_top))

        # -- Protocol table (scrollable)
        self.Chemostat_protocol_table = QTableWidget()
        self.Chemostat_protocol_table.setRowCount(10)
        self.Chemostat_protocol_table.setColumnCount(8)
        self.Chemostat_protocol_table.setVerticalHeaderLabels(
            ["Input 1", "Input 2"] + [f"Chemostat {i+1}" for i in range(8)])
        for c in range(8):
            self.Chemostat_protocol_table.setHorizontalHeaderItem(c, QTableWidgetItem(f"Step {c+1}"))
        for c in range(8):
            for r in range(10):
                if r < 2:
                    self.Chemostat_protocol_table.setItem(r, c, QTableWidgetItem(""))
                else:
                    self.Chemostat_protocol_table.setCellWidget(r, c, self.create_centered_checkbox())
        self.Chemostat_protocol_table.setStyleSheet("QTableWidget { gridline-color: #444; }")
        self.Chemostat_protocol_table.verticalHeader().setDefaultSectionSize(24)
        proto_tbl_layout = QVBoxLayout()
        proto_tbl_layout.addWidget(self.Chemostat_protocol_table)
        left.addWidget(group("Protocol Steps", proto_tbl_layout))
        left.addStretch()

        # ── RIGHT COLUMN ───────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)

        # -- Experiment timing
        timing_grid = QGridLayout(); timing_grid.setSpacing(6)
        self.cycle_Interval_Input = QLineEdit("0")
        self.cycle_Input          = QLineEdit("0")
        for r, (lbl, w) in enumerate([
            ("Cycle interval (min):",      self.cycle_Interval_Input),
            ("Total duration (min):",      self.cycle_Input)
        ]):
            l = QLabel(lbl); l.setStyleSheet("color:#aaa;")
            timing_grid.addWidget(l, r, 0)
            timing_grid.addWidget(w, r, 1)
        self.interval = 0; self.cycles = 0
        right.addWidget(group("Timing", timing_grid))

        # -- Directory
        dir_layout = QHBoxLayout(); dir_layout.setSpacing(4)
        self.directory_input = QLineEdit()
        self.directory_input.setPlaceholderText("Save directory…")
        self.browse_button   = QPushButton("Browse")
        self.browse_button.setStyleSheet(BTN_BLUE)
        self.browse_button.clicked.connect(self.browse_folder)
        dir_layout.addWidget(self.directory_input, 1)
        dir_layout.addWidget(self.browse_button)
        right.addWidget(group("Save Directory", dir_layout))

        

        # -- Experiment control
        exp_layout = QVBoxLayout(); exp_layout.setSpacing(6)
        self.start_experiment_button = QPushButton("▶  Start Experiment")
        self.stop_experiment_button  = QPushButton("■  Stop Experiment")
        self.start_experiment_button.setStyleSheet(BTN_GREEN)
        self.stop_experiment_button.setStyleSheet(BTN_RED)
        self.start_experiment_button.setMinimumHeight(36)
        self.stop_experiment_button.setMinimumHeight(36)
        self.start_experiment_button.clicked.connect(self._on_start_experiment)
        exp_layout.addWidget(self.start_experiment_button)
        exp_layout.addWidget(self.stop_experiment_button)
        right.addWidget(group("Experiment Control", exp_layout))

        right.addStretch()

        root.addLayout(left,  3)
        root.addLayout(right, 1)

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
        if state:
            self.controls[idx].setStyleSheet(BTN_GREEN)
            self.send_relay_command(f"relay off {relay_id}")
        else:
            self.controls[idx].setStyleSheet(BTN_RED)
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
        for i, ctrl in enumerate(self.controls):
            ctrl.setStyleSheet(BTN_GREEN); ctrl.setChecked(True)
            self.send_relay_command(f"relay off {self.get_relay_id(i)}")
        self.send_relay_command('close all')

    def send_relay_command(self, command):
        if self.Numato_port and self.Numato_port.is_open:
            try:
                self.Numato_port.write(f"{command}\r".encode('utf-8'))
                time.sleep(0.005)
            except serial.SerialException:
                QMessageBox.critical(self, 'Error', 'Failed to communicate with the device')

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

    def create_centered_checkbox(self):
        frame  = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        cb = QCheckBox(frame); cb.setEnabled(False)
        layout.addWidget(cb)
        return frame

    def add_loading_step(self):
        selected_inputs = [sb.value() for sb in self.Chemostat_inputs if sb.value() > 0]
        ring_status     = [cb.isChecked() for cb in self.Chemostats]
        if not selected_inputs and not any(ring_status):
            return

        # Validate inlet pair against binary multiplexer constraints.
        # Two inlets must share at least one valve to avoid inadvertently
        # opening additional inlets via the multiplexer.
        if len(selected_inputs) >= 2:
            i1_val, i2_val = selected_inputs[0], selected_inputs[1]
            valid_for_i1 = self._valid_inlet_pairs.get(i1_val, [])
            if i2_val not in valid_for_i1:
                QMessageBox.warning(
                    self, "Invalid inlet combination",
                    f"Inlet {i2_val} cannot be combined with inlet {i1_val}.\n\n"
                    f"With the binary multiplexer, opening both would activate "
                    f"additional inlets unintentionally.\n\n"
                    f"Valid choices for input 2 when input 1 = {i1_val}:\n"
                    f"{valid_for_i1}"
                )
                return

        step = {
            "input1": selected_inputs[0] if len(selected_inputs) > 0 else "",
            "input2": selected_inputs[1] if len(selected_inputs) > 1 else "",
            "rings":  ring_status
        }
        self.Chemostat_protocol_steps.append(step)
        col = self.current_protocol_table_step
        i1 = QTableWidgetItem(str(step["input1"])); i1.setTextAlignment(Qt.AlignCenter)
        i2 = QTableWidgetItem(str(step["input2"])); i2.setTextAlignment(Qt.AlignCenter)
        self.Chemostat_protocol_table.setItem(0, col, i1)
        self.Chemostat_protocol_table.setItem(1, col, i2)
        for i, is_on in enumerate(step["rings"]):
            cb = QCheckBox(); cb.setChecked(is_on); cb.setEnabled(False)
            w  = QWidget(); lyt = QVBoxLayout(w)
            lyt.setContentsMargins(0, 0, 0, 0)
            lyt.setAlignment(cb, Qt.AlignCenter)
            lyt.addWidget(cb)
            self.Chemostat_protocol_table.setCellWidget(2 + i, col, w)
        self.current_protocol_table_step += 1

    def clear_all_steps(self):
        self.Chemostat_protocol_steps = []
        self.current_protocol_table_step = 0
        for c in range(self.Chemostat_protocol_table.columnCount()):
            for r in range(self.Chemostat_protocol_table.rowCount()):
                if r < 2:
                    self.Chemostat_protocol_table.setItem(r, c, QTableWidgetItem(""))
                else:
                    self.Chemostat_protocol_table.setCellWidget(r, c, self.create_centered_checkbox())

    def clear_last_step(self):
        if not self.Chemostat_protocol_steps:
            return
        self.Chemostat_protocol_steps.pop()
        self.current_protocol_table_step = max(0, self.current_protocol_table_step - 1)
        col = self.current_protocol_table_step
        for r in range(self.Chemostat_protocol_table.rowCount()):
            if r < 2:
                self.Chemostat_protocol_table.setItem(r, col, QTableWidgetItem(""))
            else:
                frame = self.Chemostat_protocol_table.cellWidget(r, col)
                if frame:
                    cb = frame.layout().itemAt(0).widget()
                    if cb: cb.setChecked(False)

    def export_to_csv(self):
        if not self.Chemostat_protocol_steps:
            return
        fp, _ = QFileDialog.getSaveFileName(self, "Save Sequence to CSV", "",
                                             "CSV Files (*.csv);;All Files (*)")
        if not fp:
            return
        with open(fp, mode="w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Step","Input 1","Input 2"] + [f"Ring {i+1}" for i in range(8)])
            for idx, step in enumerate(self.Chemostat_protocol_steps, 1):
                w.writerow([f"Step {idx}", step["input1"], step["input2"]]
                           + ["ON" if s else "OFF" for s in step["rings"]])

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            os.chdir(folder)
            self.directory_input.setText(folder)
    
    def _fl_status(self, msg: str):
        """Update the FL segmentation status label and print to console."""
        print(f"[FL-SEG] {msg}")
        if hasattr(self, "fl_status_label"):
            self.fl_status_label.setText(f"Status: {msg}")
            QApplication.processEvents()

    def _build_fl_panel(self, parent_layout):
        """Build the FL Segmentation tab."""
        info = QLabel(
            "SAM2-free segmentation mode — no pre-experiment annotation needed.\n\n"
            "Every imaging interval:\n"
            "  • FL image taken at every position (first filter/exposure\n"
            "    from the exposure table is used for segmentation;\n"
            "    all filters are saved)\n"
            "  • Droplet segmented via Otsu threshold + electrode bridge\n"
            f"  • Chemostat triggered if area < "
            f"{SAM2Config.AREA_THRESHOLD * 100:.0f}% of initial area\n\n"
            "Each position tracks its own loop counter independently.\n"
            "Set imaging interval and total duration in the Timing panel."
        )
        info.setStyleSheet("color:#aaa; font-size:12px;")
        info.setWordWrap(True)
        parent_layout.addWidget(info)

        btn = QPushButton("▶  Start FL-segmentation timelapse")
        btn.setStyleSheet(BTN_GREEN)
        btn.setMinimumHeight(38)
        btn.clicked.connect(
            lambda: self.TimeLapse_Experiment_FL(
                interval_min=int(self.cycle_Interval_Input.text()),
                total_min=int(self.cycle_Input.text()),
            )
        )
        parent_layout.addWidget(btn)

        self.fl_status_label = QLabel("Status: idle")
        self.fl_status_label.setStyleSheet("color:#ffcc44; font-size:11px;")
        parent_layout.addWidget(self.fl_status_label)
        parent_layout.addStretch()

    def TimeLapse_Experiment_FL(self, interval_min: int, total_min: int):
        """
        FL-segmentation timelapse — no SAM2, no pre-annotation required.

        Every `interval_min` minutes for `total_min` total minutes:
          1. Move to every position and snap FL images for all filters
             defined in the exposure table.
             The FIRST filter/exposure entry is used for segmentation;
             all filter images are saved as raw uint16 TIFFs.
          2. segment_droplet_fl() segments the droplet and measures its area.
             The segmentation overlay is saved alongside the TIFF for inspection.
          3. Initial area is recorded on the very first tick.
          4. From tick 2 onwards, if area < AREA_THRESHOLD × initial:
               – Chemostat protocol runs for that position.
               – That position's loop counter increments.

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
        if not self.positions:
            QMessageBox.warning(self, "No positions",
                                "Save at least one stage position first.")
            return
        if not self.selected_exposures:
            QMessageBox.warning(self, "No exposures",
                                "Set at least one filter/exposure in the "
                                "Timelapse Setup tab and click Save Values.")
            return
        if interval_min <= 0 or total_min <= 0:
            QMessageBox.warning(self, "Invalid timing",
                                "Set a non-zero interval and total duration.")
            return

        base         = self.directory_input.text().strip() or "."
        purge_dur    = float(self.purge_duration_Input.text())
        flow_dur     = float(self.flow_duration_Input.text())
        drive_dur    = float(self.drive_duration_Input.text())
        interval_sec = interval_min * 60
        total_sec    = total_min    * 60

        # Per-position state — all local, no SAM2Manager needed
        initial_areas  = {}   # {idx: int px}  – recorded on tick 1
        pos_loop_count = {}   # {idx: int}      – completed loops (0 → Loop 1)

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
                time.sleep(wait_for)

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
            seg_filt, seg_exp = self.selected_exposures[0]

            for idx, (px, py, pz) in enumerate(self.positions):
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
                _, seg_area, seg_overlay = segment_droplet_fl(raw_fl)
                overlay_fname = (
                    f"Pos{pos_num}_Loop{pos_loop}"
                    f"_filt{seg_filt}_{seg_exp}ms_{time_tag_str}_mask.png"
                )
                cv2.imwrite(os.path.join(fl_dir, overlay_fname), seg_overlay)
                time.sleep(0.2)

                # Record initial area on the very first tick
                if tick_number == 1:
                    initial_areas[idx] = seg_area
                    print(f"  Pos {pos_num}: initial area recorded = {seg_area} px")
                else:
                    ratio = seg_area / initial if initial > 0 else 1.0
                    print(
                        f"  Pos {pos_num}  Loop {pos_loop}: "
                        f"area = {seg_area} px  ({ratio * 100:.1f}% of initial  "
                        f"[threshold {SAM2Config.AREA_THRESHOLD * 100:.0f}%])"
                    )
                    if initial > 0 and seg_area < SAM2Config.AREA_THRESHOLD * initial:
                        triggered_positions.append(idx)
                        self._fl_status(
                            f"⚠ Pos {pos_num} TRIGGERED "
                            f"({ratio * 100:.1f}% < "
                            f"{SAM2Config.AREA_THRESHOLD * 100:.0f}%)"
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
            if len(self.selected_exposures) > 1:
                # Reset shutter state after chemostat protocol before imaging.
                # The chemostat sequence leaves the hardware in an uncertain
                # shutter state; explicitly closing both shutters and waiting
                # prevents waitForSystem() timing out on TIEpiShutter.
                self.mmc.setProperty(self.EPIshutter, 'State', 0)
                self.mmc.setProperty(self.DIAshutter, 'State', 0)
                self.mmc.waitForSystem()
                time.sleep(1.0)
                self._fl_status("Full exposure table imaging of all positions …")
                for idx, (px, py, pz) in enumerate(self.positions):
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

                    for filt, exp in self.selected_exposures[1:]:
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

            # ── chemostat protocol for triggered positions only ────────────
            if self.Chemostat_protocol_steps:
                self._fl_status("Running chemostat for triggered positions …")
                
                self.open_inlet(self.Buffer_inlet)
                time.sleep(2)
                self.close_inlet(self.Buffer_inlet)
                

                '''for inlet_range in range[1,9]:
                    self.open_inlet(inlet_range)
                    time.sleep(2)
                    self.close_inlet(inlet_range)
                self.control_valve(6, state=True)'''

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
                

                for step in self.Chemostat_protocol_steps:
                    i1    = step["input1"]
                    i2    = step["input2"]
                    rings = step["rings"]

                    pw = DropletWorker("purge", inlets=[i1, i2], purge_duration=purge_dur)
                    pw.start(); pw.wait()

                    for rn, active in enumerate(rings):
                        if active and (rn in triggered_positions):
                            px, py, pz = self.positions[rn]
                            self.mmc.setTimeoutMs(30000)
                            self.mmc.setXYPosition(px, py)
                            self.mmc.waitForDevice(self.mmc.getXYStageDevice())
                            self.mmc.setPosition(pz)
                            self.mmc.waitForDevice(self.mmc.getFocusDevice())
                            self.mmc.setTimeoutMs(5000)
                            time.sleep(0.3)

                            gw = DropletWorker("generate", inlets=[i1], flow_duration=flow_dur)
                            gw.start(); gw.wait()

                            if self.video_thread and self.video_thread.isRunning():
                                self.video_thread.start_recording()
                            else:
                                print(f"WARNING: VideoThread not running at "
                                      f"position {rn+1} – skipping recording")
                                continue

                            dw = DropletWorker(
                                "drive", i1,
                                drive_duration=drive_dur,
                                chemostat_number=rn + 1,
                            )
                            dw.start(); dw.wait()

                            if self.video_thread and self.video_thread.isRunning():
                                self.video_thread.stop_recording()
                            QtCore.QThread.msleep(200)

                    self.open_inlet(self.Buffer_inlet)
                    self.control_valve(6,  state=False)
                    time.sleep(1)
                    self.close_inlet(self.Buffer_inlet)
                    self.control_valve(6,  state=True)

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

    def _sam2_status(self, msg: str):
        """Update the SAM2 status label and print to console."""
        print(f"[SAM2] {msg}")
        if hasattr(self, "sam2_status_label"):
            self.sam2_status_label.setText(f"Status: {msg}")
            QApplication.processEvents()


    # ── 1. SAM2 tab builder ─────────────────────────────────────────────────────
    def _build_sam2_panel(self, parent_layout):
        """Build the SAM2 controls tab (called from __init__)."""
        info = QLabel(
            "① Capture one initial BF image per position (pre-experiment).\n"
            "② Annotate each image with SAM2 (live point-click preview).\n"
            "③ Start the SAM2-tracked timelapse.\n\n"
            f"Chemostat fires when a droplet shrinks below "
            f"{SAM2Config.AREA_THRESHOLD * 100:.0f}% of its initial area.\n"
            "Each position tracks its own loop counter independently.\n"
            "Use the Timing panel to set imaging interval and total duration."
        )
        info.setStyleSheet("color:#aaa; font-size:12px;")
        info.setWordWrap(True)
        parent_layout.addWidget(info)

        buttons = [
            ("① Capture initial BF for all positions",     BTN_BLUE,
            lambda: self.capture_bf_for_all_positions()),
            ("② Annotate all positions with SAM2",         BTN_BLUE,
            lambda: self.annotate_all_positions_sam2()),
            ("③ Start SAM2-tracked timelapse experiment",  BTN_GREEN,
            lambda: self.TimeLapse_Experiment_SAM2(
                interval_min=int(self.cycle_Interval_Input.text()),
                total_min=int(self.cycle_Input.text()),
            )),
        ]
        for label, style, slot in buttons:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.setMinimumHeight(36)
            btn.clicked.connect(slot)
            parent_layout.addWidget(btn)

        self.sam2_status_label = QLabel("Status: idle")
        self.sam2_status_label.setStyleSheet("color:#ffcc44; font-size:11px;")
        parent_layout.addWidget(self.sam2_status_label)
        parent_layout.addStretch()


    # ── 2. Step ①: capture initial BF images ───────────────────────────────────
    def capture_bf_for_all_positions(self):
        """
        For every saved stage position:
        • Move the stage to that position.
        • Snap one BF image.
        • Save as  <base>/Position_<N>/BF/PosN_initialBF.tiff
        Paths are stored in sam2_mgr for the annotation step.
        """
        if not self.positions:
            QMessageBox.warning(self, "No positions",
                                "Save at least one stage position first.")
            return

        base = self.directory_input.text().strip() or "."
        self.sam2_mgr.base_dir = base

        self.DIALamp_activate()

        for idx, (px, py, pz) in enumerate(self.positions):
            pos_num = idx + 1
            bf_dir  = os.path.join(base, f"Position_{pos_num}", "BF")
            os.makedirs(bf_dir, exist_ok=True)

            self._sam2_status(f"Moving to position {pos_num} …")
            self.mmc.setXYPosition(px, py)
            self.mmc.setPosition(pz)
            self.mmc.waitForSystem()
            time.sleep(0.6)

            self._sam2_status(f"Snapping initial BF for position {pos_num} …")
            
            raw_arr = self.snap_DIA_image()

            save_path = os.path.join(bf_dir, f"Pos{pos_num}_initialBF.tiff")
            tiff.imwrite(save_path, raw_arr)

            # Initialise per-position state
            self.sam2_mgr.ref_image_path[idx] = save_path
            self.sam2_mgr.loop_bf_paths[idx]  = []
            self.sam2_mgr.pos_loop_count[idx] = 0

            self._sam2_status(f"Pos {pos_num}: saved → {save_path}")

        self._sam2_status("Initial BF capture complete for all positions.")
        self.DIALamp_deactivate()
        QMessageBox.information(
            self, "Done",
            "Initial BF images captured for all positions.\n"
            "Proceed to Step ② to annotate.",
        )


    # ── 3. Step ②: SAM2 annotation ─────────────────────────────────────────────
    def annotate_all_positions_sam2(self):
        """
        For each position, open the initial BF image in a matplotlib window.
        The user annotates the droplet; the mask is saved as:
            <base>/Position_<N>/BF/PosN_initialMask.tiff
        and stored in sam2_mgr.ref_mask[idx].
        """
        if not self.sam2_mgr.ref_image_path:
            QMessageBox.warning(self, "No BF images",
                                "Capture initial BF images first (Step ①).")
            return

        self.sam2_mgr.load_predictor()

        for idx in sorted(self.sam2_mgr.ref_image_path):
            pos_num  = idx + 1
            img_path = self.sam2_mgr.ref_image_path[idx]
            bf_dir   = os.path.dirname(img_path)

            self._sam2_status(
                f"Annotate Pos {pos_num} – click droplet, press Enter to accept …"
            )

            gray = SAM2Manager.load_gray_uint8(img_path)

            # Build a single-frame SAM2 state purely for the annotation window
            tmp_dir = os.path.join(
                self.sam2_mgr.base_dir, f"_sam2_annotate_tmp_pos{idx}"
            )
            SAM2Manager.write_sam2_frame_folder([img_path], tmp_dir)
            state = self.sam2_mgr.predictor.init_state(video_path=tmp_dir)

            mask = self.sam2_mgr.annotate_frame_interactive(gray, state)
            self.sam2_mgr.ref_mask[idx]    = mask
            self.sam2_mgr.initial_area[idx] = int(mask.sum())

            mask_path = os.path.join(bf_dir, f"Pos{pos_num}_initialMask.tiff")
            tiff.imwrite(mask_path, mask.astype(np.uint8))

            self._sam2_status(
                f"Pos {pos_num} annotated – initial area = {mask.sum()} px"
            )

        self._sam2_status("All positions annotated. Ready for Step ③.")
        QMessageBox.information(self, "Done",
                                "All positions annotated. Ready to start.")


    # ── 4. Steps 3-6: SAM2-tracked timelapse ────────────────────────────────────
    def TimeLapse_Experiment_SAM2(self, interval_min: int, total_min: int):
        """
        Time-driven timelapse with per-position SAM2 tracking.

        Parameters
        ----------
        interval_min : int  – minutes between imaging rounds (e.g. 3)
        total_min    : int  – total experiment duration in minutes (e.g. 120)

        Loop structure
        ──────────────
        Every `interval_min` minutes:
        [Step 3]  BF-image ALL positions and measure droplet area via SAM2.
                    SAM2 context for position P = [initial_BF] +
                    [all BF images taken in P's *current* loop so far].
                    Append the new BF to P's current-loop context.
                    Save the new BF image and its SAM2 mask.

        [Step 4]  Identify positions where area < AREA_THRESHOLD × initial.

        [Step 5]  FL imaging of triggered positions only.

        [Step 6]  Chemostat protocol for triggered positions only.
                    After chemostat:
                    • Reset that position's loop-BF list (context → initial only).
                    • Increment that position's loop counter.
        """
        if not self.sam2_mgr.ref_mask:
            QMessageBox.warning(self, "Not annotated",
                                "Complete Steps ① and ② before starting.")
            return
        if not self.positions:
            QMessageBox.warning(self, "No positions", "No stage positions saved.")
            return
        
        if interval_min <= 0 or total_min <= 0:
            QMessageBox.warning(self, "Invalid timing",
                                "Set a non-zero interval and total duration before starting.")
            return

        base = self.directory_input.text().strip() or "."
        self.sam2_mgr.base_dir = base

        purge_dur    = float(self.purge_duration_Input.text())
        flow_dur     = float(self.flow_duration_Input.text())
        drive_dur    = float(self.drive_duration_Input.text())
        interval_sec = interval_min * 60
        total_sec    = total_min    * 60

        # ── Initialise valve state (identical to original TimeLapse_Experiment) ──
        init_states = [
            (0, False), (1, True),  (2, False), (3, True),  (4, True),  (5, False),
            (6, False), (7, True),  (8, False), (9, False),  (10, False), (11, False),
            (12, True), (13, True), (14, True), (15, True),
        ]
        for v, s in init_states:
            self.control_valve(v, state=s)

        experiment_start = time.time()
        tick_number      = 0   # counts how many imaging rounds have been done

        self._sam2_status(
            f"Experiment started – interval {interval_min} min / "
            f"total {total_min} min"
        )
        print(f"\n{'='*62}")
        print(f"  SAM2 TIMELAPSE  |  interval {interval_min} min  "
            f"|  total {total_min} min")
        print(f"{'='*62}")

        # ── outer timing loop ────────────────────────────────────────────────────
        while True:
            now               = time.time()
            elapsed_sec       = now - experiment_start

            # Stop when total time is reached
            if elapsed_sec >= total_sec:
                break

            # Sleep until the next tick is due
            next_due_sec = tick_number * interval_sec
            wait_for     = next_due_sec - elapsed_sec
            if wait_for > 0:
                self._sam2_status(
                    f"Waiting {wait_for:.0f} s until next imaging round …"
                )
                time.sleep(wait_for)

            # ── start of one imaging round ───────────────────────────────────────
            tick_number         += 1
            tick_wall_start      = time.time()
            elapsed_min          = (tick_wall_start - experiment_start) / 60.0

            # Round the elapsed time to the nearest interval for the filename tag
            # e.g. at 3.02 min with interval=3  →  "3min"
            time_tag_min  = round(elapsed_min / interval_min) * interval_min
            time_tag_str  = f"{time_tag_min:.0f}min"

            print(f"\n{'─'*62}")
            print(f"  Tick {tick_number}  |  ~{time_tag_min:.0f} min elapsed")
            print(f"{'─'*62}")

            triggered_positions = []   # positions whose area fell below threshold

            self.DIALamp_activate()

            # ── Step 3: BF image every position, measure area ────────────────────
            for idx, (px, py, pz) in enumerate(self.positions):
                pos_num  = idx + 1
                # pos_loop is the 1-based loop label shown in filenames
                pos_loop = self.sam2_mgr.pos_loop_count.get(idx, 0) + 1
                initial  = self.sam2_mgr.initial_area.get(idx, 0)

                bf_dir = os.path.join(base, f"Position_{pos_num}", "BF")
                os.makedirs(bf_dir, exist_ok=True)

                # e.g.  Pos1_Loop3_BF_6min.tiff
                bf_fname = f"Pos{pos_num}_Loop{pos_loop}_BF_{time_tag_str}.tiff"
                bf_path  = os.path.join(bf_dir, bf_fname)

                self._sam2_status(
                    f"BF snap – Pos {pos_num}  Loop {pos_loop}  @ {time_tag_str}"
                )
                self.mmc.setTimeoutMs(30000)
                self.mmc.setXYPosition(px, py)
                self.mmc.waitForDevice(self.mmc.getXYStageDevice())
                self.mmc.setPosition(pz)
                self.mmc.waitForDevice(self.mmc.getFocusDevice())
                time.sleep(0.3)

                raw_arr = self.snap_DIA_image()
                tiff.imwrite(bf_path, raw_arr)

                # ── SAM2 area measurement ─────────────────────────────────────────
                if idx not in self.sam2_mgr.ref_mask:
                    print(f"  Pos {pos_num}: no reference mask, skipping SAM2.")
                    continue

                mask, area = self.sam2_mgr.measure_area_with_context(idx, bf_path)

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                # Save the SAM2 mask for this time-point
                # e.g.  Pos1_Loop3_mask_6min.tiff
                mask_fname = (
                    f"Pos{pos_num}_Loop{pos_loop}_mask_{time_tag_str}.tiff"
                )
                tiff.imwrite(os.path.join(bf_dir, mask_fname),
                            mask.astype(np.uint8))

                # Append this BF to the current-loop context for future ticks
                self.sam2_mgr.append_loop_bf(idx, bf_path)

                ratio = area / initial if initial > 0 else 1.0
                print(
                    f"  Pos {pos_num}  Loop {pos_loop}: "
                    f"area = {area} px  ({ratio * 100:.1f}% of initial  "
                    f"[threshold {SAM2Config.AREA_THRESHOLD * 100:.0f}%])"
                )

                if initial > 0 and area < SAM2Config.AREA_THRESHOLD * initial:
                    triggered_positions.append(idx)
                    self._sam2_status(
                        f"⚠ Pos {pos_num} TRIGGERED "
                        f"({ratio * 100:.1f}% < "
                        f"{SAM2Config.AREA_THRESHOLD * 100:.0f}%)"
                    )

            self.DIALamp_deactivate()
            
            # ── Step 4: report triggered positions ──────────────────────────────
            if not triggered_positions:
                print("  ✓ All droplets within acceptable size.")
                self._sam2_status(
                    f"Tick {tick_number}: all areas OK. "
                    f"Next tick in ~{interval_min} min."
                )
                continue   # no FL imaging or chemostat needed this round

            names = [f"Pos {i + 1}" for i in triggered_positions]
            print(f"\n  ⚠ Triggered this tick: {', '.join(names)}")

            # ── Step 5: FL imaging of triggered positions only ───────────────────
            if self.selected_exposures:
                for idx in triggered_positions:
                    pos_num  = idx + 1
                    pos_loop = self.sam2_mgr.pos_loop_count.get(idx, 0) + 1

                    fl_dir = os.path.join(base, f"Position_{pos_num}", "FL")
                    os.makedirs(fl_dir, exist_ok=True)

                    self._sam2_status(
                        f"FL imaging – Pos {pos_num}  Loop {pos_loop}"
                    )
                    px, py, pz = self.positions[idx]
                    self.mmc.setTimeoutMs(30000)
                    self.mmc.setXYPosition(px, py)
                    self.mmc.waitForDevice(self.mmc.getXYStageDevice())
                    self.mmc.setPosition(pz)
                    self.mmc.waitForDevice(self.mmc.getFocusDevice())
                    time.sleep(0.3)

                    for filt, exp in self.selected_exposures:
                        raw_fl = self.snap_EPI_image(filt, exp)
                        # e.g.  Pos1_Loop3_filt1_100ms_6min.tiff
                        fl_fname = (
                            f"Pos{pos_num}_Loop{pos_loop}"
                            f"_filt{filt}_{exp}ms_{time_tag_str}.tiff"
                        )
                        tiff.imwrite(os.path.join(fl_dir, fl_fname), raw_fl)
                        time.sleep(0.2)

            # ── Step 6: chemostat protocol for triggered positions only ──────────
            if self.Chemostat_protocol_steps:
                self._sam2_status(
                    "Running chemostat for triggered positions …"
                )

                # Valve priming sequence (identical to original experiment)
                self.control_valve(15, state=False)
                time.sleep(10)
                self.control_valve(15, state=True)
                self.control_valve(7,  state=False)
                for v in [12, 13, 14, 15]:
                    self.control_valve(v, state=False)
                    time.sleep(5)
                    self.control_valve(v, state=True)
                self.control_valve(7, state=True)

                self.mmc.setProperty(self.DIAlamp, "State", 1)
                # FIX: stop any leftover thread from a previous loop iteration
                # before creating a new one, preventing camera resource conflicts
                if self.video_thread is not None and self.video_thread.isRunning():
                    self.video_thread.stop()
                    self.video_thread = None

                self.video_thread = VideoThread()
                self.video_thread.start()
                # Give the acquisition pipeline a moment to initialise before
                # the first start_recording() call
                QtCore.QThread.msleep(300)

                for step in self.Chemostat_protocol_steps:
                    i1    = step["input1"]
                    i2    = step["input2"]
                    rings = step["rings"]   # list[bool], one entry per position

                    # Purge inlet once per step (not once per position)
                    pw = DropletWorker("purge", inlets=[i1, i2], purge_duration=purge_dur)
                    pw.start(); pw.wait()

                    for rn, active in enumerate(rings):
                        # Only act if the ring is checked AND this pos was triggered
                        if active and (rn in triggered_positions):
                            px, py, pz = self.positions[rn]
                            self.mmc.setTimeoutMs(30000)
                            self.mmc.setXYPosition(px, py)
                            self.mmc.waitForDevice(self.mmc.getXYStageDevice())
                            self.mmc.setPosition(pz)
                            self.mmc.waitForDevice(self.mmc.getFocusDevice())
                            time.sleep(0.3)

                            gw = DropletWorker(
                                "generate", inlets=[i1], flow_duration=flow_dur
                            )
                            gw.start(); gw.wait()
                            # FIX: guard against a dead video thread before recording
                            if self.video_thread and self.video_thread.isRunning():
                                self.video_thread.start_recording()
                            else:
                                print(f"WARNING: VideoThread not running at loop "
                                      f"step {rn+1} – skipping recording for this chemostat")
                                continue

                            dw = DropletWorker(
                                "drive", i1,
                                drive_duration=drive_dur,
                                chemostat_number=rn + 1,
                            )
                            dw.start(); dw.wait()
                            # FIX: always stop recording in a finally block so a
                            # DropletWorker failure can't leave the writer open
                            if self.video_thread and self.video_thread.isRunning():
                                self.video_thread.stop_recording()
                            # Brief pause to let the writer flush before the next clip
                            QtCore.QThread.msleep(200)

                    # Close / re-open flush valves between steps
                    self.control_valve(15, state=False)
                    self.control_valve(7,  state=False)
                    time.sleep(5)
                    self.control_valve(15, state=True)
                    self.control_valve(7,  state=True)

                self.video_thread.stop()
                self.video_thread = None
                self.mmc.setProperty(self.DIAlamp, "State", 0)

            # ── Reset SAM2 context and advance loop counter per triggered pos ────
            for idx in triggered_positions:
                self.sam2_mgr.reset_loop_context(idx)
                self.sam2_mgr.pos_loop_count[idx] = (
                    self.sam2_mgr.pos_loop_count.get(idx, 0) + 1
                )
                new_loop = self.sam2_mgr.pos_loop_count[idx] + 1
                print(
                    f"  Pos {idx + 1}: SAM2 context reset → "
                    f"entering Loop {new_loop}"
                )

        # ── Experiment complete ──────────────────────────────────────────────────
        self.control_valve(0, state=True)
        print("\n=== SAM2 timelapse experiment complete ===")
        self._sam2_status("Experiment complete.")




    # ── timelapse experiment ──────────────────
    def TimeLapse_Experiment(self, num_loops, time_interval, positions_table,
                              selected_exposures, chemostat_protocol_table):
        init_states = [(0,False),(1,True),(2,False),(3,True),(4,True),(5,False),
                       (6,False),(7,True),(8,False),(9,False),(10,False),(11,False),
                       (12,True),(13,True),(14,True),(15,True)]
        for v, s in init_states:
            self.control_valve(v, state=s)

        purge_duration = float(self.purge_duration_Input.text())
        flow_duration  = float(self.flow_duration_Input.text())
        drive_duration = float(self.drive_duration_Input.text())

        for loop in range(num_loops):
            print(f"--- Loop {loop+1}/{num_loops} ---")
            loop_start = time.time()

            for ci in range(len(positions_table)):
                self.mmc.setXYPosition(positions_table[ci][0], positions_table[ci][1])
                self.mmc.setPosition(positions_table[ci][2])
                self.mmc.waitForSystem(); time.sleep(0.5)
                for filt, exp in selected_exposures:
                    img = self.snap_EPI_image(filt, exp)
                    fn  = f"Expt_{ci+1}_{filt}_{exp}_{loop+1}.tiff"
                    time.sleep(0.2)
                    img.save(os.path.join(".", fn))

            if self.Chemostat_protocol_steps:
                self.control_valve(15, state=False); time.sleep(30)
                self.control_valve(15, state=True)
                self.control_valve(7,  state=False)
                for v in [12, 13, 14, 15]:
                    self.control_valve(v, state=False); time.sleep(5)
                    self.control_valve(v, state=True)
                self.control_valve(7, state=True)
                self.mmc.setProperty(self.DIAlamp, 'State', 1)
                self.video_thread = VideoThread()
                self.video_thread.start()

                for step in self.Chemostat_protocol_steps:
                    i1 = step["input1"]; i2 = step["input2"]
                    pw = DropletWorker("purge", inlets=[i1, i2], purge_duration=purge_duration)
                    pw.start(); pw.wait()
                    for rn, active in enumerate(step["rings"]):
                        if active:
                            self.mmc.setXYPosition(positions_table[rn][0], positions_table[rn][1])
                            self.mmc.setPosition(positions_table[rn][2])
                            gw = DropletWorker("generate", inlets=[i1], flow_duration=flow_duration)
                            gw.start(); gw.wait()
                            self.video_thread.start_recording()
                            dw = DropletWorker("drive", i1, drive_duration=drive_duration, chemostat_number=rn+1)
                            dw.start(); dw.wait()
                            self.video_thread.stop_recording()
                    self.control_valve(15, state=False); self.control_valve(7, state=False)
                    time.sleep(5)
                    self.control_valve(15, state=True);  self.control_valve(7, state=True)

                self.video_thread.stop()
                self.mmc.setProperty(self.DIAlamp, 'State', 0)

            elapsed   = time.time() - loop_start
            remaining = time_interval * 60 - elapsed
            if remaining > 0:
                print(f"Waiting {remaining:.1f}s …")
                time.sleep(remaining)

        
        self.mmc.setTimeoutMs(5000)  # restore default
        self._sam2_status("Experiment complete.")
        self.control_valve(0, state=True)




    # ── 5. Dispatcher: replaces the original start-button connection ─────────────
    def _on_start_experiment(self):
        """
        Dispatch to the correct experiment mode based on which tab the user
        has set up:
          • FL Segmentation  – if the active tab is 'FL Segmentation'
          • SAM2 Tracking    – if SAM2 reference masks have been annotated
          • Original timelapse – fallback

        Wire up in __init__:
            self.start_experiment_button.clicked.connect(self._on_start_experiment)
        """
        self._stop_live_video()
        active_tab = self.tabs.tabText(self.tabs.currentIndex())
        if active_tab == "FL Segmentation":
            self.TimeLapse_Experiment_FL(
                interval_min=int(self.cycle_Interval_Input.text()),
                total_min=int(self.cycle_Input.text()),
            )
        elif self.sam2_mgr.ref_mask:
            self.TimeLapse_Experiment_SAM2(
                interval_min=int(self.cycle_Interval_Input.text()),
                total_min=int(self.cycle_Input.text()),
            )
        else:
            self.TimeLapse_Experiment(
                num_loops=int(self.cycle_Input.text()),
                time_interval=int(self.cycle_Interval_Input.text()),
                positions_table=self.positions,
                selected_exposures=self.selected_exposures,
                chemostat_protocol_table=self.Chemostat_protocol_steps,
            )
            



    def closeEvent(self, event):
        self.all_on_callback()
        if self.Numato_port and self.Numato_port.is_open:
            self.Numato_port.close()
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



"""EXPERIMENT LOGIC OVERVIEW
─────────────────────────
Pre-experiment (manual, before clicking Start):
①  capture_bf_for_all_positions()   – snap & save one BF per position
②  annotate_all_positions_sam2()    – interactive SAM2 point annotation

Experiment (TimeLapse_Experiment_SAM2):
• Every `interval_min` minutes, BF-image ALL positions.
• Each position keeps its own independent loop counter.
• SAM2 context for position P at time T in loop L =
        [initial_BF]  +  [all BF images taken in loop L before time T]
    → the initial BF is always frame 0; current-loop BFs accumulate on top.
• If area < 70 % of initial  →  position is "triggered":
        – FL imaging for that position (saved to Position_N/FL/)
        – Chemostat protocol for that position
        – Current-loop BF list reset (context back to initial only)
        – That position's loop counter incremented by 1
• Experiment ends when total wall-clock time is reached.

FOLDER / FILE NAMING
─────────────────────
<base>/
Position_1/
    BF/
    Pos1_initialBF.tiff
    Pos1_initialMask.tiff
    Pos1_Loop1_BF_3min.tiff        ← first tick, loop 1
    Pos1_Loop1_mask_3min.tiff
    Pos1_Loop1_BF_6min.tiff        ← triggered here
    Pos1_Loop1_mask_6min.tiff
    Pos1_Loop2_BF_3min.tiff        ← context reset, loop 2 begins
    Pos1_Loop2_mask_3min.tiff
    …
    FL/
    Pos1_Loop1_filt1_100ms_6min.tiff
    Pos1_Loop2_filt2_50ms_21min.tiff
    …
Position_2/
    BF/  …
    FL/  …
"""