import threading
import subprocess
import logging
from pathlib import Path
from abc import ABC, abstractmethod

# --- GoF State Machine Design Pattern ---
class RestartContext:
    """The Context class that delegates actions to the current State."""
    def __init__(self):
        self.lock = threading.Lock()
        self.state = IdleState()
        self.debounce_timer = None

    def set_state(self, state: 'State'):
        self.state = state

    def queue_restart(self):
        # Delegate to whatever state we are currently in
        with self.lock:
            self.state.handle_webhook(self)

class State(ABC):
    """Abstract State interface."""
    @abstractmethod
    def handle_webhook(self, context: RestartContext):
        pass

class IdleState(State):
    """When idle, a webhook transitions us to Debouncing."""
    def handle_webhook(self, context: RestartContext):
        logging.info("⏳ [IDLE] Webhook received. Transitioning to DEBOUNCING...")
        context.set_state(DebouncingState(context))

class DebouncingState(State):
    """When debouncing, a webhook resets the timer. When the timer pops, we run."""
    def __init__(self, context: RestartContext):
        self._start_timer(context)

    def _start_timer(self, context: RestartContext):
        if context.debounce_timer:
            context.debounce_timer.cancel()
        context.debounce_timer = threading.Timer(3.0, self._timer_expired, args=[context])
        context.debounce_timer.start()

    def _timer_expired(self, context: RestartContext):
        with context.lock:
            # Only transition to running if we are still in the Debouncing state!
            if isinstance(context.state, DebouncingState):
                logging.info("⏳ [DEBOUNCING] Timer expired! Transitioning to RUNNING...")
                context.set_state(RunningState(context))

    def handle_webhook(self, context: RestartContext):
        logging.info("⏳ [DEBOUNCING] Spam detected! Resetting debounce timer...")
        self._start_timer(context)

class RunningState(State):
    """When running, a webhook queues exactly one rerun for when we finish."""
    def __init__(self, context: RestartContext):
        self.rerun_pending = False
        
        # Start the bash script asynchronously so we don't block the state lock
        threading.Thread(target=self._execute_bash, args=[context]).start()

    def _execute_bash(self, context: RestartContext):
        try:
            logging.info(f"🚀 [RUNNING] Triggering restart_infra.sh...")
            script_path = Path(__file__).parent / "restart_infra.sh"
            cmd = ["bash", str(script_path)]

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logging.info("✅ [RUNNING] Infrastructure restarted successfully!")
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ [RUNNING] Error triggering script. Exit code: {e.returncode}\nOutput:\n{e.stdout}\n{e.stderr}")
        except Exception as e:
            logging.error(f"❌ [RUNNING] Unexpected error: {e}")
            
        # When finished, check if anyone queued another run
        with context.lock:
            if self.rerun_pending:
                logging.info("🔄 [RUNNING] Webhooks arrived while busy! Transitioning back to RUNNING...")
                context.set_state(RunningState(context))
            else:
                logging.info("🏁 [RUNNING] All queues clear. Transitioning to IDLE...")
                context.set_state(IdleState())

    def handle_webhook(self, context: RestartContext):
        logging.info("⏳ [RUNNING] Script is busy. Queuing exactly one re-run.")
        self.rerun_pending = True

# Initialize the State Machine Context to be imported by main.py
restart_manager = RestartContext()
