from flask import Flask
from app_dispatch import make_endpoints

app = Flask(__name__)

make_endpoints(app)

