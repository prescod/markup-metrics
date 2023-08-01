import contextlib
import time
from typing import Generator, List, NamedTuple


class ProfileLog(NamedTuple):
    name: str
    time: float

class ProfileLogger:
    def __init__(self) -> None:
        self.times: List[ProfileLog] = []

    @contextlib.contextmanager
    def log_time(self, context:str) -> Generator[None, None, None]:
        start = time.perf_counter()
        yield
        end = time.perf_counter()
        self.times.append(ProfileLog(context, end - start))
