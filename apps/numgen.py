#!/usr/bin/env python3

"""
App module for generating and showing a random number.
"""

import sys
import os
import json

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QWidget,
                             QVBoxLayout, QComboBox, QPushButton, QLabel)

from swift.app import BaseApp
from apps.backend import generate, write

class GeneratorFrame(QWidget):
    """Frame for requesting generating a random number.
    
    Attributes:
        dbBox: A combobox for selecting a database 
          into which the generated number is saved.
        generateButton: A button for generating a new number.
    """
    def __init__(self, parent=None):
        """
        Args:
            parent: A parent widget.
        """
        super().__init__(parent=parent)
        self._initWidget()

    def _initWidget(self):
        """Initializes widgets in the frame."""
        self.dbBox = QComboBox(self)
        self.generateButton = QPushButton("generate number", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbBox)
        layout.addWidget(self.generateButton)


class ViewerFrame(QWidget):
    """Frame for showing the generated number.

    Attributes:
        statusLabel: A label for showing the current status.
          (database updated, random number generated, etc.)
        numberLabel: A label for showing the recently generated number.
    """
    def __init__(self, parent=None):
        """
        Args:
            parent: A parent widget.
        """
        super().__init__(parent=parent)
        self._initWidget()

    def _initWidget(self):
        """Initializes widgets in the frame."""
        self.statusLabel = QLabel("initialized", self)
        self.numberLabel = QLabel("not generated", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.numberLabel)


class NumGenApp(BaseApp):
    """App for generating and showing a random number.

    Manage a generator frame and a viewer frame.
    Communicate with the backend.

    Attributes:
        dbDict: A dictionary for storing available databases.
          Each element represents a database.
          A key is a file name and its value is an absolute path.
        dbName: A name of the selected database.
        generatorFrame: A frame that requests generating a random number.
        viewerFrame: A frame that shows the generated number.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.dbs = {"": ""}
        self.dbName = ""
        self.generatorFrame = GeneratorFrame()
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.received.connect(self.updateDB)
        self.generatorFrame.dbBox.currentIndexChanged.connect(self.setDB)
        self.generatorFrame.generateButton.clicked.connect(self.generateNumber)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.generatorFrame, self.viewerFrame)

    @pyqtSlot(str, str)
    def updateDB(self, busName: str, msg: str):
        """Updates the database list using the transferred message.

        This is a slot for received signal.

        Args:
            busName: A name of the bus that transfered the signal.
            msg: An input message to be transferred through the bus.
              The structure follows the message protocol of DBMgrApp.
        """
        if busName == "dbbus":
            try:
                msg = json.loads(msg)
            except json.JSONDecodeError as e:
                print(f"apps.numgen.updateDB(): {e!r}")
            else:
                self.dbs = {"": ""}
                self.generatorFrame.dbBox.clear()
                self.generatorFrame.dbBox.addItem("")
                for db in msg.get("db", ()):
                    if all(key in db for key in ("name", "path")):
                        name, path = db["name"], db["path"]
                        self.dbs[name] = path
                        self.generatorFrame.dbBox.addItem(name)
                    else:
                        print("The database has no such key; name or path.")
        else:
            print("The message is ignored.")

    @pyqtSlot()
    def setDB(self):
        """Sets the database to store the number."""
        self.dbName = self.generatorFrame.dbBox.currentText()
        self.viewerFrame.statusLabel.setText("database updated")

    @pyqtSlot()
    def generateNumber(self):
        """Generates and shows a random number when the button is clicked."""
        # generate a random number
        num = generate()
        self.viewerFrame.numberLabel.setText(f"generated number: {num}")
        # save the generated number
        dbPath = self.dbs[self.dbName]
        is_save_success = write(os.path.join(dbPath, self.dbName), "number", num)
        if is_save_success:
            self.viewerFrame.statusLabel.setText("number saved successfully")
        else:
            self.viewerFrame.statusLabel.setText("failed to save number")


def main():
    """Main function that runs when numgen module is executed rather than imported."""
    _app = QApplication(sys.argv)
    mainWindow = QMainWindow()
    # create an app
    app = NumGenApp("numgen")
    # get frames from the app and add them as dock widgets
    for frame in app.frames():
        dockWidget = QDockWidget("random number generator", mainWindow)
        dockWidget.setWidget(frame)
        mainWindow.addDockWidget(Qt.LeftDockWidgetArea, dockWidget)
    mainWindow.show()
    _app.exec_()


if __name__ == "__main__":
    main()
