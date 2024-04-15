import os
from typing import Union
import json

from uuid import uuid4
import requests
from requests.exceptions import RequestException
from multiprocessing import Value

import io

from tqdm import tqdm as base_tqdm

def getBoolEnv(name):
    return os.getenv(name, 'False') == 'True'

class tqdme(base_tqdm):

    __connected = Value('i', 1)

    __notifications = dict(
        connected = Value('i', 0),
        failure= Value('i', 0)
    )

    def __init__(self, *args, **kwargs):

        # Setup tqdme metadata
        identifier = str(uuid4())
        ppid = os.getppid()
        pid = os.getpid()
        kwargs['desc'] = f"PID: {pid}" if 'desc' not in kwargs else f"{kwargs['desc']} ({pid})"

        # Block display on the console
        if not getBoolEnv('TQDME_DISPLAY') and 'file' not in kwargs:
            kwargs['file'] = BlockTqdmDisplay()

        # Initialize the base tqdm class
        super().__init__(*args, **kwargs)

        # Initialize the metadata function
        self.metadata = dict(id=identifier, pid=pid, ppid=ppid)

        # Send initial state
        is_connected = self.__connected
        connection_notification = self.__notifications['connected']

        connection_notification.acquire()
        to_request_url = not connection_notification.value
        if to_request_url:
            connection_notification.value = 1
        connection_notification.release() # Release to modify with the request

        result = self.__forward(self.metadata, self.format_dict.copy(), dict(url=to_request_url))

        is_connected.acquire()
        is_currently_connected = is_connected.value
        is_connected.release()
        if is_currently_connected and result:
            url = result.get('url')
            if url:
                print(f"\nVisit {url} to view progress updates\n")

        else:
            failure_notification = self.__notifications['failure']
            failure_notification.acquire()
            if not failure_notification.value:
                print("\nFailed to connect to TQDME server\n")
                failure_notification.value = 1
            failure_notification.release()


    # Override the update method to run a callback function
    def update(self, n: int = 1) -> Union[bool, None]:
        displayed = super().update(n)

        is_connected = self.__connected
        is_connected.acquire()
        if is_connected.value:
            self.__forward(self.metadata, self.format_dict.copy())
        is_connected.release()

        return displayed
    

    def __forward(self, metadata:dict, format_dict: dict, metadata_in_response: dict = dict()):

        is_connected = self.__connected
        is_connected.acquire()
        if not is_connected.value:
            is_connected.release()
            return
        is_connected.release()

        URL = f"{os.getenv('TQDME_URL', 'http://tqdm.me')}/update" 
        json_data = json.dumps(obj=dict(**metadata, format=format_dict, requests=metadata_in_response))
        try:
            response = requests.post(url=URL, data=json_data, headers={"Content-Type": "application/json"})
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
            result = response.json()
            return result

        except RequestException as e:
            if getBoolEnv('TQDME_VERBOSE'):
                print(f"An error occurred: {e}")

            is_connected.acquire()
            is_connected.value = 0
            is_connected.release()


class BlockTqdmDisplay(io.StringIO):
    def write(self, s):
        pass

    def flush(self):
        pass