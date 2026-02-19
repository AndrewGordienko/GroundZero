import sys
import os

# Add the root directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Now we can import and run the app correctly
from groundzero.chess_app.app import app

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)