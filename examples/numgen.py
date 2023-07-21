"""
App module for generating and showing a random number.
"""

import os
import json
import logging
from typing import Any, Optional, Tuple, Union

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QWidget, QComboBox, QPushButton, QLabel, QVBoxLayout

from qiwis import BaseApp
from examples.backend import generate, write

logger = logging.getLogger(__name__)


class GeneratorFrame(QWidget):
    """Frame for requesting generating a random number.
    
    Attributes:
        dbBox: A combobox for selecting a database 
          into which the generated number is saved.
        generateButton: A button for generating a new number.
    """
    def __init__(self, parent: Optional[QObject] = None):
        """Extended."""
        super().__init__(parent=parent)
        # widgets
        self.dbBox = QComboBox(self)
        self.generateButton = QPushButton("generate number", self)
        # layout
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
    def __init__(self, parent: Optional[QObject] = None):
        """Extended."""
        super().__init__(parent=parent)
        # widgets
        self.statusLabel = QLabel("initialized", self)
        self.numberLabel = QLabel("not generated", self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.numberLabel)


class NumGenApp(BaseApp):
    """App for generating and showing a random number.

    Manage a generator frame and a viewer frame.
    Communicate with the backend.

    Attributes:
        table: A name of table to store the generated number.
        dbs: A dictionary for storing available databases.
          Each element represents a database.
          A key is a file name and its value is an absolute path.
        dbName: A name of the selected database.
        generatorFrame: A frame that requests generating a random number.
        viewerFrame: A frame that shows the generated number.
    """
    def __init__(self, name: str, table: str = "number", parent: Optional[QObject] = None):
        """Extended.

        Args:
            table: A name of table to store the generated number.
        """
        super().__init__(name, parent=parent)
        self.table = table
        self.dbs = {"": ""}
        self.dbName = ""
        self.isGenerated = False
        self.generatorFrame = GeneratorFrame()
        self.generatorFrame.dbBox.addItem("")
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.generatorFrame.dbBox.currentIndexChanged.connect(self.setDB)
        self.generatorFrame.generateButton.clicked.connect(self.generateNumber)

    def frames(self) -> Union[Tuple[GeneratorFrame, ViewerFrame], Tuple[GeneratorFrame]]:
        """Overridden.
        
        Once a number is generated, returns both frames.
        Otherwise, returns only the generator frame.
        """
        if self.isGenerated:
            return (self.generatorFrame, self.viewerFrame)
        return (self.generatorFrame,)

    def updateDB(self, content: dict):
        """Updates the database list using the transferred message.

        It assumes that:
            The new database is always added at the end.
            Changing the order of the databases is not allowed.

        Args:
            content: Received content.
              The structure follows the message protocol of DBMgrApp.
        """
        originalDBs = set(self.dbs)
        newDBs = set([""])
        for db in content.get("db", ()):
            if any(key not in db for key in ("name", "path")):
                logger.error("The message was ignored because "
                             "the database %s has no such key; name or path.", json.dumps(db))
                continue
            name, path = db["name"], db["path"]
            newDBs.add(name)
            if name not in self.dbs:
                self.dbs[name] = path
                self.generatorFrame.dbBox.addItem(name)
        removingDBs = originalDBs - newDBs
        if self.generatorFrame.dbBox.currentText() in removingDBs:
            self.generatorFrame.dbBox.setCurrentText("")
        for name in removingDBs:
            self.dbs.pop(name)
            self.generatorFrame.dbBox.removeItem(self.generatorFrame.dbBox.findText(name))

    def receivedSlot(self, channelName: str, content: Any):
        """Overridden.

        Possible channels are as follows.

        "db": Database channel.
            See self.updateDB().
        """
        if channelName == "db":
            if isinstance(content, dict):
                self.updateDB(content)
            else:
                logger.error("The message for the channel db should be a dictionary.")
        else:
            logger.error("The message was ignored because "
                         "the treatment for the channel %s is not implemented.", channelName)

    @pyqtSlot()
    def setDB(self):
        """Sets the database to store the number."""
        self.dbName = self.generatorFrame.dbBox.currentText()
        self.viewerFrame.statusLabel.setText("database updated")
        if self.dbName:
            logger.info("Database to store is set as %s", self.dbName)
        else:
            logger.info("Database to store is not selected.")

    @pyqtSlot()
    def generateNumber(self):
        """Generates and shows a random number when the button is clicked."""
        # generate a random number
        num = generate()
        if not self.isGenerated:
            self.isGenerated = True
            self.qiwiscall.updateFrames(name=self.name)
        self.viewerFrame.numberLabel.setText(f"generated number: {num}")
        logger.info("Generated number: %d.", num)
        # save the generated number
        dbPath = self.dbs[self.dbName]
        is_save_success = write(os.path.join(dbPath, self.dbName), self.table, num)
        if is_save_success:
            self.viewerFrame.statusLabel.setText("number saved successfully")
            logger.info("Generated number saved.")
        else:
            self.viewerFrame.statusLabel.setText("failed to save number")
            logger.error("Failed to save generated number")
