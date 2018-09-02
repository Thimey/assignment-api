from flask import Flask, request, jsonify
from flask_cors import CORS

from solver import solver

app = Flask(__name__)
CORS(app)

@app.route("/solve", methods=['POST'])
def solve_allocation():
    data = request.get_json()

    solution = solver(data)

    return jsonify({
        "solved": solution
    })

if __name__ == '__main__':
    app.run(debug=True)