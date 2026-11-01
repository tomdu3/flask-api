from flask import Flask
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

@app.route('/')
def home():
    return "<h1>Flask REST API</h1>"

# class HelloWorld(Resource):
#     def get(self):
#         return {'hello': 'world'}

# api.add_resource(HelloWorld, '/')


def main() -> None:
    app.run(debug=True)


if __name__ == '__main__':
    main()