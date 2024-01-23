import os

# Ensure the instance log folder exists
try:
    os.makedirs(os.path.join(os.getcwd(), 'instance', 'log'))
except OSError:
    pass

bind="0.0.0.0:8000"
workers = 3 
logpath='instance/log'
errorlog = os.path.join(logpath, "gunicorn.error")
accesslog = os.path.join(logpath, "gunicorn.access")
loglevel = "debug"