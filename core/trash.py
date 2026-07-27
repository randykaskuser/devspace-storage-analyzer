import os
from send2trash import send2trash

def safe_delete(path: str) -> bool:
    """
    Moves the given file or directory to the OS Recycle Bin/Trash.
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(path):
        return False
    
    try:
        send2trash(path)
        return True
    except Exception as e:
        print(f"Failed to trash {path}: {e}")
        return False

def empty_directory_contents(path: str) -> tuple[int, int]:
    """
    Moves all contents of a directory to the Recycle Bin, but keeps the root directory.
    Returns (success_count, fail_count).
    """
    if not os.path.exists(path) or not os.path.isdir(path):
        return 0, 0
        
    success_count = 0
    fail_count = 0
    
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        try:
            send2trash(full_path)
            success_count += 1
        except Exception:
            fail_count += 1
            
    return success_count, fail_count

def hard_delete_directory_contents(path: str) -> tuple[int, int]:
    """
    Permanently deletes all contents of a directory, bypassing the Recycle Bin.
    Extremely fast for Windows caches (Temp, Prefetch, etc).
    Returns (success_count, fail_count).
    """
    import shutil
    if not os.path.exists(path) or not os.path.isdir(path):
        return 0, 0
        
    success_count = 0
    fail_count = 0
    
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        try:
            if os.path.isfile(full_path) or os.path.islink(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
            success_count += 1
        except Exception:
            fail_count += 1
            
    return success_count, fail_count
