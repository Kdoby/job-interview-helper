import threading
import time


def log(handler: str, message: str) -> None:
    now = time.strftime("%H:%M:%S")
    thread = threading.current_thread().name
    print(f"{now} [{handler}] {message} (스레드: {thread})")
