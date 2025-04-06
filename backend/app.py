from flask import Flask, jsonify, flash, redirect, render_template, request, session
from flask_restful import Api, Resource
from flask_cors import CORS
from tempfile import mkdtemp

from helpers.getEvents import getAllEvents

app = Flask(__name__)
CORS(app)
api = Api(app)

@app.route('/', methods = ['GET'])
def index():
  response = getAllEvents()
  return jsonify({'response': response})

if __name__ == "__main__":
    app.run(host = "127.0.0.1", port=5000, debug=True)