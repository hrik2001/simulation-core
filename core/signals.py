import traceback
import sys
from celery.signals import task_failure
from core.utils import send_telegram_message

@task_failure.connect
def celery_task_failure_handler(**kwargs):
    try:
        # Comprehensive error extraction with safety checks
        error_info = {
            "Task Name": kwargs.get('sender', {}).name if hasattr(kwargs.get('sender'), 'name') else "Unknown",
            "Task ID": kwargs.get('task_id', "N/A"),
            "Exception Type": str(type(kwargs.get('exception', "No Exception")).__name__),
            "Exception": str(kwargs.get('exception', "No Exception Details")),
            "Args": str(kwargs.get('args', "No Args")),
            "Kwargs": str(kwargs.get('kwargs', "No Kwargs")),
        }

        # Attempt to generate traceback details
        try:
            exc = kwargs.get('exception')
            if exc:
                exception_details = "".join(traceback.format_exception(
                    type(exc), 
                    exc, 
                    exc.__traceback__ if hasattr(exc, '__traceback__') else None
                ))
            else:
                exception_details = "No traceback available"
        except Exception as formatting_error:
            exception_details = f"Error formatting traceback: {formatting_error}"

        # Construct detailed error message
        message = "<b>🚨 Celery Task Failure 🚨</b>\n"
        for key, value in error_info.items():
            message += f"<b>{key}:</b> {value}\n"
        
        message += f"\n<b>Traceback:</b>\n<pre>{exception_details}</pre>"

        # Send the detailed error message
        send_telegram_message(message)

    except Exception as general_error:
        # Fallback error reporting
        fallback_message = (
            "<b>🚨 CRITICAL: Error in Celery Task Failure Handler</b>\n"
            f"<b>Error:</b> {type(general_error).__name__}\n"
            f"<b>Details:</b> {str(general_error)}"
        )
        try:
            send_telegram_message(fallback_message)
        except:
            # If even sending a Telegram message fails, print to stderr
            print(fallback_message, file=sys.stderr)
