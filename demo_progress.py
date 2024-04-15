from src.tqdme import tqdme

# # Polyfill the tqdm module
# import sys
# from src.tqdme import tqdme
# del sys.modules['tqdm']
# sys.modules['tqdm'] = tqdme

# # Import tqdm from the new module
# from tqdm import tqdm

from src.dummylib import run_parallel_processes
from typing import List

from dotenv import load_dotenv
load_dotenv() 

N_JOBS = 3

# Each outer entry is a list of 'tasks' to perform on a particular worker
# For demonstration purposes, each in the list of tasks is the length of time in seconds
# that each iteration of the task takes to run and update the progress bar (emulated by sleeping)
BASE_SECONDS_PER_TASK = 0.5  # The base time for each task; actual time increases proportional to the index of the task
NUMBER_OF_TASKS_PER_JOB = 10
TASK_TIMES: List[List[float]] = [
    [BASE_SECONDS_PER_TASK * task_index] * NUMBER_OF_TASKS_PER_JOB
    for task_index in range(1, NUMBER_OF_TASKS_PER_JOB + 1)
]

if __name__ == '__main__':
    run_parallel_processes(all_task_times=TASK_TIMES, n_jobs=N_JOBS)