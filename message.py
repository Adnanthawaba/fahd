from flask import Blueprint, jsonify, request
from src.models.user import User, db
from src.models.venue import Venue
from src.models.booking import Booking
from src.models.message import Message, Review, MessageType, MessageStatus
from datetime import datetime
from sqlalchemy import and_, or_

message_bp = Blueprint('message', __name__)

@message_bp.route('', methods=['POST'])
def send_message():
    """Send message between users"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['sender_id', 'receiver_id', 'content']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate users exist
        sender = User.query.get(data['sender_id'])
        receiver = User.query.get(data['receiver_id'])
        
        if not sender or not receiver:
            return jsonify({'error': 'Sender or receiver not found'}), 404
        
        # Validate message type
        message_type = MessageType.TEXT
        if data.get('message_type'):
            try:
                message_type = MessageType(data['message_type'])
            except ValueError:
                return jsonify({'error': 'Invalid message type'}), 400
        
        # Create message
        message = Message(
            sender_id=data['sender_id'],
            receiver_id=data['receiver_id'],
            booking_id=data.get('booking_id'),
            message_type=message_type,
            content=data['content'],
            file_url=data.get('file_url'),
            file_name=data.get('file_name'),
            file_size=data.get('file_size'),
            status=MessageStatus.SENT
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'message': 'Message sent successfully',
            'data': message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/conversation/<int:user1_id>/<int:user2_id>', methods=['GET'])
def get_conversation(user1_id, user2_id):
    """Get conversation between two users"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        booking_id = request.args.get('booking_id')
        
        # Build query
        query = Message.query.filter(
            or_(
                and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
                and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
            )
        )
        
        if booking_id:
            query = query.filter(Message.booking_id == booking_id)
        
        query = query.order_by(Message.created_at.desc())
        messages = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Mark messages as read for the current user (assuming user1_id is current user)
        unread_messages = Message.query.filter(
            and_(
                Message.sender_id == user2_id,
                Message.receiver_id == user1_id,
                Message.status != MessageStatus.READ
            )
        ).all()
        
        for msg in unread_messages:
            msg.status = MessageStatus.READ
            msg.read_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'messages': [message.to_dict() for message in reversed(messages.items)],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': messages.total,
                'pages': messages.pages,
                'has_next': messages.has_next,
                'has_prev': messages.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/conversations/<int:user_id>', methods=['GET'])
def get_user_conversations(user_id):
    """Get all conversations for a user"""
    try:
        # Get unique conversation partners
        sent_to = db.session.query(Message.receiver_id).filter(Message.sender_id == user_id).distinct()
        received_from = db.session.query(Message.sender_id).filter(Message.receiver_id == user_id).distinct()
        
        partner_ids = set()
        for row in sent_to:
            partner_ids.add(row[0])
        for row in received_from:
            partner_ids.add(row[0])
        
        conversations = []
        for partner_id in partner_ids:
            # Get last message
            last_message = Message.query.filter(
                or_(
                    and_(Message.sender_id == user_id, Message.receiver_id == partner_id),
                    and_(Message.sender_id == partner_id, Message.receiver_id == user_id)
                )
            ).order_by(Message.created_at.desc()).first()
            
            # Get unread count
            unread_count = Message.query.filter(
                and_(
                    Message.sender_id == partner_id,
                    Message.receiver_id == user_id,
                    Message.status != MessageStatus.READ
                )
            ).count()
            
            # Get partner info
            partner = User.query.get(partner_id)
            
            if last_message and partner:
                conversations.append({
                    'partner': partner.to_dict(),
                    'last_message': last_message.to_dict(),
                    'unread_count': unread_count
                })
        
        # Sort by last message time
        conversations.sort(key=lambda x: x['last_message']['created_at'], reverse=True)
        
        return jsonify(conversations), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/<int:message_id>/read', methods=['POST'])
def mark_message_read(message_id):
    """Mark message as read"""
    try:
        message = Message.query.get_or_404(message_id)
        
        if message.status != MessageStatus.READ:
            message.status = MessageStatus.READ
            message.read_at = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'message': 'Message marked as read',
            'data': message.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Review endpoints
