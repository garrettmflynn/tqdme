import os
from typing import Union
import json

from uuid import uuid4
import requests
from requests.exceptions import RequestException
from json.decoder import JSONDecodeError

import io

from tqdm import tqdm as base_tqdm

def getBoolEnv(name):
    return os.getenv(name, 'False') == 'True'

TQDME_URL = os.getenv('TQDME_URL', 'http://tqdm.me')
TQDME_DISPLAY = getBoolEnv('TQDME_DISPLAY')
TQDME_VERBOSE = getBoolEnv('TQDME_VERBOSE')

URL = f"{TQDME_URL}/update"

class tqdme(base_tqdm):

    __connected = True

    def __init__(self, *args, **kwargs):

        # Setup tqdme metadata
        identifier = str(uuid4())
        ppid = os.getppid()
        pid = os.getpid()
        kwargs['desc'] = f"PID: {pid}" if 'desc' not in kwargs else f"{kwargs['desc']} ({pid})"

        # Block display on the console
        if not TQDME_DISPLAY and 'file' not in kwargs:
            kwargs['file'] = BlockTqdmDisplay()

        # Initialize the base tqdm class
        super().__init__(*args, **kwargs)

        # Initialize the metadata function
        self.metadata = dict(id=identifier, pid=pid, ppid=ppid)

        # Send initial state
        result = self.__forward(self.metadata, self.format_dict.copy())

        if self.__connected:
            url = result.get('url')
            if url:
                print(f"\nVisit {url} to view progress updates\n")

        else:
            print("\nFailed to connect to TQDME server\n")


    # Override the update method to run a callback function
    def update(self, n: int = 1) -> Union[bool, None]:
        displayed = super().update(n)

        if self.__connected:
            self.__forward(self.metadata, self.format_dict.copy())

        return displayed
    

    def __forward(self, metadata:dict, format_dict: dict):

        if not self.__connected:
            return
        
        json_data = json.dumps(obj=dict(**metadata, format=format_dict))
        try:
            response = requests.post(url=URL, data=json_data, headers={"Content-Type": "application/json"})
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code

            try:
                result = response.json()
                self.__connected = True
                return result
            except JSONDecodeError:
                if TQDME_VERBOSE:
                    print("Response content is not valid JSON")

                self.__connected = False

        except RequestException as e:
            if TQDME_VERBOSE:
                print(f"An error occurred: {e}")

            self.__connected = False


class BlockTqdmDisplay(io.StringIO):
    def write(self, s):
        pass

    def flush(self):
        pass