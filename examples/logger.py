"""
App module for logging.
"""

import time
import logging
from typing import Any, Optional, Tuple, Callable

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QDialogButtonBox, QComboBox

from qiwis import BaseApp

class _Signaller(QObject):
    """Signal only for LoggingHandler.

    Signals:
        signal(log): A formatted log message is emitted. 
    """

    signal = pyqtSignal(str)


class LoggingHandler(logging.Handler):
    """Handler for logger.

    Sends a log message to connected function using emit.   
    """

    def __init__(self, slotfunc: Callable[[str], Any]):
        """Extended.

        Connects the slotfunc to the signal.

        Args:
            slotfunc: A slot function which is called when a log record is emitted.
        """
        super().__init__()
        self.signaller = _Signaller()
        self.signaller.signal.connect(slotfunc)

    def emit(self, record: logging.LogRecord):
        """Overridden.
        
        Emits input signal to the connected function.
        """
        s = self.format(record)
        self.signaller.signal.emit(s)


class LoggerFrame(QWidget):
    """Frame for logging.

    Attributes:
        logEdit: A textEdit which shows all logs.
        clearButton: A button for clearing all logs.
    """

    def __init__(self, parent: Optional[QObject] = None):
        """Extended."""
        super().__init__(parent=parent)
        # widgets
        self.logEdit = QTextEdit(self)
        self.logEdit.setReadOnly(True)
        self.clearButton = QPushButton("Clear")
        self.levelSelector = QComboBox(self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.logEdit)
        layout.addWidget(self.clearButton)
        layout.addWidget(self.levelSelector)


class ConfirmClearingFrame(QWidget):
    """
    A confirmation frame for log clearing.
    """
    confirmed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        """
        Extended.
        """
        super().__init__(parent=parent)
        # widgets
        self.label = QLabel("Are you sure to clear?")
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton("OK", QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton("Cancel", QDialogButtonBox.RejectRole)
        # connect signals
        self.buttonBox.accepted.connect(self.buttonOKClicked)
        self.buttonBox.rejected.connect(self.buttonCancelClicked)
        # layouts
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.label)
        layout.addWidget(self.buttonBox)

    def buttonOKClicked(self):
        """Clicks OK to clear log."""
        self.confirmed.emit()
        self.close()

    def buttonCancelClicked(self):
        """Clicks Cancel not to clear log."""
        self.close()


class LoggerApp(BaseApp):
    """App for logging.

    Manages a logger frame.

    Attributes:
        loggerFrame: A frame that shows the logs.
    """

    def __init__(self, name: str, parent: Optional[QObject] = None):
        """Extended.

        Args:
            name: Name of the App
        """
        super().__init__(name, parent=parent)
        self.loggerFrame = LoggerFrame()
        # connect signals to slots
        self.loggerFrame.clearButton.clicked.connect(self.checkToClear)
        self.confirmFrame = ConfirmClearingFrame()
        self.confirmFrame.confirmed.connect(self.clearLog)
        self.handler = LoggingHandler(self.addLog)
        # TODO(aijuh): Change the log format when it is determined.
        fs ="%(name)s %(message)s"
        formatter = logging.Formatter(fs)
        self.handler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(self.handler)
        self.initLevelSelector(self.loggerFrame.levelSelector)

    def initLevelSelector(self, box: QComboBox):
        """Initialize a combo box for selecting level."""
        box.addItem("DEBUG")
        box.addItem("INFO")
        box.addItem("WARNING")
        box.addItem("ERROR")
        box.addItem("CRITICAL")
        box.activated[str].connect(self.fixLevel)
    
    def fixLevel(self, text):
        match text:
            case "DEBUG":
                self.handler.setLevel(logging.DEBUG)
            case "INFO":
                self.handler.setLevel(logging.INFO)        
            case "WARNING":
                self.handler.setLevel(logging.WARNING)
            case "ERROR":
                self.handler.setLevel(logging.ERROR)
            case "CRITICAL":
                self.handler.setLevel(logging.CRITICAL)

    def frames(self) -> Tuple[LoggerFrame]:
        """Overridden."""
        return (self.loggerFrame,)

    @pyqtSlot(str)
    def addLog(self, content: str):
        """Adds a channel name and log message.

        Args:
            content: Received log message.
        """
        timeString = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        self.loggerFrame.logEdit.insertPlainText(f"{timeString}: {content}\n")

    def receivedSlot(self, channelName: str, content: Any):
        """Overridden.

        Possible channels are as follows.

        "log": Log channel.
            See self.addLog().
        """
        if channelName == "log":
            if isinstance(content, str):
                self.addLog(content)
            else:
                print("The message for the channel log should be a string.")
        else:
            print(f"The message was ignored because "
                  f"the treatment for the channel {channelName} is not implemented.")

    @pyqtSlot()
    def checkToClear(self):
        """Shows a confirmation frame for log clearing."""
        self.broadcast("log", "Clicked to clear logs")
        self.confirmFrame.show()

    @pyqtSlot()
    def clearLog(self):
        """Clears the log text edit."""
        self.loggerFrame.logEdit.clear()
