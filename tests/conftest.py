import os

# The application intentionally refuses to infer a security mode. Tests opt in
# before test modules import the module-level FastAPI application.
os.environ["APP_ENV"] = "test"