@message_bp.route('/reviews', methods=['POST'])
def create_review():
    """Create venue review"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['customer_id', 'venue_id', 'rating']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate rating
        rating = data['rating']
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        # Validate customer and venue exist
        customer = User.query.get(data['customer_id'])
        venue = Venue.query.get(data['venue_id'])
        
        if not customer or not venue:
            return jsonify({'error': 'Customer or venue not found'}), 404
        
        # Check if customer has a completed booking for this venue
        booking = None
        if data.get('booking_id'):
            booking = Booking.query.filter_by(
                id=data['booking_id'],
                customer_id=data['customer_id'],
                venue_id=data['venue_id']
            ).first()
            
            if not booking:
                return jsonify({'error': 'Booking not found'}), 404
        
        # Check if review already exists for this booking
        if booking:
            existing_review = Review.query.filter_by(
                customer_id=data['customer_id'],
                venue_id=data['venue_id'],
                booking_id=booking.id
            ).first()
            
            if existing_review:
                return jsonify({'error': 'Review already exists for this booking'}), 409
        
        # Create review
        review = Review(
            customer_id=data['customer_id'],
            venue_id=data['venue_id'],
            booking_id=data.get('booking_id'),
            rating=rating,
            title_en=data.get('title_en'),
            title_ar=data.get('title_ar'),
            comment_en=data.get('comment_en'),
            comment_ar=data.get('comment_ar')
        )
        
        db.session.add(review)
        
        # Update venue rating
        venue_reviews = Review.query.filter_by(venue_id=data['venue_id'], is_approved=True).all()
        if venue_reviews:
            total_rating = sum(r.rating for r in venue_reviews) + rating
            total_reviews = len(venue_reviews) + 1
            venue.average_rating = total_rating / total_reviews
            venue.total_reviews = total_reviews
        else:
            venue.average_rating = rating
            venue.total_reviews = 1
        
        db.session.commit()
        
        language = data.get('language', 'ar')
        return jsonify({
            'message': 'Review created successfully',
            'review': review.to_dict(language=language)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/reviews/venue/<int:venue_id>', methods=['GET'])
def get_venue_reviews(venue_id):
    """Get reviews for a venue"""
    try:
        language = request.args.get('language', 'ar')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        venue = Venue.query.get_or_404(venue_id)
        
        query = Review.query.filter_by(venue_id=venue_id, is_approved=True)
        query = query.order_by(Review.created_at.desc())
        reviews = query.paginate(page=page, per_page=per_page, error_out=False)
        
        review_data = []
        for review in reviews.items:
            review_dict = review.to_dict(language=language)
            review_dict['customer'] = review.customer.to_dict(language=language)
            review_data.append(review_dict)
        
        return jsonify({
            'venue': venue.to_dict(language=language),
            'reviews': review_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': reviews.total,
                'pages': reviews.pages,
                'has_next': reviews.has_next,
                'has_prev': reviews.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/reviews/customer/<int:customer_id>', methods=['GET'])
def get_customer_reviews(customer_id):
    """Get reviews by a customer"""
    try:
        language = request.args.get('language', 'ar')
        customer = User.query.get_or_404(customer_id)
        
        reviews = Review.query.filter_by(customer_id=customer_id).order_by(Review.created_at.desc()).all()
        
        review_data = []
        for review in reviews:
            review_dict = review.to_dict(language=language)
            review_dict['venue'] = review.venue.to_dict(language=language)
            review_data.append(review_dict)
        
        return jsonify({
            'customer': customer.to_dict(language=language),
            'reviews': review_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/reviews/<int:review_id>', methods=['PUT'])
def update_review(review_id):
    """Update review (customer only)"""
    try:
        data = request.json
        review = Review.query.get_or_404(review_id)
        
        # Verify ownership
        if review.customer_id != data.get('customer_id'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update fields
        if 'rating' in data:
            rating = data['rating']
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({'error': 'Rating must be between 1 and 5'}), 400
            review.rating = rating
        
        if 'title_en' in data:
            review.title_en = data['title_en']
        if 'title_ar' in data:
            review.title_ar = data['title_ar']
        if 'comment_en' in data:
            review.comment_en = data['comment_en']
        if 'comment_ar' in data:
            review.comment_ar = data['comment_ar']
        
        review.updated_at = datetime.utcnow()
        
        # Recalculate venue rating
        venue = review.venue
        venue_reviews = Review.query.filter_by(venue_id=venue.id, is_approved=True).all()
        if venue_reviews:
            total_rating = sum(r.rating for r in venue_reviews)
            venue.average_rating = total_rating / len(venue_reviews)
        
        db.session.commit()
        
        language = data.get('language', 'ar')
        return jsonify({
            'message': 'Review updated successfully',
            'review': review.to_dict(language=language)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    """Delete review (customer only)"""
    try:
        data = request.json
        review = Review.query.get_or_404(review_id)
        
        # Verify ownership
        if review.customer_id != data.get('customer_id'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        venue = review.venue
        db.session.delete(review)
        
        # Recalculate venue rating
        venue_reviews = Review.query.filter_by(venue_id=venue.id, is_approved=True).all()
        if venue_reviews:
            total_rating = sum(r.rating for r in venue_reviews)
            venue.average_rating = total_rating / len(venue_reviews)
            venue.total_reviews = len(venue_reviews)
        else:
            venue.average_rating = 0.0
            venue.total_reviews = 0
        
        db.session.commit()
        
        return jsonify({'message': 'Review deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

