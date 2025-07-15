from flask import Blueprint, request, jsonify
from datetime import datetime, date, time, timedelta
from sqlalchemy import and_, or_
from src.models.availability import VenueAvailability, VenueBlockedDates, VenueOperatingHours, AvailabilityStatus, db
from src.models.venue import Venue
from src.models.booking import Booking
import calendar

availability_bp = Blueprint('availability', __name__)

@availability_bp.route('/api/availability/venue/<int:venue_id>', methods=['GET'])
def get_venue_availability(venue_id):
    """Get availability for a specific venue"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = date.today()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
        if not end_date:
            end_date = start_date + timedelta(days=30)
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get venue
        venue = Venue.query.get_or_404(venue_id)
        
        # Get availability slots
        availability_slots = VenueAvailability.query.filter(
            and_(
                VenueAvailability.venue_id == venue_id,
                VenueAvailability.date >= start_date,
                VenueAvailability.date <= end_date
            )
        ).order_by(VenueAvailability.date, VenueAvailability.start_time).all()
        
        # Get blocked dates
        blocked_dates = VenueBlockedDates.query.filter(
            and_(
                VenueBlockedDates.venue_id == venue_id,
                or_(
                    and_(VenueBlockedDates.start_date <= end_date, VenueBlockedDates.end_date >= start_date)
                )
            )
        ).all()
        
        # Get operating hours
        operating_hours = VenueOperatingHours.query.filter_by(venue_id=venue_id).all()
        
        # Generate availability calendar
        availability_calendar = generate_availability_calendar(
            venue_id, start_date, end_date, availability_slots, blocked_dates, operating_hours
        )
        
        return jsonify({
            'success': True,
            'venue': venue.to_dict(),
            'availability_calendar': availability_calendar,
            'availability_slots': [slot.to_dict() for slot in availability_slots],
            'blocked_dates': [blocked.to_dict() for blocked in blocked_dates],
            'operating_hours': [hours.to_dict() for hours in operating_hours]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@availability_bp.route('/api/availability/check', methods=['POST'])
def check_availability():
    """Check if a venue is available for specific date and time"""
    try:
        data = request.get_json()
        venue_id = data.get('venue_id')
        check_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
        start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
        end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
        
        # Check if venue exists
        venue = Venue.query.get_or_404(venue_id)
        
        # Check blocked dates
        blocked = VenueBlockedDates.query.filter(
            and_(
                VenueBlockedDates.venue_id == venue_id,
                VenueBlockedDates.start_date <= check_date,
                VenueBlockedDates.end_date >= check_date
            )
        ).first()
        
        if blocked:
            return jsonify({
                'success': True,
                'available': False,
                'reason': 'Date is blocked',
                'blocked_reason': blocked.reason
            })
        
        # Check operating hours
        day_of_week = check_date.weekday()
        operating_hours = VenueOperatingHours.query.filter_by(
            venue_id=venue_id,
            day_of_week=day_of_week
        ).first()
        
        if operating_hours and operating_hours.is_closed:
            return jsonify({
                'success': True,
                'available': False,
                'reason': 'Venue is closed on this day'
            })
        
        if operating_hours:
            if start_time < operating_hours.open_time or end_time > operating_hours.close_time:
                return jsonify({
                    'success': True,
                    'available': False,
                    'reason': 'Outside operating hours',
                    'operating_hours': {
                        'open': operating_hours.open_time.strftime('%H:%M'),
                        'close': operating_hours.close_time.strftime('%H:%M')
                    }
                })
        
        # Check existing bookings
        conflicting_slots = VenueAvailability.query.filter(
            and_(
                VenueAvailability.venue_id == venue_id,
                VenueAvailability.date == check_date,
                VenueAvailability.status.in_([AvailabilityStatus.BOOKED, AvailabilityStatus.MAINTENANCE]),
                or_(
                    and_(VenueAvailability.start_time <= start_time, VenueAvailability.end_time > start_time),
                    and_(VenueAvailability.start_time < end_time, VenueAvailability.end_time >= end_time),
                    and_(VenueAvailability.start_time >= start_time, VenueAvailability.end_time <= end_time)
                )
            )
        ).all()
        
        if conflicting_slots:
            return jsonify({
                'success': True,
                'available': False,
                'reason': 'Time slot already booked',
                'conflicting_slots': [slot.to_dict() for slot in conflicting_slots]
            })
        
        return jsonify({
            'success': True,
            'available': True,
            'message': 'Venue is available for the requested time'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@availability_bp.route('/api/availability/venue/<int:venue_id>/block', methods=['POST'])
def block_venue_dates(venue_id):
    """Block dates for a venue (owner only)"""
    try:
        data = request.get_json()
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
        reason = data.get('reason', 'Blocked by owner')
        created_by = data.get('user_id')  # Should come from authentication
        
        # Check if venue exists and user is owner
        venue = Venue.query.get_or_404(venue_id)
        
        # Create blocked date entry
        blocked_date = VenueBlockedDates(
            venue_id=venue_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            created_by=created_by
        )
        
        db.session.add(blocked_date)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Dates blocked successfully',
            'blocked_date': blocked_date.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@availability_bp.route('/api/availability/venue/<int:venue_id>/operating-hours', methods=['POST'])
def set_operating_hours(venue_id):
    """Set operating hours for a venue"""
    try:
        data = request.get_json()
        
        # Check if venue exists
        venue = Venue.query.get_or_404(venue_id)
        
        # Clear existing operating hours
        VenueOperatingHours.query.filter_by(venue_id=venue_id).delete()
        
        # Add new operating hours
        for day_data in data.get('operating_hours', []):
            operating_hour = VenueOperatingHours(
                venue_id=venue_id,
                day_of_week=day_data.get('day_of_week'),
                open_time=datetime.strptime(day_data.get('open_time'), '%H:%M').time() if day_data.get('open_time') else None,
                close_time=datetime.strptime(day_data.get('close_time'), '%H:%M').time() if day_data.get('close_time') else None,
                is_closed=day_data.get('is_closed', False)
            )
            db.session.add(operating_hour)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Operating hours updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_availability_calendar(venue_id, start_date, end_date, availability_slots, blocked_dates, operating_hours):
    """Generate a calendar view of availability"""
    calendar_data = {}
    current_date = start_date
    
    while current_date <= end_date:
        day_status = get_day_availability_status(
            venue_id, current_date, availability_slots, blocked_dates, operating_hours
        )
        
        calendar_data[current_date.isoformat()] = day_status
        current_date += timedelta(days=1)
    
    return calendar_data

def get_day_availability_status(venue_id, check_date, availability_slots, blocked_dates, operating_hours):
    """Get availability status for a specific day"""
    # Check if date is blocked
    for blocked in blocked_dates:
        if blocked.start_date <= check_date <= blocked.end_date:
            return {
                'status': 'blocked',
                'reason': blocked.reason,
                'available_slots': 0,
                'total_slots': 0
            }
    
    # Check operating hours
    day_of_week = check_date.weekday()
    operating_hour = next((oh for oh in operating_hours if oh.day_of_week == day_of_week), None)
    
    if operating_hour and operating_hour.is_closed:
        return {
            'status': 'closed',
            'reason': 'Venue closed',
            'available_slots': 0,
            'total_slots': 0
        }
    
    # Count availability slots for this date
    day_slots = [slot for slot in availability_slots if slot.date == check_date]
    available_slots = len([slot for slot in day_slots if slot.status == AvailabilityStatus.AVAILABLE])
    total_slots = len(day_slots)
    
    if total_slots == 0:
        return {
            'status': 'available',
            'reason': 'No specific slots defined',
            'available_slots': 'unlimited',
            'total_slots': 'unlimited'
        }
    
    if available_slots == 0:
        return {
            'status': 'fully_booked',
            'reason': 'All slots booked',
            'available_slots': 0,
            'total_slots': total_slots
        }
    elif available_slots < total_slots:
        return {
            'status': 'partially_available',
            'reason': 'Some slots available',
            'available_slots': available_slots,
            'total_slots': total_slots
        }
    else:
        return {
            'status': 'available',
            'reason': 'All slots available',
            'available_slots': available_slots,
            'total_slots': total_slots
        }

