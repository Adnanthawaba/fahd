from flask import Blueprint, jsonify, request
from src.models.user import User, UserRole, db
from src.models.venue import Venue, VenueImage, EventType
from src.models.booking import Booking
from datetime import datetime, date
from sqlalchemy import and_, or_

venue_bp = Blueprint('venue', __name__)

@venue_bp.route('', methods=['GET'])
def get_venues():
    """Get venues with filtering and search"""
    try:
        language = request.args.get('language', 'ar')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Filters
        city = request.args.get('city')
        governorate = request.args.get('governorate')
        event_type_id = request.args.get('event_type_id')
        min_capacity = request.args.get('min_capacity', type=int)
        max_capacity = request.args.get('max_capacity', type=int)
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        search_query = request.args.get('search')
        
        # Base query
        query = Venue.query.filter(Venue.is_active == True)
        
        # Apply filters
        if city:
            if language == 'en':
                query = query.filter(Venue.city_en.ilike(f'%{city}%'))
            else:
                query = query.filter(or_(
                    Venue.city_ar.ilike(f'%{city}%'),
                    Venue.city_en.ilike(f'%{city}%')
                ))
        
        if governorate:
            if language == 'en':
                query = query.filter(Venue.governorate_en.ilike(f'%{governorate}%'))
            else:
                query = query.filter(or_(
                    Venue.governorate_ar.ilike(f'%{governorate}%'),
                    Venue.governorate_en.ilike(f'%{governorate}%')
                ))
        
        if min_capacity:
            query = query.filter(Venue.capacity >= min_capacity)
        
        if max_capacity:
            query = query.filter(Venue.capacity <= max_capacity)
        
        if min_price:
            query = query.filter(or_(
                Venue.price_per_hour >= min_price,
                Venue.price_per_day >= min_price
            ))
        
        if max_price:
            query = query.filter(or_(
                Venue.price_per_hour <= max_price,
                Venue.price_per_day <= max_price
            ))
        
        if search_query:
            if language == 'en':
                query = query.filter(or_(
                    Venue.name_en.ilike(f'%{search_query}%'),
                    Venue.description_en.ilike(f'%{search_query}%'),
                    Venue.address_en.ilike(f'%{search_query}%')
                ))
            else:
                query = query.filter(or_(
                    Venue.name_ar.ilike(f'%{search_query}%'),
                    Venue.name_en.ilike(f'%{search_query}%'),
                    Venue.description_ar.ilike(f'%{search_query}%'),
                    Venue.description_en.ilike(f'%{search_query}%'),
                    Venue.address_ar.ilike(f'%{search_query}%'),
                    Venue.address_en.ilike(f'%{search_query}%')
                ))
        
        # Order by rating and creation date
        query = query.order_by(Venue.average_rating.desc(), Venue.created_at.desc())
        
        # Paginate
        venues = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'venues': [venue.to_dict(language=language) for venue in venues.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': venues.total,
                'pages': venues.pages,
                'has_next': venues.has_next,
                'has_prev': venues.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/<int:venue_id>', methods=['GET'])
def get_venue(venue_id):
    """Get venue details"""
    try:
        language = request.args.get('language', 'ar')
        venue = Venue.query.get_or_404(venue_id)
        
        if not venue.is_active:
            return jsonify({'error': 'Venue not found'}), 404
        
        venue_data = venue.to_dict(language=language)
        
        # Add owner information
        owner = User.query.get(venue.owner_id)
        if owner:
            venue_data['owner'] = {
                'id': owner.id,
                'name': f"{owner.first_name_en} {owner.last_name_en}",
                'phone': owner.phone_number,
                'whatsapp': owner.whatsapp_number,
                'email': owner.email,
                'business_name': owner.business_name_en if language == 'en' else owner.business_name_ar
            }
        
        return jsonify(venue_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@venue_bp.route('', methods=['POST'])
def create_venue():
    """Create new venue (venue owners only)"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name_en', 'name_ar', 'address_en', 'address_ar', 
                          'city_en', 'city_ar', 'governorate_en', 'governorate_ar',
                          'capacity', 'owner_id']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Verify owner exists and is venue owner
        owner = User.query.get(data['owner_id'])
        if not owner or not owner.is_venue_owner():
            return jsonify({'error': 'Invalid venue owner'}), 400
        
        # Create venue
        venue = Venue(
            name_en=data['name_en'],
            name_ar=data['name_ar'],
            description_en=data.get('description_en'),
            description_ar=data.get('description_ar'),
            owner_id=data['owner_id'],
            address_en=data['address_en'],
            address_ar=data['address_ar'],
            city_en=data['city_en'],
            city_ar=data['city_ar'],
            governorate_en=data['governorate_en'],
            governorate_ar=data['governorate_ar'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            capacity=data['capacity'],
            area_sqm=data.get('area_sqm'),
            price_per_hour=data.get('price_per_hour'),
            price_per_day=data.get('price_per_day'),
            amenities=data.get('amenities', []),
            phone_primary=data.get('phone_primary'),
            phone_secondary=data.get('phone_secondary'),
            whatsapp_number=data.get('whatsapp_number'),
            email=data.get('email')
        )
        
        db.session.add(venue)
        db.session.commit()
        
        # Add images if provided
        if data.get('images'):
            for img_data in data['images']:
                image = VenueImage(
                    venue_id=venue.id,
                    image_url=img_data['url'],
                    image_type=img_data.get('type', 'gallery'),
                    caption_en=img_data.get('caption_en'),
                    caption_ar=img_data.get('caption_ar'),
                    display_order=img_data.get('display_order', 0)
                )
                db.session.add(image)
        
        db.session.commit()
        
        language = data.get('language', 'ar')
        return jsonify({
            'message': 'Venue created successfully',
            'venue': venue.to_dict(language=language)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/<int:venue_id>', methods=['PUT'])
def update_venue(venue_id):
    """Update venue (owner only)"""
    try:
        data = request.json
        venue = Venue.query.get_or_404(venue_id)
        
        # Verify ownership (in real app, use authentication)
        owner_id = data.get('owner_id')
        if venue.owner_id != owner_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update fields
        updateable_fields = [
            'name_en', 'name_ar', 'description_en', 'description_ar',
            'address_en', 'address_ar', 'city_en', 'city_ar',
            'governorate_en', 'governorate_ar', 'latitude', 'longitude',
            'capacity', 'area_sqm', 'price_per_hour', 'price_per_day',
            'amenities', 'phone_primary', 'phone_secondary', 
            'whatsapp_number', 'email'
        ]
        
        for field in updateable_fields:
            if field in data:
                setattr(venue, field, data[field])
        
        venue.updated_at = datetime.utcnow()
        db.session.commit()
        
        language = data.get('language', 'ar')
        return jsonify({
            'message': 'Venue updated successfully',
            'venue': venue.to_dict(language=language)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/<int:venue_id>/availability', methods=['GET'])
def check_availability(venue_id):
    """Check venue availability for specific date"""
    try:
        venue = Venue.query.get_or_404(venue_id)
        check_date = request.args.get('date')
        
        if not check_date:
            return jsonify({'error': 'Date parameter is required'}), 400
        
        try:
            check_date = datetime.strptime(check_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Get bookings for this date
        bookings = Booking.query.filter(
            and_(
                Booking.venue_id == venue_id,
                Booking.event_date == check_date,
                Booking.booking_status.in_(['pending', 'confirmed'])
            )
        ).all()
        
        booked_slots = []
        for booking in bookings:
            booked_slots.append({
                'start_time': booking.start_time.strftime('%H:%M'),
                'end_time': booking.end_time.strftime('%H:%M'),
                'booking_id': booking.id,
                'status': booking.booking_status.value
            })
        
        return jsonify({
            'venue_id': venue_id,
            'date': check_date.isoformat(),
            'is_available': len(booked_slots) == 0,
            'booked_slots': booked_slots
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/owner/<int:owner_id>', methods=['GET'])
def get_owner_venues(owner_id):
    """Get venues by owner"""
    try:
        language = request.args.get('language', 'ar')
        
        owner = User.query.get_or_404(owner_id)
        if not owner.is_venue_owner():
            return jsonify({'error': 'User is not a venue owner'}), 400
        
        venues = Venue.query.filter_by(owner_id=owner_id).order_by(Venue.created_at.desc()).all()
        
        return jsonify({
            'owner': owner.to_dict(language=language),
            'venues': [venue.to_dict(language=language) for venue in venues]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/event-types', methods=['GET'])
def get_event_types():
    """Get all event types"""
    try:
        language = request.args.get('language', 'ar')
        event_types = EventType.query.filter_by(is_active=True).all()
        
        return jsonify([event_type.to_dict(language=language) for event_type in event_types]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/<int:venue_id>/images', methods=['POST'])
def add_venue_image(venue_id):
    """Add image to venue"""
    try:
        data = request.json
        venue = Venue.query.get_or_404(venue_id)
        
        # Verify ownership
        owner_id = data.get('owner_id')
        if venue.owner_id != owner_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        image = VenueImage(
            venue_id=venue_id,
            image_url=data['image_url'],
            image_type=data.get('image_type', 'gallery'),
            caption_en=data.get('caption_en'),
            caption_ar=data.get('caption_ar'),
            display_order=data.get('display_order', 0)
        )
        
        db.session.add(image)
        db.session.commit()
        
        language = data.get('language', 'ar')
        return jsonify({
            'message': 'Image added successfully',
            'image': image.to_dict(language=language)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@venue_bp.route('/featured', methods=['GET'])
def get_featured_venues():
    """Get featured venues (highest rated)"""
    try:
        language = request.args.get('language', 'ar')
        limit = int(request.args.get('limit', 6))
        
        venues = Venue.query.filter(
            and_(Venue.is_active == True, Venue.is_verified == True)
        ).order_by(
            Venue.average_rating.desc(),
            Venue.total_reviews.desc()
        ).limit(limit).all()
        
        return jsonify([venue.to_dict(language=language) for venue in venues]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

