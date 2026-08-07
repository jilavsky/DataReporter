"""Single PySide6/PyQt6 import point for the whole ``datareporter.gui`` package.

Same pattern (and largely the same file) as ``pyirena.gui._qt`` and
``mailtovault.gui._qt``: every GUI module imports the Qt names it needs from
here rather than repeating a try/except binding block. Keeping the three
projects identical here means anything learned about Qt binding quirks in one
applies unchanged to the others.

PySide6 is the binding we ship and test. PyQt6 remains as a fallback only —
do **not** install both into the same environment: having PySide6 and PyQt6
side by side breaks Qt platform-plugin resolution (on macOS it surfaces as
"could not load the Qt platform plugin cocoa").

Two import styles are supported:

* flat names — ``from datareporter.gui._qt import QWidget, Qt, Signal``
* submodules — ``from datareporter.gui._qt import QtWidgets, QtCore, QtGui``

``Signal`` is normalised across bindings (``pyqtSignal`` under PyQt6).
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Signal

    QT_BINDING = "PySide6"
except ImportError as _pyside_error:  # pragma: no cover - only without PySide6
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets  # type: ignore[no-redef]
        from PyQt6.QtCore import pyqtSignal as Signal  # type: ignore[no-redef]

        QT_BINDING = "PyQt6"
    except ImportError:  # pragma: no cover
        # Do NOT report this as "not installed". ImportError also covers an
        # installed-but-unloadable binding — a missing system library
        # (libEGL.so.1, libGL.so.1 and libxkbcommon are the usual suspects on
        # bare Linux images), an architecture mismatch, or shiboken6 version
        # skew. Telling the user to reinstall Qt in those cases sends them
        # round in a circle, so surface the original error instead.
        raise ImportError(
            "datareporter.gui could not load a Qt binding.\n"
            f"The underlying error was: {_pyside_error}\n\n"
            "If PySide6 is not installed:  pip install 'datareporter[gui]'\n"
            "If it IS installed, the error above is the real cause — on a bare\n"
            "Linux image install the Qt runtime libraries, e.g.\n"
            "    apt-get install libegl1 libgl1 libxkbcommon0 libdbus-1-3"
        ) from _pyside_error

# --- QtWidgets --------------------------------------------------------------
QApplication = QtWidgets.QApplication
QCheckBox = QtWidgets.QCheckBox
QComboBox = QtWidgets.QComboBox
QDialog = QtWidgets.QDialog
QFileDialog = QtWidgets.QFileDialog
QFormLayout = QtWidgets.QFormLayout
QGroupBox = QtWidgets.QGroupBox
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QMainWindow = QtWidgets.QMainWindow
QMessageBox = QtWidgets.QMessageBox
QProgressBar = QtWidgets.QProgressBar
QPushButton = QtWidgets.QPushButton
QRadioButton = QtWidgets.QRadioButton
QSpinBox = QtWidgets.QSpinBox
QSplitter = QtWidgets.QSplitter
QStatusBar = QtWidgets.QStatusBar
QTreeWidget = QtWidgets.QTreeWidget
QTreeWidgetItem = QtWidgets.QTreeWidgetItem
QVBoxLayout = QtWidgets.QVBoxLayout
QWidget = QtWidgets.QWidget

# --- QtCore -----------------------------------------------------------------
QObject = QtCore.QObject
Qt = QtCore.Qt
QThread = QtCore.QThread
QTimer = QtCore.QTimer

# --- QtGui ------------------------------------------------------------------
QAction = QtGui.QAction
QFont = QtGui.QFont
QIcon = QtGui.QIcon

__all__ = [
    "QT_BINDING",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "Signal",
    # QtWidgets
    "QApplication",
    "QCheckBox",
    "QComboBox",
    "QDialog",
    "QFileDialog",
    "QFormLayout",
    "QGroupBox",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QMainWindow",
    "QMessageBox",
    "QProgressBar",
    "QPushButton",
    "QRadioButton",
    "QSpinBox",
    "QSplitter",
    "QStatusBar",
    "QTreeWidget",
    "QTreeWidgetItem",
    "QVBoxLayout",
    "QWidget",
    # QtCore
    "QObject",
    "Qt",
    "QThread",
    "QTimer",
    # QtGui
    "QAction",
    "QFont",
    "QIcon",
]
