[![Pylint](https://github.com/snu-quiqcl/swift/actions/workflows/pylint.yml/badge.svg)](https://github.com/snu-quiqcl/swift/actions/workflows/pylint.yml)

# swift
**S**NU **w**idget **i**ntegration **f**ramework for PyQ**t**

A framework for integration of PyQt widgets where they can communicate with each other.
This project is mainly developed for trapped ion experiment controller GUI in SNU QuIQCL.

`swift` provides a dashboard-like main window, in which variety of `Frame`s reside.
A `Frame` is in fact a special `QWidget` which obeys the interface of `swift`, and it will be wrapped by a `QDockWidget`.

## Features
- Independent development of each `Frame`, which is a sub-window application resides in the framework
- Communication channel between `Frame`s
- Thread-safety

## Structure chart
### Overall structure
<img width="80%" alt="image" src="https://user-images.githubusercontent.com/76851886/219574551-2f798863-ea48-4857-8db6-15840a0505e5.png">

```python
### Please be careful because Frame and Logic are mixed.

class Swift:
    """
    1. Read json setup files
        - Frame information file       (e.g. whether to show frame A at the beginning, whether frame B is a subscriber of GB)
        - Global bus information file  (e.g. name)
    
    2. Create instances of GlobalBus (GB) -> Able to be many GBs
        - Create a signal for emitting to each frame
        - Set global_signal_receiver() of subscribers as a slot

    3. Create frames
        - Connect bc signal of frames to corresponding GB
        
    4. Show frames
    """
    pass


class GlobalBus:
    def __init__():
         queue = []  # Queue for storing signals
         # Start thread for popping from queue and emitting signal to frames
         
        _signal = pyqtSignal(...)

        for frame in subscribers:
            _signal.connect(frame.global_signal_receiver) 

    # Method when called when a frame emits bc signal
    def receive(msg):
        queue.push(msg)
        
    # Method polling until queue is empty
    def poll():
        while True:
            if queue is not empty:
                msg = queue.pop()
                _signal.emit(msg)
    

# This class means both Frame and Logic (not real)
class Frame:
    def __init__():
        bc = pyqtSignal(...)  # create broadcasting signal

    # If the frame wants to receive global signals, override desired operation on the below function
    # This function is set as a slot in GB
    def global_signal_receiver(...):
        pass
```

### Frame structure
<img width="50%" alt="image" src="https://user-images.githubusercontent.com/76851886/219575722-408dc03a-c84e-417f-a541-e48dfda100c0.png">

A `Frame` simply means a window of PyQt that we see.

In fact, an engine which makes a `Frame` works is a `Logic`.
A `Logic` can 
- show/hide `Frame`s, which the `Logic` manages
- set a slot for each signal of `Frame`
- receive a signal which the `Frame` emits
- emit a signal to `Frame` or a global signal to `swift`
- communicate `backend` APIs

A `swift` recognizes only `Logic`, not `Frame` or `backend`. Thus, every order for `Frame` is implemented in `Logic`.

A `backend` is a set of APIs for handling UI-independent operations, such as controlling hardwards, polling something, and connecting DB.

```python
### Please be careful because Frame and Logic are mixed.

class Logic:
    """
    1. Create frames (generally only one frame)
         
    2. Connect signal of frame elements to API of Logic
        
    3. Show frames
    """
    
    # Example method that receive signal of frame elements
    def receive(...):
        # If necessary, start thread
        # Communicate with backend
        pass


class Frame(QWidget):
    pass
```

# Toy example applications
Several toy example applications are provided to demonstrate the basic features of `swift`.

## 1. Random number generator
### GUI - generator frame
- A combobox for selecting a database into which the generated number is saved
- A button for generating new number
### GUI - viewer frame
- A label for showing the current status (database updated, random number generated, etc.)
- A read-only spinbox showing the recently generated number
### Backend
- `generate() -> int`: Generate a random number and return it
- `save(num: int) -> bool`: Save the given number into the database

## 2. Logger
### GUI
- A read-only text field that prints out the log messages
### Backend
Not required.

## 3. Poller
### GUI
- A spinbox for adjusting the polling period
- A label for showing the polled count (how many numbers have been polled): this will confidently show when the polling occurs
- A read-only spinbox showing the recently polled number
### Backend
- `poll() -> int`: Return a predictable number e.g. `time.time() % 100`
- `save(num: int) -> bool`: Save the given number into the database

## 4. Database manager
### GUI
- A list whose each row shows the database name, information (host address, etc.), and a button to remove the row from the list
- Line-edit(s) and a button to add a row (new database)
### Backend
Not required.
