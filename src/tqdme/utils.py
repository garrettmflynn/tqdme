import os

def getBoolEnv(name):
    return os.getenv(name, 'False') == 'True'
