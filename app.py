from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
)
import os
import random
import string
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configuration for file uploads
UPLOAD_FOLDER = "uploads"
SRC_FOLDER = "src"  # Add this line for the src folder
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# File to store link preview data
DATA_FILE = "link_previews.json"


# Store link data in app config instead of global variable
def get_link_previews():
    """Get the link previews from the storage"""
    if "link_previews" not in app.config:
        try:
            with open(DATA_FILE, "r") as f:
                app.config["link_previews"] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            app.config["link_previews"] = {}
    return app.config["link_previews"]


def save_link_previews():
    """Save link previews to a JSON file"""
    with open(DATA_FILE, "w") as f:
        json.dump(app.config["link_previews"], f, indent=4)


def generate_short_id(length=6):
    """Generate a random short ID for links"""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        link = request.form["link"]
        preview_text = request.form["preview_text"]
        preview_description = request.form.get(
            "preview_description", ""
        )  # Optional field
        preview_image_file = request.files["preview_image_file"]

        if not link or not preview_text or not preview_image_file:
            flash(
                "Destination URL, Preview Title, and Preview Image are required!",
                "danger",
            )
            return render_template("create.html")

        if not allowed_file(preview_image_file.filename):
            flash(
                "Invalid image format! Allowed formats: PNG, JPG, JPEG, GIF", "danger"
            )
            return render_template("create.html")

        filename = secure_filename(preview_image_file.filename)
        preview_image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        preview_image = url_for("uploaded_file", filename=filename, _external=True)

        # Generate unique short ID
        link_previews = get_link_previews()
        short_id = generate_short_id()
        while short_id in link_previews:
            short_id = generate_short_id()

        # Store the link data
        link_previews[short_id] = {
            "link": link,
            "preview_image": preview_image,
            "preview_text": preview_text,
            "preview_description": preview_description,
        }

        # Save to JSON file
        save_link_previews()

        # Redirect to success page showing the shortlink
        return redirect(url_for("success", short_id=short_id))

    return render_template("create.html")


@app.route("/success/<short_id>")
def success(short_id):
    link_previews = get_link_previews()

    if short_id not in link_previews:
        return redirect(url_for("index"))

    shortlink = url_for("short_redirect", short_id=short_id, _external=True)
    return render_template("success.html", shortlink=shortlink)


@app.route("/s/<short_id>")
def short_redirect(short_id):
    link_previews = get_link_previews()

    if short_id not in link_previews:
        return redirect(url_for("index"))

    preview = link_previews[short_id]
    return render_template("redirect.html", preview=preview)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# Add a new route to serve files from the src directory
@app.route("/src/<filename>")
def serve_src(filename):
    return send_from_directory(SRC_FOLDER, filename)


if __name__ == "__main__":
    # Make sure the uploads directory exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Make sure the src directory exists
    if not os.path.exists(SRC_FOLDER):
        os.makedirs(SRC_FOLDER)

    # Initialize by loading data from file
    get_link_previews()

    # Run the app
    app.run(debug=True, port=2000, host="0.0.0.0")
