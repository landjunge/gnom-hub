import subprocess
import tempfile
import os

def run_sandboxed(cmd, cwd, timeout=15):
    """
    Runs a shell command (or list of args) inside a macOS sandbox-exec.
    Allows read-access to the entire disk (since python needs libraries),
    but restricts write-access ONLY to the current working directory and temp folders.
    """
    abs_cwd = os.path.abspath(cwd)
    
    profile = f"""(version 1)
(allow default)
(deny file-write*
    (require-all
        (require-not (subpath "{abs_cwd}"))
        (require-not (subpath "/tmp"))
        (require-not (subpath "/private/tmp"))
        (require-not (subpath "/private/var/folders"))
    )
)
"""
    fd, profile_path = tempfile.mkstemp(suffix=".sb", prefix="gnom_sb_")
    try:
        os.write(fd, profile.encode('utf-8'))
        os.close(fd)
        
        if isinstance(cmd, str):
            sandboxed_cmd = ["sandbox-exec", "-f", profile_path, "bash", "-c", cmd]
        else:
            sandboxed_cmd = ["sandbox-exec", "-f", profile_path] + cmd
            
        r = subprocess.run(sandboxed_cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r
    finally:
        try:
            os.remove(profile_path)
        except:
            pass
