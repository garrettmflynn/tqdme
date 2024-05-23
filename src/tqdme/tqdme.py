import os
from typing import Union
import json
from uuid import uuid4
import urllib3
from multiprocessing import Value
import io

from tqdm import tqdm as base_tqdm
from .utils import getBoolEnv

ACTIVE_BARS = dict()

DEFAULT_CONFIG = dict(
    user_id = lambda: os.getenv('TQDME_USER_ID', None),
    verbose = lambda: getBoolEnv('TQDME_VERBOSE'),
    display = lambda: getBoolEnv('TQDME_DISPLAY'),
    url = lambda: os.getenv('TQDME_URL', 'http://tqdm.me'),
    id = lambda: str(uuid4()),
    group = lambda: os.getpid(),
    parent = lambda: os.getppid()
)

METADATA_TO_SEND = [ 'id', 'group', 'parent' ]

class tqdme(base_tqdm):

    __connected = Value('i', 1)

    __notifications = dict(
        connected = Value('i', 0),
        failure= Value('i', 0)
    )

    def __init__(
            self, 
            *args, 
            tqdme_options: dict = dict(),
            **kwargs
        ):

        config = tqdme_options.copy()
        # Resolve the configuration options for TQDME
        for key, func in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = func()

        self.__tqdme = config

        self.__done = False

        metadata = self.__sendrequest('ping', dict(url=True)) # Send a ping request to the server

        ACTIVE_BARS[self.__tqdme['id']] = self
        
        # If the server is connected, display the URL
        is_connected = self.__connected
        is_connected.acquire()
        is_currently_connected = is_connected.value
        is_connected.release()
        if is_currently_connected and metadata:
            url = metadata.get('url')
            if url:
                print(f"\nVisit {url} to view progress updates\n")

        else:
            failure_notification = self.__notifications['failure']
            failure_notification.acquire()
            if not failure_notification.value:
                print("\nFailed to connect to TQDME server\n")
                failure_notification.value = 1
            failure_notification.release()

        # Block display on the console
        if not self.__tqdme["display"] and 'file' not in kwargs:
            kwargs['file'] = BlockTqdmDisplay()

        # Initialize the base tqdm class
        super().__init__(*args, **kwargs)

        # Send initialization
        self.__sendupdate()

    # Override the update method to run a callback function
    def update(self, n: int = 1) -> Union[bool, None]:
        displayed = super().update(n)

        self.__sendupdate()
        return displayed
    
    # Add cleanup method
    def __del__(self):
        self.cleanup()

    def cleanup(self):
        if not self.__done:
            self.__sendrequest('ping', dict(done=True))
            ACTIVE_BARS.pop(self.__tqdme['id'], None)
            self.__done = True

    # Always send a consistent update
    def __sendupdate(self):
        update = dict(format=self.format_dict.copy())

        if update['format']['n'] == update['format']['total']:
            update['done'] = True

        return self.__sendrequest('update', update)

    # Check if the server has been rejected
    def __isconnected(self):
        is_connected = self.__connected
        is_connected.acquire()
        to_request_url = is_connected.value == 1
        is_connected.release()
        return to_request_url
    
    # Send a request to the server
    def __sendrequest(self, pathname: str, data: dict = dict()):

        if not self.__isconnected():
            return

        url = f"{self.__tqdme['url']}/{pathname}" 

        http = urllib3.PoolManager()

        # Provide arbitrary user_id on all requests (if exists)
        if self.__tqdme["user_id"] is not None:
            data['user_id'] = self.__tqdme["user_id"]


        try:
            to_send = { key: self.__tqdme[key] for key in METADATA_TO_SEND }
            to_send.update(data)

            response = http.request('POST', url, body=json.dumps(to_send), headers={'Content-Type': 'application/json'})
            if response.status == 200:
                return json.loads(response.data)
            else:
                raise Exception(f"Failed to send POST request. Status code: {response.status}")

        except Exception as e:

            if self.__tqdme["verbose"]:
                print(f"An error occurred: {e}")

            is_connected = self.__connected
            is_connected.acquire()
            is_connected.value = 0
            is_connected.release()

class BlockTqdmDisplay(io.StringIO):
    def write(self, s):
        pass

    def flush(self):
        pass


# Ensure proper exit
import atexit
import signal

def exit_handler():
    for bar in list(ACTIVE_BARS.values()):
        bar.cleanup()

atexit.register(exit_handler)

def signal_handler(signum, frame):
    exit_handler()  # Call exit_handler before exiting
    raise SystemExit

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
