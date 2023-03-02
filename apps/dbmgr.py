"""
App module for adding and removing available databases.
"""

import os
import json

from PyQt5.QtCore import QPoint, pyqtSlot
from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton, QFileDialog,
                             QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem)

from swift.app import BaseApp

class DBWidget(QWidget):
    """Widget for showing a database.

    Attributes:
        name: A file name of the database.
        path: An absolute path of the database.
        nameLabel: A label for showing the file name.
        pathLabel: A label for showing the absolue path.
        removeButton: A button for removing (disconnecting) the database.
    """
    def __init__(self, name, path, parent=None):
        """
        Args:
            name: A file name of the database.
            path: An absolute path of the database.
            parent: A parent widget.
        """
        super().__init__(parent=parent)
        self.name = name
        self.path = path
        self._initWidget()

    def _initWidget(self):
        """Initializes widgets in the item."""
        self.nameLabel = QLabel(self.name, self)
        self.pathLabel = QLabel(self.path, self)
        self.removeButton = QPushButton("remove", self)
        # set layout
        layout = QHBoxLayout(self)
        layout.addWidget(self.nameLabel)
        layout.addWidget(self.pathLabel)
        layout.addWidget(self.removeButton)


class ManagerFrame(QWidget):
    """Frame for managing available databases.

    Attributes:
        dbListWidget: A list widget for showing available databases.
          Each database can be removed (actually disconnected) 
          when removeButton (of each item) clicked.
        addButton: A button for adding (actually connecting) a database.
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
        self.dbListWidget = QListWidget(self)
        self.addButton = QPushButton("add", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbListWidget)
        layout.addWidget(self.addButton)


class DBMgrApp(BaseApp):
    """App for adding and removing available databases.

    Manage a manager frame.
    Send an updated database information to database bus.

    Protocol:
        A broadcastRequested signal is emitted 
          when the available databases are changed (added or removed).
        It is a json object converted to string using json.dumps().
        On the receiving end, it can be interpreted using json.loads().

        The json object has one key; db. In db, there is a list of databases.  
        Each database has two keys; name and path.
          name: A file name of the database.
          path: An absolute path of the database.

    Attributes:
        dbList: A list for storing available databases.
          Each element is a tuple which represents a database.
          It has two elements; file name and absolute path.
        managerFrame: A frame that manages and shows available databases.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.dbList = []
        self.managerFrame = ManagerFrame()
        # connect signals to slots
        self.managerFrame.addButton.clicked.connect(self.addDB)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.managerFrame,)

    @pyqtSlot()
    def addDB(self):
        """Selects a database and adds to dbList.
        
        Show the database at dbListWidget in ManagerFrame.
        Emit a broadcastRequested signal containing an added database information.
        """
        dbPath, _ = QFileDialog.getOpenFileName(
            self.managerFrame,
            "Select a database file",
            "./"
        )
        if not dbPath:
            return
        name, path = reversed(os.path.split(dbPath))
        self.dbList.append((name, path))
        # create a database widget
        widget = DBWidget(name, path, self.managerFrame.dbListWidget)
        widget.removeButton.clicked.connect(self.removeDB)
        item = QListWidgetItem(self.managerFrame.dbListWidget)
        item.setSizeHint(widget.sizeHint())
        self.managerFrame.dbListWidget.addItem(item)
        self.managerFrame.dbListWidget.setItemWidget(item, widget)
        # emit a broadcastRequested signal
        msg = {"db": [{"name": db[0], "path": db[1]} for db in self.dbList]}
        self.broadcastRequested.emit("dbbus", json.dumps(msg))

    @pyqtSlot()
    def removeDB(self):
        """Selects a database and removes from dbList.
        
        Show the database at dbListWidget in ManagerFrame.
        Emit a broadcastRequested signal containing an added database information.
        """
        # find the selected database
        widget = self.sender().parent()
        gp = widget.mapToGlobal(QPoint())
        lp = self.managerFrame.dbListWidget.viewport().mapFromGlobal(gp)
        row = self.managerFrame.dbListWidget.row(self.managerFrame.dbListWidget.itemAt(lp))
        # remove the database widget
        del self.dbList[row]
        self.managerFrame.dbListWidget.takeItem(row)
        # emit a broadcastRequested signal
        msg = {"db": [{"name": db[0], "path": db[1]} for db in self.dbList]}
        self.broadcastRequested.emit("dbbus", json.dumps(msg))
