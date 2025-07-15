from flask import Blueprint, jsonify, request
from src.models.user import User, db, UserRole
from datetime import datetime

user_bp = Blueprint('user', __name__)

@user_bp.route('/', methods=['GET'])
def get_users():
    """Get all users"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/', methods=['POST'])
def create_user():
    """Create a new user"""
    data = request.json
    
    # Check if user already exists
    existing_user = User.query.filter(
        (User.email == data.get('email')) | 
        (User.phone_number == data.get('phone_number'))
    ).first()
    
    if existing_user:
        return jsonify({'error': 'User with this email or phone already exists'}), 400
    
    user = User(
        first_name_en=data.get('first_name_en', ''),
        first_name_ar=data.get('first_name_ar', ''),
        last_name_en=data.get('last_name_en', ''),
        last_name_ar=data.get('last_name_ar', ''),
        email=data['email'],
        phone_number=data['phone_number'],
        password_hash=data.get('password_hash', ''),  # In real app, hash the password
        role=UserRole(data.get('role', 'customer'))
    )
    
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user"""
    user = User.query.get_or_404(user_id)
    language = request.args.get('language', 'en')
    return jsonify(user.to_dict(language=language))

@user_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user profile"""
    user = User.query.get_or_404(user_id)
    data = request.json
    
    # Update basic information
    if 'first_name_en' in data:
        user.first_name_en = data['first_name_en']
    if 'first_name_ar' in data:
        user.first_name_ar = data['first_name_ar']
    if 'last_name_en' in data:
        user.last_name_en = data['last_name_en']
    if 'last_name_ar' in data:
        user.last_name_ar = data['last_name_ar']
    
    # Update contact information
    if 'email' in data:
        user.email = data['email']
    if 'phone_number' in data:
        user.phone_number = data['phone_number']
    if 'whatsapp_number' in data:
        user.whatsapp_number = data['whatsapp_number']
    
    # Update profile information
    if 'profile_image_url' in data:
        user.profile_image_url = data['profile_image_url']
    if 'date_of_birth' in data:
        if data['date_of_birth']:
            user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
    if 'gender' in data:
        user.gender = data['gender']
    
    # Update location
    if 'city_en' in data:
        user.city_en = data['city_en']
    if 'city_ar' in data:
        user.city_ar = data['city_ar']
    if 'governorate_en' in data:
        user.governorate_en = data['governorate_en']
    if 'governorate_ar' in data:
        user.governorate_ar = data['governorate_ar']
    
    # Update preferences
    if 'preferred_language' in data:
        user.preferred_language = data['preferred_language']
    if 'notification_preferences' in data:
        user.notification_preferences = data['notification_preferences']
    
    # Update business information (for venue owners)
    if 'business_name_en' in data:
        user.business_name_en = data['business_name_en']
    if 'business_name_ar' in data:
        user.business_name_ar = data['business_name_ar']
    if 'business_license' in data:
        user.business_license = data['business_license']
    if 'business_address_en' in data:
        user.business_address_en = data['business_address_en']
    if 'business_address_ar' in data:
        user.business_address_ar = data['business_address_ar']
    
    # Update role if provided
    if 'role' in data:
        user.role = UserRole(data['role'])
    
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    language = request.args.get('language', 'en')
    return jsonify(user.to_dict(language=language))

@user_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return '', 204

@user_bp.route('/<int:user_id>/verify-phone', methods=['POST'])
def verify_phone(user_id):
    """Verify user's phone number"""
    user = User.query.get_or_404(user_id)
    data = request.json
    
    # In a real app, you would verify the OTP code here
    verification_code = data.get('verification_code')
    
    if verification_code:  # Simple check for demo
        user.is_phone_verified = True
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Phone number verified successfully'})
    
    return jsonify({'error': 'Invalid verification code'}), 400

@user_bp.route('/<int:user_id>/verify-email', methods=['POST'])
def verify_email(user_id):
    """Verify user's email address"""
    user = User.query.get_or_404(user_id)
    data = request.json
    
    # In a real app, you would verify the email token here
    verification_token = data.get('verification_token')
    
    if verification_token:  # Simple check for demo
        user.is_email_verified = True
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Email address verified successfully'})
    
    return jsonify({'error': 'Invalid verification token'}), 400

@user_bp.route('/<int:user_id>/upload-avatar', methods=['POST'])
def upload_avatar(user_id):
    """Upload user avatar"""
    user = User.query.get_or_404(user_id)
    
    # In a real app, you would handle file upload here
    # For now, we'll just accept a URL
    data = request.json
    avatar_url = data.get('avatar_url')
    
    if avatar_url:
        user.profile_image_url = avatar_url
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Avatar uploaded successfully', 'avatar_url': avatar_url})
    
    return jsonify({'error': 'No avatar URL provided'}), 400
