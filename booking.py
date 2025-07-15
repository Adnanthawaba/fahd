from flask import Blueprint, jsonify, request
from src.models.user import User, db
from src.models.venue import Venue, EventType
from src.models.booking import Booking, Payment, BookingStatus, PaymentStatus, PaymentMethod
from datetime import datetime, date, time
from sqlalchemy import and_, or_
import uuid

booking_bp = Blueprint('booking', __name__)

def generate_booking_reference():
    """Generate unique booking reference"""
    return f"YQ{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"

@booking_bp.route('', methods=['POST'])
def create_booking():
    """Create new booking"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['customer_id', 'venue_id', 'event_type_id', 
                          'event_date', 'start_time', 'end_time', 'guest_count']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate customer exists
        customer = User.query.get(data['customer_id'])
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Validate venue exists and is active
        venue = Venue.query.get(data['venue_id'])
        if not venue or not venue.is_active:
            return jsonify({'error': 'Venue not found or inactive'}), 404
        
        # Validate event type
        event_type = EventType.query.get(data['event_type_id'])
        if not event_type:
            return jsonify({'error': 'Event type not found'}), 404
        
        # Parse date and time
        try:
            event_date = datetime.strptime(data['event_date'], '%Y-%m-%d').date()
            start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'Invalid date or time format'}), 400
        
        # Check if date is in the future
        if event_date <= date.today():
            return jsonify({'error': 'Event date must be in the future'}), 400
        
        # Check if end time is after start time
        if end_time <= start_time:
            return jsonify({'error': 'End time must be after start time'}), 400
        
        # Check venue availability
        existing_bookings = Booking.query.filter(
            and_(
                Booking.venue_id == data['venue_id'],
                Booking.event_date == event_date,
                Booking.booking_status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
                or_(
                    and_(Booking.start_time <= start_time, Booking.end_time > start_time),
                    and_(Booking.start_time < end_time, Booking.end_time >= end_time),
                    and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
                )
            )
        ).first()
        
        if existing_bookings:
            return jsonify({'error': 'Venue is not available for the selected time slot'}), 409
        
        # Check capacity
        if data['guest_count'] > venue.capacity:
            return jsonify({'error': f'Guest count exceeds venue capacity ({venue.capacity})'}), 400
        
        # Calculate pricing
        duration_hours = (datetime.combine(date.today(), end_time) - 
                         datetime.combine(date.today(), start_time)).total_seconds() / 3600
        
        if venue.price_per_hour:
            base_price = venue.price_per_hour * duration_hours
        elif venue.price_per_day:
            base_price = venue.price_per_day
        else:
            return jsonify({'error': 'Venue pricing not configured'}), 400
        
        additional_charges = data.get('additional_charges', 0.0)
        discount = data.get('discount', 0.0)
        total_amount = base_price + additional_charges - discount
        
        # Create booking
        booking = Booking(
            booking_reference=generate_booking_reference(),
            customer_id=data['customer_id'],
            venue_id=data['venue_id'],
            event_type_id=data['event_type_id'],
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            guest_count=data['guest_count'],
            event_title_en=data.get('event_title_en'),
            event_title_ar=data.get('event_title_ar'),
            special_requirements_en=data.get('special_requirements_en'),
            special_requirements_ar=data.get('special_requirements_ar'),
            base_price=base_price,
            additional_charges=additional_charges,
            discount=discount,
            total_amount=total_amount,
            booking_status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING
        )
        
        db.session.add(booking)
        db.session.commit()
        
        language = data.get('language', 'ar')
        return jsonify({
            'message': 'Booking created successfully',
            'booking': booking.to_dict(language=language)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Get booking details"""
    try:
        language = request.args.get('language', 'ar')
        booking = Booking.query.get_or_404(booking_id)
        
        booking_data = booking.to_dict(language=language)
        
        # Add related data
        booking_data['customer'] = booking.customer.to_dict(language=language)
        booking_data['venue'] = booking.venue.to_dict(language=language)
        booking_data['event_type'] = booking.event_type.to_dict(language=language)
        booking_data['payments'] = [payment.to_dict() for payment in booking.payments]
        
        return jsonify(booking_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/customer/<int:customer_id>', methods=['GET'])
def get_customer_bookings(customer_id):
    """Get bookings for a customer"""
    try:
        language = request.args.get('language', 'ar')
        status = request.args.get('status')  # pending, confirmed, cancelled, completed
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        customer = User.query.get_or_404(customer_id)
        
        query = Booking.query.filter_by(customer_id=customer_id)
        
        if status:
            query = query.filter(Booking.booking_status == BookingStatus(status))
        
        query = query.order_by(Booking.created_at.desc())
        bookings = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'customer': customer.to_dict(language=language),
            'bookings': [booking.to_dict(language=language) for booking in bookings.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': bookings.total,
                'pages': bookings.pages,
                'has_next': bookings.has_next,
                'has_prev': bookings.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/venue/<int:venue_id>', methods=['GET'])
def get_venue_bookings(venue_id):
    """Get bookings for a venue (venue owner only)"""
    try:
        language = request.args.get('language', 'ar')
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        venue = Venue.query.get_or_404(venue_id)
        
        query = Booking.query.filter_by(venue_id=venue_id)
        
        if status:
            query = query.filter(Booking.booking_status == BookingStatus(status))
        
        query = query.order_by(Booking.created_at.desc())
        bookings = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'venue': venue.to_dict(language=language),
            'bookings': [booking.to_dict(language=language) for booking in bookings.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': bookings.total,
                'pages': bookings.pages,
                'has_next': bookings.has_next,
                'has_prev': bookings.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/<int:booking_id>/confirm', methods=['POST'])
def confirm_booking(booking_id):
    """Confirm booking (venue owner only)"""
    try:
        data = request.json
        booking = Booking.query.get_or_404(booking_id)
        
        # Verify venue ownership
        owner_id = data.get('owner_id')
        if booking.venue.owner_id != owner_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if booking.booking_status != BookingStatus.PENDING:
            return jsonify({'error': 'Only pending bookings can be confirmed'}), 400
        
        booking.booking_status = BookingStatus.CONFIRMED
        booking.confirmed_at = datetime.utcnow()
        db.session.commit()
        
        language = data.get('language', 'ar')
        return jsonify({
            'message': 'Booking confirmed successfully',
            'booking': booking.to_dict(language=language)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel booking"""
    try:
        data = request.json
        booking = Booking.query.get_or_404(booking_id)
        
        # Verify authorization (customer or venue owner)
        user_id = data.get('user_id')
        if user_id != booking.customer_id and user_id != booking.venue.owner_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if booking.booking_status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
            return jsonify({'error': 'Booking cannot be cancelled'}), 400
        
        booking.booking_status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.utcnow()
        booking.cancelled_by_id = user_id
        booking.cancellation_reason_en = data.get('reason_en')
        booking.cancellation_reason_ar = data.get('reason_ar')
        
        db.session.commit()
        
        language = data.get('language', 'ar')
        return jsonify({
            'message': 'Booking cancelled successfully',
            'booking': booking.to_dict(language=language)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/<int:booking_id>/payment', methods=['POST'])
def create_payment(booking_id):
    """Create payment for booking"""
    try:
        data = request.json
        booking = Booking.query.get_or_404(booking_id)
        
        # Validate payment method
        try:
            payment_method = PaymentMethod(data['payment_method'])
        except ValueError:
            return jsonify({'error': 'Invalid payment method'}), 400
        
        amount = data.get('amount', booking.total_amount)
        
        # Validate amount
        if amount <= 0 or amount > booking.total_amount:
            return jsonify({'error': 'Invalid payment amount'}), 400
        
        # Create payment record
        payment = Payment(
            booking_id=booking_id,
            payment_reference=f"PAY{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}",
            amount=amount,
            payment_method=payment_method,
            payment_status=PaymentStatus.PENDING,
            transaction_id=data.get('transaction_id'),
            bank_name=data.get('bank_name'),
            account_number=data.get('account_number'),
            transfer_receipt_url=data.get('transfer_receipt_url')
        )
        
        db.session.add(payment)
        
        # Update booking payment status
        total_paid = sum(p.amount for p in booking.payments if p.payment_status == PaymentStatus.PAID)
        total_paid += amount  # Include current payment
        
        if total_paid >= booking.total_amount:
            booking.payment_status = PaymentStatus.PAID
        elif total_paid > 0:
            booking.payment_status = PaymentStatus.PARTIAL
        
        # For cash payments, mark as paid immediately
        if payment_method == PaymentMethod.CASH:
            payment.payment_status = PaymentStatus.PAID
            payment.paid_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment created successfully',
            'payment': payment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/payment/<int:payment_id>/confirm', methods=['POST'])
def confirm_payment(payment_id):
    """Confirm payment (venue owner only)"""
    try:
        data = request.json
        payment = Payment.query.get_or_404(payment_id)
        booking = payment.booking
        
        # Verify venue ownership
        owner_id = data.get('owner_id')
        if booking.venue.owner_id != owner_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if payment.payment_status != PaymentStatus.PENDING:
            return jsonify({'error': 'Payment already processed'}), 400
        
        payment.payment_status = PaymentStatus.PAID
        payment.paid_at = datetime.utcnow()
        
        # Update booking payment status
        total_paid = sum(p.amount for p in booking.payments if p.payment_status == PaymentStatus.PAID)
        
        if total_paid >= booking.total_amount:
            booking.payment_status = PaymentStatus.PAID
        elif total_paid > 0:
            booking.payment_status = PaymentStatus.PARTIAL
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment confirmed successfully',
            'payment': payment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/stats/venue/<int:venue_id>', methods=['GET'])
def get_venue_booking_stats(venue_id):
    """Get booking statistics for venue"""
    try:
        venue = Venue.query.get_or_404(venue_id)
        
        # Get booking counts by status
        stats = {
            'total_bookings': Booking.query.filter_by(venue_id=venue_id).count(),
            'pending_bookings': Booking.query.filter_by(
                venue_id=venue_id, 
                booking_status=BookingStatus.PENDING
            ).count(),
            'confirmed_bookings': Booking.query.filter_by(
                venue_id=venue_id, 
                booking_status=BookingStatus.CONFIRMED
            ).count(),
            'completed_bookings': Booking.query.filter_by(
                venue_id=venue_id, 
                booking_status=BookingStatus.COMPLETED
            ).count(),
            'cancelled_bookings': Booking.query.filter_by(
                venue_id=venue_id, 
                booking_status=BookingStatus.CANCELLED
            ).count()
        }
        
        # Calculate revenue
        completed_bookings = Booking.query.filter_by(
            venue_id=venue_id, 
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID
        ).all()
        
        stats['total_revenue'] = sum(booking.total_amount for booking in completed_bookings)
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

