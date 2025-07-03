# project_root/main_api/celery_worker.py

from celery import Celery

celery_app = Celery(
    "zammad_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.conf.task_routes = {
    "main_api.zammad_auto_agent.handle_ticket_async": {"queue": "zammad"},
}
