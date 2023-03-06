"""
App module for polling a number and saving it into the selected database.
"""

import json

from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QSpinBox, QLabel

from swift.app import BaseApp
from apps.backend import poller

class ViewerFrame(QWidget):
    """Frame of for polling a number and saving it into the selected database.
    
    Attributes:
        dbBox: A combobox for selecting a database into which the polled number is saved.
        periodBox: A spinbox for adjusting the polling period.
        countLabel: A label for showing the polled count. (how many numbers have been polled)
          This will confidently show when the polling occurs
        numberLabel: A label for showing the recently polled number
    """
    def __init__(self, parent=None):
        """
        Args:
            parent: A parent widget.
        """
        super().__init__(parent=parent)
        # widgets
        self.dbBox = QComboBox(self)
        self.periodBox = QSpinBox(self)
        self.periodBox.setMinimum(1)
        self.periodBox.setMaximum(10)
        self.countLabel = QLabel("not initiated", self)
        self.numberLabel = QLabel("not initiated", self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbBox)
        layout.addWidget(self.periodBox)
        layout.addWidget(self.countLabel)
        layout.addWidget(self.numberLabel)


class PollerApp(BaseApp):
    def __init__(self, name: str, table: str = "B"):
        """
        Args:
            table: A name of table to store the polled number.
        """
        super().__init__(name)
        self.table = table
        self.dbs = {"": ""}
        self.dbName = ""
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.received.connect(self.updateDB)
        # start timer
        self.timer = QTimer(self)
        self.timer.start(1000 * self.viewerFrame.periodBox.value())
        self.timer.timeout.connect(self.poll)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.viewerFrame,)

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
                orgDbName = self.dbName
                self.dbs = {"": ""}
                self.viewerFrame.dbBox.clear()
                self.viewerFrame.dbBox.addItem("")
                for db in msg.get("db", ()):
                    if all(key in db for key in ("name", "path")):
                        name, path = db["name"], db["path"]
                        self.dbs[name] = path
                        self.viewerFrame.dbBox.addItem(name)
                    else:
                        print(f"The message was ignored because "
                              f"the database {db} has no such key; name or path.")
                if orgDbName in self.dbs:
                    self.viewerFrame.dbBox.setCurrentText(orgDbName)
        else:
            print(f"The message was ignored because "
                  f"the treatment for the bus {busName} is not implemented.")
            
    @pyqtSlot()
    def poll(self):
        num = poller()
        print(num)
