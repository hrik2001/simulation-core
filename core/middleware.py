from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import traceback
from .utils import send_telegram_message

class ExceptionMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        exception_details = "".join(traceback.format_exception(None, exception, exception.__traceback__))
        message = (
            "<b>🚨 Exception in Llamarisk Backend</b>\n"
            f"<b>URL:</b> {request.path}\n"
            f"<b>Method:</b> {request.method}\n"
            f"<b>Exception:</b> {type(exception).__name__}\n"
            f"<b>Details:</b>\n<pre>{exception_details}</pre>"
        )
        send_telegram_message(message)
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)

