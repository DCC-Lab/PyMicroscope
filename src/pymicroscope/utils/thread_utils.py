from threading import current_thread, main_thread

def is_main_thread() -> bool:
    return current_thread() == main_thread()
