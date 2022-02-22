import redis
from celery import Celery

celery = Celery("task", broker='redis://localhost:6379/0', backend="redis://localhost:6379/0")
db = redis.Redis('localhost', decode_responses=True)


@celery.task(bind=True)
def async_command(self, host, command):
    progress = 10
    self.update_state(state='RUNNING',
                      meta={'progress': progress, 'message': f"Preparing command on {host['name']}"})

    # get the host object
    host_obj = None

    # get some information about the command
    command_info = host_obj.find_command(command)

    if(command_info is not None):
        progress = 50
        self.update_state(state='RUNNING',
                          meta={'progress': progress, 'message': f"Running {command_info['name']} on {host['name']}"})

        # run the command on the host
        host_obj.run_command(command)

    return {'progress': 100, 'message': 'Command Complete'}
