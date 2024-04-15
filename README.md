# tqdme
 

## Environment Variables
- `TQDME_URL` - URL to the TQDME server. Default: `http://tqdm.me`
- `TQDME_DISPLAY` - Show TQDM progress bars in the terminal. Default: `True`
- `TQDME_VERBOSE` - Print debug messages. Default: `False`

## Usage

### tqdm Replacement
Use `tqdme` as a drop-in replacement for `tqdm` in your Python scripts.
```python
import time
# from tqdm import tqdm
from tqdme import tqdme

num_iterations = 100 # Define the number of iterations

for i in tqdme(range(num_iterations)):
    time.sleep(0.1)  # Sleep for 0.1 seconds
```

### Relay Server (Flask + SocketIO)

> **Note:** The `tqdme` server assumes you have provided an `index.html` file in the `base` directory. 

```python
from tqdme.server import Server
from flask import send_from_directory
from pathlib import Path

script_directory = Path(__file__).parent.resolve()

server = Server(script_directory, 'localhost', 3768)

app = server.app

@server.app.route('/src/<path:path>')
def get_static_assets(path):
    return send_from_directory(server.base / 'src', path)

server.run()
```