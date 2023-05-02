"""
Module for testing swift module.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import importlib
from collections.abc import Iterable
import json

from PyQt5.QtCore import QObject, pyqtSignal, pyqtBoundSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QLabel

import swift

APP_INFOS = {
    "app1": swift.AppInfo(
        module="module1",
        cls="cls1",
        path="path1",
        show=False,
        pos="left",
        channel=["ch1", "ch2"],
        args={"arg1": "value1"}
    ),
    "app2": swift.AppInfo(
        module="module2",
        cls="cls2"
    )
}

APP_DICTS = {
    "app1": {
        "module": "module1",
        "cls": "cls1",
        "path": "path1",
        "show": False,
        "pos": "left",
        "channel": ["ch1", "ch2"],
        "args": {"arg1": "value1"}
    },
    "app2": {
        "module": "module2",
        "cls": "cls2"
    }
}

APP_JSONS = {
    "app1": ('{"module": "module1", "cls": "cls1", "path": "path1", "show": false, '
             '"pos": "left", "channel": ["ch1", "ch2"], "args": {"arg1": "value1"}}'),
    "app2": ('{"module": "module2", "cls": "cls2", "path": ".", "show": true, '
             '"pos": "", "channel": [], "args": null}'),
    "app2_default": '{"module": "module2", "cls": "cls2"}'
}

'''
class SwiftTest(unittest.TestCase):
    """Unit test for Swift class."""

    def setUp(self):
        self.qapp = QApplication(sys.argv)
        importlib.import_module = MagicMock()
        for appInfo in APP_INFOS.values():
            app_ = MagicMock()
            app_.frames.return_value = (QWidget(),)
            cls = MagicMock(return_value=app_)
            setattr(importlib.import_module.return_value, appInfo.cls, cls)
        self.channels = set()
        for appInfo in APP_INFOS.values():
            self.channels.update(appInfo.channel)
        self.channels = sorted(self.channels)
        self.swift = swift.Swift(APP_INFOS)

    def test_init(self):
        self.assertEqual(self.swift.appInfos, APP_INFOS)
        self.assertIsInstance(self.swift.mainWindow, QMainWindow)
        self.assertIsInstance(self.swift.centralWidget, QLabel)
        for name in APP_INFOS:
            self.assertIn(name, self.swift._dockWidgets)
            self.assertIn(name, self.swift._apps)
        for channel in self.channels:
            self.assertIn(channel, self.swift._subscribers)

    def test_app_names(self):
        appNames = self.swift.appNames()
        for name in APP_INFOS:
            self.assertIn(name, appNames)

    def test_destroy_app(self):
        for name in APP_INFOS:
            self.swift.destroyApp(name)
            self.assertNotIn(name, self.swift._apps)

    def test_update_frames(self):
        self.swift._apps["app1"].frames.return_value = (QWidget(),)
        self.swift.updateFrames("app1")

    def test_channel_names(self):
        channelNames = self.swift.channelNames()
        for channelName in self.channels:
            self.assertIn(channelName, channelNames)

    def test_subscriber_names(self):
        for channel in self.channels:
            subscriberNames = self.swift.subscriberNames(channel)
            for name, info in APP_INFOS.items():
                if channel in info.channel:
                    self.assertIn(name, subscriberNames)

    def test_unsubcribe(self):
        self.assertEqual(self.swift.unsubscribe("app1", "ch1"), True)
        self.assertNotIn("app1", self.swift._subscribers["ch1"])
        self.assertEqual(self.swift.unsubscribe("app2", "ch1"), False)

    def test_swiftcall(self):
        QMessageBox.warning = MagicMock(return_value=QMessageBox.Ok)
        self.swift._swiftcall("app1", json.dumps({"call": "appNames", "args": {}}))
        self.swift._swiftcall("app1", json.dumps({
            "call": "createApp", "args": {"name": "app3", "info": {"module": "module2", "cls": "cls2"}}
        }))
        self.swift.callWithSerializable = MagicMock()
        self.swift.getSerializable = MagicMock(return_value=APP_INFOS["app1"])
        self.swift._swiftcall("app1", json.dumps({"call": "getSerializable", "args": {}}))
        self.swift._swiftcall("app1", json.dumps({"call": "_broadcast", "args": {}}))
        QMessageBox.warning.return_value = QMessageBox.Cancel
        self.swift._swiftcall("app1", json.dumps({"call": "appNames", "args": {}}))

    def test_broadcast(self):
        for channelName in self.channels:
            self.swift._broadcast(channelName, "test_msg")
        for name, app_ in self.swift._apps.items():
            self.assertEqual(len(APP_INFOS[name].channel), app_.received.emit.call_count)
'''

class BaseAppTest(unittest.TestCase):
    """Unit test for BaseApp class."""

    def setUp(self):
        self.app = swift.BaseApp("name")

    def test_init(self):
        self.assertEqual(self.app.name, "name")
        self.assertIsInstance(self.app.swiftcall, swift.SwiftcallProxy)
        self.assertEqual(type(self.app.broadcastRequested), pyqtBoundSignal)
        self.assertEqual(type(self.app.received), pyqtBoundSignal)
        self.assertEqual(type(self.app.swiftcallRequested), pyqtBoundSignal)
        self.assertEqual(type(self.app.swiftcallReturned), pyqtBoundSignal)

    def test_set_parent(self):
        swift.BaseApp("name", QObject())

    def test_frames(self):
        self.assertIsInstance(self.app.frames(), Iterable)

    def test_broadcast(self):
        self.app.broadcast("ch1", "msg")
        self.app.broadcast("ch1", lambda: None)


class SwiftFunctionTest(unittest.TestCase):
    """Unit test for functions in swift.py"""

    def test_parse(self):
        self.assertEqual(swift.loads(swift.AppInfo, APP_JSONS["app1"]), APP_INFOS["app1"])

    def test_parse_default(self):
        self.assertEqual(swift.loads(swift.AppInfo, APP_JSONS["app2_default"]), APP_INFOS["app2"])

    def test_strinfo(self):
        self.assertEqual(swift.dumps(APP_INFOS["app1"]), APP_JSONS["app1"])
        self.assertEqual(swift.dumps(APP_INFOS["app2"]), APP_JSONS["app2"])

    def test_add_to_path(self):
        test_dir = "/test_dir"
        old_path = sys.path.copy()
        with swift._add_to_path(test_dir):
            self.assertNotEqual(old_path, sys.path)
            self.assertIn(test_dir, sys.path)
        self.assertEqual(old_path, sys.path)

    @patch.object(sys, "argv", ["", "-s", "test_setup.json"])
    def test_get_argparser(self):
        parser = swift._get_argparser()
        args = parser.parse_args()
        self.assertEqual(args.setup_path, "test_setup.json")

    @patch.object(sys, "argv", [""])
    def test_get_argparser_default(self):
        args = swift._get_argparser().parse_args()
        self.assertEqual(args.setup_path, "./setup.json")

    @patch("builtins.open")
    @patch("json.load", return_value={"app": APP_DICTS})
    def test_read_setup_file(self, mock_open, mock_load):
        self.assertEqual(swift._read_setup_file(""), APP_INFOS)
        mock_open.assert_called_once()
        mock_load.assert_called_once()

    @patch("swift._get_argparser")
    @patch("swift._read_setup_file", return_value={})
    @patch("swift.Swift")
    @patch("PyQt5.QtWidgets.QApplication.exec_")
    def test_main(self, mock_get_argparser, mock_read_setup_file, mock_swift, mock_exec_):
        swift.main()
        mock_get_argparser.assert_called_once()
        mock_read_setup_file.assert_called_once()
        mock_swift.assert_called_once()
        mock_exec_.assert_called_once()


if __name__ == "__main__":
    unittest.main()
