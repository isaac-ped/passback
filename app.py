from flask import Flask
from app_dispatch import create_endpoints, generate_shell_functions

app = Flask(__name__)

generate_shell_functions(123)

create_endpoints(app)

