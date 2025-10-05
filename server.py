from flask import Flask, send_from_directory
import os

app = Flask(__name__)
TRANSCRIPTS_DIR = os.path.join(os.getcwd(), "transcripts")

@app.route("/")
def index():
    return "✅ Transcript server is running!"

@app.route("/transcripts/<path:filename>")
def serve_transcript(filename):
    return send_from_directory(TRANSCRIPTS_DIR, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)