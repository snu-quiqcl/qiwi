#!/usr/bin/env python3

"""
QIWI is a main manager for qiwi system.

Using a set-up file written by a user, it sets up apps.

Usage:
    python -m qiwi (-s <SETUP_PATH>)
"""

import sys
import os
import argparse
import json
import importlib
import importlib.util
import inspect
import dataclasses
import functools
from collections import defaultdict
from contextlib import contextmanager
from typing import (
    Dict, DefaultDict, Set, Any, Callable, Iterable, Mapping, Optional, Tuple, TypeVar, Type
)

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QDockWidget, QMessageBox, QWidget


T = TypeVar("T")


class Serializable:  # pylint: disable=too-few-public-methods
    """A type for dataclasses that can be converted to a JSON string.
    
    The message protocols in qiwi use JSON strings to encode data.
    If a dataclass inherits this class, the dictionary yielded by asdict() must
      be able to converted to a JSON string, i.e., JSONifiable.
    Every argument of qiwicalls must be JSONifiable by itself
      or an instance of Serializable.
    """


@dataclasses.dataclass
class AppInfo(Serializable):
    """Information required to create an app.
    
    Fields:
        module: Module name in which the app class resides.
        cls: App class name.
        path: System path for module importing.
        show: Whether to show the app frames on creation.
        pos: Position on the main window; refer to Qt.DockWidgetArea enum.
          Should be one of "left", "right", "top", or "bottom", case-sensitive.
          Otherwise, defaults to Qt.LeftDockWidgetArea.
        channel: Channels which the app subscribes to.
        args: Keyword argument dictionary of the app class constructor.
          It must exclude name and parent arguments. Even if they exist, they will be ignored.
          None for initializing the app with default values,
          where only name and parent arguments will be passed.
    """
    module: str
    cls: str
    path: str = "."
    show: bool = True
    pos: str = ""
    channel: Iterable[str] = ()
    args: Optional[Mapping[str, Any]] = None


def loads(cls: Type[T], kwargs: str) -> T:
    """Returns a new cls instance from a JSON string.
    
    Args:
        cls: A class object.
        kwargs: A JSON string of a dictionary that contains the keyword arguments of cls.
          Positional arguments should be given with the argument names, just like
          the other keyword arguments.
          There must not exist arguments which are not in cls constructor.
    """
    return cls(**json.loads(kwargs))


def dumps(obj: Serializable) -> str:
    """Returns a JSON string converted from the given Serializable object.
    
    Args:
        obj: Dataclass object to convert to a JSON string.
    """
    return json.dumps(dataclasses.asdict(obj))


