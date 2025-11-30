import os
import sys
import logging
import time

# Configure logger if this script is run standalone
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

log = logging.getLogger("auto_session_runner")

def recover():
    """
    Attempt to recover from a session expiration.
    Since we cannot interactively login, this involves:
    1. Logging the critical failure.
    2. Writing a status file for monitoring.
    3. Restarting the process to retry (in case of transient issues or updated env).
    """
    log.critical("⚠️ SESSION EXPIRED: Initiating recovery sequence...")
    
    # 1. Write status file for Admin Dashboard / Monitoring
    try:
        # Assuming /app/data is mounted and writable as per docker-compose
        status_path = "/app/data/session_status"
        # If we are not in docker, we might not have /app/data. Check env or fallback.
        if not os.path.exists("/app/data"):
            # Fallback to local directory
            status_path = "session_status"
            
        with open(status_path, "w") as f:
            f.write("EXPIRED")
        log.info(f"Status written to {status_path}")
    except Exception as e:
        log.error(f"Failed to write session status file: {e}")

    # 2. Wait to prevent rapid crash loops
    wait_seconds = 30
    log.info(f"Waiting {wait_seconds} seconds before restarting service...")
    time.sleep(wait_seconds)
    
    # 3. Restart the process
    log.info("♻️ Restarting process now...")
    try:
        # Re-execute the current script
        # This replaces the current process with a new one
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        log.critical(f"Failed to restart process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    recover()
