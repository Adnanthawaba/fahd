import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from src.models.user import db
from src.models.venue import Venue, VenueImage, EventType
from src.models.booking import Booking, Payment
from src.models.message import Message, Review

# Import route blueprints
from src.routes.user import user_bp
from src.routes.venue import venue_bp
from src.routes.booking import booking_bp
from src.routes.message import message_bp
from src.routes.auth import auth_bp
from src.routes.availability import availability_bp

# Get the parent directory (where the built frontend files are)
parent_dir = os.path.dirname(os.path.dirname(__file__))
static_folder = parent_dir

app = Flask(__name__, static_folder=static_folder)
app.config['SECRET_KEY'] = 'yemen_qaat_secret_key_2025'

# Enable CORS for all routes
CORS(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(venue_bp, url_prefix='/api/venues')
app.register_blueprint(booking_bp, url_prefix='/api/bookings')
app.register_blueprint(message_bp, url_prefix='/api/messages')
app.register_blueprint(availability_bp)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize database and create sample data
with app.app_context():
    db.create_all()
    
    # Create default event types if they don't exist
    if EventType.query.count() == 0:
        event_types = [
            EventType(name_en='Wedding', name_ar='زفاف', icon='wedding-rings'),
            EventType(name_en='Party', name_ar='حفلة', icon='party'),
            EventType(name_en='Meeting', name_ar='اجتماع', icon='meeting'),
            EventType(name_en='Funeral', name_ar='عزاء', icon='funeral'),
            EventType(name_en='Conference', name_ar='مؤتمر', icon='conference'),
            EventType(name_en='Birthday', name_ar='عيد ميلاد', icon='birthday')
        ]
        for event_type in event_types:
            db.session.add(event_type)
        db.session.commit()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

@app.route('/api/health')
def health_check():
    return {'status': 'healthy', 'app': 'Yemen Qa\'at API', 'version': '1.0.0'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