@dataclasses.dataclass
class QiwicallInfo(Serializable):
    """Information of a qiwicall request.
    
    Fields:
        call: The name of the qiwicall feature, e.g., "createApp" for createApp().
          This is case-sensitive.
        args: The arguments of the qiwicall as a dictionary of keyword arguements.
          The names of the arguements are case-sensitive.
          When an argument is Serializable, it must be given as a converted JSON string,
          e.g., not {"arg": QiwicallInfo(call="call")},
          but {"arg": '{"call": "call", "args": {}}'}.
    """
    call: str
    args: Mapping[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class QiwicallResult(Serializable):
    """Result data of a qiwicall.
    
    Fields:
        done: Whether the qiwicall is done. Even when it failed, this is True as well.
        success: True when the qiwicall is done without any problems.
        value: Return value of the qiwicall, if any. It must be JSONifiable.
        error: Information about the problem that occurred during the qiwicall.
    """
    done: bool
    success: bool
    value: Any = None
    error: Optional[str] = None


class Qiwi(QObject):
    """Actual manager for qiwi system.

    Note that QApplication instance must be created before instantiating Qiwi object.

    A qiwicall is a request for the qiwi system such as creating an app.
    Messages emitted from "qiwicallRequested" signal are considered as qiwicall.
    For details, see _qiwicall().

    Brief procedure:
        1. Load setup environment.
        2. Create apps and show their frames.
    """

    def __init__(
        self,
        appInfos: Optional[Mapping[str, AppInfo]] = None,
        parent: Optional[QObject] = None):
        """
        Args:
            appInfos: See Qiwi.load(). None or an empty dictionary for loading no apps.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.appInfos = appInfos
        self.mainWindow = QMainWindow()
        self.centralWidget = QLabel("Qiwi")
        self.centralWidget.setAlignment(Qt.AlignCenter)
        self.centralWidget.setStyleSheet("background-color: gray;")
        self.mainWindow.setCentralWidget(self.centralWidget)
        self._dockWidgets = defaultdict(list)
        self._apps: Dict[str, BaseApp] = {}
        self._subscribers: DefaultDict[str, Set[str]] = defaultdict(set)
        appInfos = appInfos if appInfos else {}
        self.load(appInfos)
        self.mainWindow.show()

    def load(self, appInfos: Mapping[str, AppInfo]):
        """Initializes qiwi system and loads the apps.
        
        Args:
            appInfos: A dictionary whose keys are app names and the values are
              corresponding AppInfo objects. All the apps in the dictionary
              will be created, and if the show field is True, its frames will
              be shown.
        """
        for name, info in appInfos.items():
            self.createApp(name, info)

    def addFrame(self, name: str, frame: QWidget, info: AppInfo):
        """Adds a frame of the app and wraps it with a dock widget.

        This is not a qiwicall because QWidget is not Serializable.
        
        Args:
            name: A name of app.
            frame: A frame to show.
            info: An AppInfo object describing the app.
        """
        dockWidget = QDockWidget(name, self.mainWindow)
        dockWidget.setWidget(frame)
        area = {
            "left": Qt.LeftDockWidgetArea,
            "right": Qt.RightDockWidgetArea,
            "top": Qt.TopDockWidgetArea,
            "bottom": Qt.BottomDockWidgetArea
        }.get(info.pos, Qt.LeftDockWidgetArea)
        if info.show:
            self.mainWindow.addDockWidget(area, dockWidget)
        self._dockWidgets[name].append(dockWidget)

    def removeFrame(self, name: str, dockWidget: QDockWidget):
        """Removes the frame from the main window.
        
        This is not a qiwicall because QDockWidget is not Serializable.
        
        Args:
            name: A name of app.
            dockWidget: A dock widget to remove.
        """
        self.mainWindow.removeDockWidget(dockWidget)
        self._dockWidgets[name].remove(dockWidget)
        dockWidget.deleteLater()

    def appNames(self) -> Tuple[str]:
        """Returns the names of the apps including whose frames are hidden."""
        return tuple(self._apps.keys())

    def createApp(self, name: str, info: AppInfo):
        """Creates an app and shows their frames using set-up environment.
        
        Args:
            name: A name of app.
            info: An AppInfo object describing the app.
        """
        with _add_to_path(os.path.dirname(info.path)):
            module = importlib.import_module(info.module)
        cls = getattr(module, info.cls)
        if info.args is not None:
            app = cls(name, parent=self, **info.args)
        else:
            app = cls(name, parent=self)
        app.broadcastRequested.connect(self._broadcast, type=Qt.QueuedConnection)
        app.qiwicallRequested.connect(
            functools.partial(self._qiwicall, name),
            type=Qt.QueuedConnection,
        )
        for channelName in info.channel:
            self.subscribe(name, channelName)
        for frame in app.frames():
            self.addFrame(name, frame, info)
        self._apps[name] = app

    def destroyApp(self, name: str):
        """Destroys an app.
        
        Args:
            name: A name of the app to destroy.
        """
        dockWidgets = self._dockWidgets[name]
        for dockWidget in dockWidgets:
            self.removeFrame(name, dockWidget)
        del self._dockWidgets[name]
        for apps in self._subscribers.values():
            apps.discard(name)
        self._apps.pop(name).deleteLater()

    def updateFrames(self, name: str):
        """Updates the frames of an app.
        
        Args:
            name: A name of the app to update its frames.
        """
        app = self._apps[name]
        info = self.appInfos[name]
        orgFrames = {dockWidget.widget(): dockWidget for dockWidget in self._dockWidgets[name]}
        newFrames = app.frames()
        orgFramesSet = set(orgFrames)
        newFramesSet = set(newFrames)
        for frame in orgFramesSet - newFramesSet:
            self.removeFrame(name, orgFrames[frame])
        for frame in newFramesSet - orgFramesSet:
            self.addFrame(name, frame, info)

    def channelNames(self) -> Tuple[str]:
        """Returns the names of the channels."""
        return tuple(self._subscribers.keys())

    def subscriberNames(self, channel: str) -> Set[str]:
        """Returns the names of the subscriber apps of the channel.
        
        Args:
            channel: The name of the channel of interest.
              If it has no subscribers or does not exist, an empty set is returned.
        """
        return self._subscribers[channel].copy()

    def subscribe(self, app: str, channel: str):
        """Starts a subscription of the app to the channel.
        
        Args:
            app: The name of the app which wants to subscribe to the channel.
            channel: The target channel name.
        """
        self._subscribers[channel].add(app)

    def unsubscribe(self, app: str, channel: str) -> bool:
        """Cancels the subscription of the app to the channel.
        
        Args:
            app: The name of the app which wants to unsubscribe from the channel.
            channel: The target channel name.
        
        Returns:
            False when the app was not subscribing to the channel.
        """
        subscribers = self._subscribers[channel]
        try:
            subscribers.remove(app)
        except KeyError:
            return False
        return True

    @pyqtSlot(str, str)
    def _broadcast(self, channelName: str, msg: str):
        """Broadcasts the message to the subscriber apps of the channel.

        Args:
            channelName: Target channel name.
            msg: Message to be broadcast.
        """
        for name in self._subscribers[channelName]:
            self._apps[name].received.emit(channelName, msg)

    def _parseArgs(self, call: Callable, args: Mapping[str, Any]) -> Dict[str, Any]:
        """Converts all Serializable arguments to dataclass objects from strings.

        It checks the function signature of the call and converts the JSON string
        arguments to concrete dataclass instances if the parameter type is Serializable.

        The limitation of this implementation is that it can only support a single
        concrete type for each method parameter, i.e., it does not support union types,
        inheritance, etc.

        Args:
            call: Function object to inspect its signature.
            args: See QiwicallInfo.args.
        
        Returns:
            A dictionary of the same arguments as args, but with concrete Serializable
            dataclass instances instead of JSON strings.
        """
        signature = inspect.signature(call)
        parsedArgs = {}
        for name, arg in args.items():
            cls = signature.parameters[name].annotation
            parsedArgs[name] = loads(cls, arg) if issubclass(cls, Serializable) else arg
        return parsedArgs

    def _handleQiwicall(self, sender: str, msg: str) -> Any:
        """Handles the qiwicall.

        This can raise an exception if the arguments do not follow the valid API.
        The caller must obey the API and catch the possible exceptions.
        Calling non-public methods are prohibitted.

        Args:
            sender: The name of the request sender app.
            msg: A JSON string that can be converted to SwiftcallInfo,
              i.e., the same form as the returned string of dumps().
              See SwiftcallInfo for details.
        
        Raises:
            ValueError: When the requested call is not public, i.e., starts with
              an underscore (_).
            RuntimeError: When the user rejects the request.
        
        Returns:
            The returned value of the qiwicall, if any.
        """
        info = loads(QiwicallInfo, msg)
        if info.call.startswith("_"):
            raise ValueError("Only public method calls are allowed.")
        call = getattr(self, info.call)
        args = self._parseArgs(call, info.args)
        reply = QMessageBox.warning(
            None,
            "qiwicall",
            f"The app {sender} requests for a qiwicall {info.call} with {args}.",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply == QMessageBox.Ok:
            return call(**args)
        raise RuntimeError("The user rejected the request.")

    def _qiwicall(self, sender: str, msg: str):
        """Will be connected to the qiwicallRequested signal.

        Note that qiwicallRequested signal only has one str argument.
        In fact the partial method will be connected using functools.partial().

        Args:
            sender: See _handleQiwicall().
            msg: See _handleQiwicall().
        """
        try:
            value = self._handleQiwicall(sender, msg)
        except Exception as error:  # pylint: disable=broad-exception-caught
            result = QiwicallResult(done=True, success=False, error=repr(error))
        else:
            if isinstance(value, Serializable):
                value = dumps(value)
            result = QiwicallResult(done=True, success=True, value=value)
        self._apps[sender].qiwicallReturned.emit(msg, dumps(result))


class BaseApp(QObject):
    """Base App class that all apps should inherit.

    Signals: 
        broadcastRequested(channel, message): The app can emit this signal to request
          broadcasting to a channel with the target channel name and the message.
        received(channel, message): A broadcast message is received from a channel.
        qiwicallRequested(request): The app can emit this signal to request
          a qiwicall with a request message converted from a qiwi.QiwicallInfo
          object by qiwi.dumps().
        qiwicallReturned(request, result): The result of the requested qiwicall
          with the original requested message and the result message converted
          from a qiwi.QiwicallResult object by qiwi.dumps().
    
    Attributes:
        name: The string identifier name of this app.
        qiwicall: A qiwicall proxy for requesting qiwicalls conveniently.
    """

    broadcastRequested = pyqtSignal(str, str)
    received = pyqtSignal(str, str)
    qiwicallRequested = pyqtSignal(str)
    qiwicallReturned = pyqtSignal(str, str)

    def __init__(self, name: str, parent: Optional[QObject] = None):
        """
        Args:
            name: A string that indicates the name of App.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.name = name
        self.qiwicall = QiwicallProxy(self.qiwicallRequested)
        self.received.connect(self._receivedMessage)
        self.qiwicallReturned.connect(self._receivedQiwicallResult)

    def frames(self) -> Iterable[QWidget]:
        """Gets frames for which are managed by the App.

        Returns:
            An iterable object of Frame objects for showing.
        """
        return ()

    def broadcast(self, channelName: str, content: Any):
        """Broadcasts the content to the target channel.

        Args:
            channelName: Target channel name.
            content: Content to be broadcast. It should be able to be converted to JSON object.
        """
        try:
            msg = json.dumps(content)
        except TypeError as e:
            print(f"qiwi.app.broadcast(): {e!r}")
        else:
            self.broadcastRequested.emit(channelName, msg)

    def receivedSlot(self, channelName: str, content: Any):
        """Handles the received broadcast message.
        
        This is called when self.received signal is emitted.
        This will be overridden by child classes.

        Args:
            channelName: Channel name that transferred the message.
            content: Received content.
        """

    @pyqtSlot(str, str)
    def _receivedMessage(self, channelName: str, msg: str):
        """This is connected to self.received signal.
        
        Args:
            channelName: Channel name that transferred the message.
            msg: Received JSON string.
        """
        try:
            content = json.loads(msg)
        except json.JSONDecodeError as e:
            print(f"qiwi.app._receivedMessage(): {e!r}")
        else:
            self.receivedSlot(channelName, content)

    @pyqtSlot(str, str)
    def _receivedQiwicallResult(self, request: str, msg: str):
        """This is connected to self.qiwicallReturned signal.

        Args:
            request: The request message that has been sent via 
              self.qiwicallRequested signal.
            msg: The received qiwicall result message.
        """
        try:
            result = loads(QiwicallResult, msg)
        except json.JSONDecodeError as e:
            print(f"{self}._receivedResult: {e}")
        else:
            self.qiwicall.update_result(request, result)


class QiwicallProxy:  # pylint: disable=too-few-public-methods
    """A proxy for requesting qiwicalls conveniently.
    
    Every attribute access is proxied, and if you try to call a method of this
    object, it will emit a qiwicall requesting signal instead.
    If you get an attribute of this object, you will get a callable object which
    does the same thing as calling a method of this object.
    """

    def __init__(self, requested: QObject):
        """
        Args:
            requested: A pyqtSignal(str) which will be emitted when a proxied
              method call is invoked. See BaseApp.qiwicallRequested.
        """
        self.requested = requested
        self.results: Dict[str, QiwicallResult] = {}

    def __getattr__(self, call: str) -> Callable:
        """Returns a callable object which emits a qiwicall requesting signal.

        Args:
            call: The name of the qiwicall.
        """
        def proxy(**args: Any) -> QiwicallResult:
            """Emits a qiwicall request signal with the given arguments.

            It saves the returned result to self.results dictionary, so when
            self.returned signal is emitted, i.e., the qiwicall result is received,
            it will update the result object contents.

            Args:
                **args: The arguments for the qiwicall, all as keyword arguments.
                  If an argument is a qiwi.Serializable instance, it will be
                  converted to a JSON string by qiwi.dumps().

            Returns:
                A qiwicall result object to keep tracking the result.
            """
            for name, arg in args.items():
                if isinstance(arg, Serializable):
                    args[name] = dumps(arg)
            info = QiwicallInfo(call=call, args=args)
            result = QiwicallResult(done=False, success=False)
            msg = dumps(info)
            if msg in self.results:
                print(f"QiwicallProxy.<local>.proxy(): Duplicate message {msg} is ignored.")
            self.results[msg] = result
            self.requested.emit(msg)
            return result
        return proxy

    def update_result(self, request: str, result: QiwicallResult, discard: bool = True):
        """Updates the result for the request parsing the received message.

        Args:
            request: The request message that has been sent to Qiwi.
            result: The received result object.
            discard: If True, the result object is removed from self.results.
              In most cases, it will be updated only once and never be looked up again.
              Therefore, it is efficient to discard it after updating the result.
              If you want to find the result from self.results later again, give False.
        """
        _get_result = self.results.pop if discard else self.results.get
        _result = _get_result(request, None)
        if _result is None:
            print(f"QiwicallProxy.update_result(): Failed to find a result for {request}.")
            return
        _result.error = result.error
        _result.value = result.value
        _result.success = result.success
        _result.done = result.done


@contextmanager
def _add_to_path(path: str):
    """Adds a path temporarily.

    Using a 'with' statement, you can import a module without changing sys.path.

    Args:
        path: A desired path to be added. 
    """
    old_path = sys.path
    sys.path = old_path.copy()
    sys.path.insert(0, path)
    try:
        yield
    finally:
        sys.path = old_path


def _get_argparser() -> argparse.ArgumentParser:
    """Parses command line arguments.

    -s, --setup: A path of set-up file.

    Returns:
        A namespace containing arguments.
    """
    parser = argparse.ArgumentParser(
        description="SNU widget integration framework for PyQt"
    )
    parser.add_argument(
        "-s", "--setup", dest="setup_path", default="./setup.json",
        help="a path of set-up file containing the infomation about app"
    )
    return parser


def _read_setup_file(setup_path: str) -> Mapping[str, AppInfo]:
    """Reads set-up information from a JSON file.

    The JSON file content should have the following structure:

      {
        "app": {
          "app_name_0": {app_info_0},
          ...
        }
      }

    See AppInfo for app_info_* structure.
      
    Args:
        setup_path: A path of set-up file.

    Returns:
        A dictionary of set-up information about apps. See appInfos in Qiwi.load().
    """
    with open(setup_path, encoding="utf-8") as setup_file:
        setup_data: Dict[str, Dict[str, dict]] = json.load(setup_file)
    app_dict = setup_data.get("app", {})
    app_infos = {name: AppInfo(**info) for (name, info) in app_dict.items()}
    return app_infos


def main():
    """Main function that runs when qiwi module is executed rather than imported."""
    args = _get_argparser().parse_args()
    # read set-up information
    app_infos = _read_setup_file(args.setup_path)
    # start GUI
    qapp = QApplication(sys.argv)
    _qiwi = Qiwi(app_infos)
    qapp.exec_()


if __name__ == "__main__":
    main()