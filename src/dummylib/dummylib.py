"""Demo of parallel tqdm visualization using tqdm.me polyfill"""

import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List
from src.tqdme import tqdme

def _run_sleep_tasks_in_subprocess(
    task_times: List[float],
    iteration_index: int
):
    """
    Run a 'task' that takes a certain amount of time to run on each worker.

    In this case that task is simply time.sleep.

    Parameters
    ----------
    sleep_time : float
        The amount of time this task emulates having taken to complete.
    iteration_index : int
        The index of this task in the list of all tasks from the buffer map.
        Each index would map to a different tqdm position.
    """

    sub_progress_bar = tqdme(
        iterable=task_times,
        position=iteration_index + 1,
        desc=f"Progress on iteration {iteration_index}",
        leave=False,
    )

    for sleep_time in sub_progress_bar:
        time.sleep(sleep_time)


def run_parallel_processes(*, all_task_times: List[List[float]], n_jobs: int = 2):

    futures = list()
    with ProcessPoolExecutor(max_workers=n_jobs) as executor:

        # # Assign the parallel jobs
        for iteration_index, task_times_per_job in enumerate(all_task_times):
            futures.append(
                executor.submit(
                    _run_sleep_tasks_in_subprocess,
                    task_times=task_times_per_job,
                    iteration_index=iteration_index
                )
            )

        total_tasks_iterable = as_completed(futures)
        total_tasks_progress_bar = tqdme(
            iterable=total_tasks_iterable, total=len(all_task_times), desc=f"Total tasks completed"
        )

        # Trigger the deployment of the parallel jobs
        for _ in total_tasks_progress_bar:
            pass
