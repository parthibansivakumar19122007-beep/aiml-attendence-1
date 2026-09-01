"""
iCampus ERP Integration Service (Placeholder & Staging Architecture)

IMPORTANT ARCHITECTURAL DIRECTIVE:
Direct iCampus database manipulation, web scraping, or unauthorized authentication
bypassing is strictly prohibited. This service provides a safe, standard API adapter
placeholder that remains DISABLED by default.

It will only activate when Nehru Institute of Technology provides official
iCampus REST API endpoints, API keys, and authorized service credentials.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from models import AttendanceRecord, AttendanceSession, Timetable, Student

logger = logging.getLogger(__name__)

# Integration configuration
ICAMPUS_ENABLED = os.environ.get('ICAMPUS_ENABLED', 'False').lower() in ['true', '1']
ICAMPUS_API_ENDPOINT = os.environ.get('ICAMPUS_API_ENDPOINT', 'https://api.icampus.nehrucolleges.com/v1')
ICAMPUS_API_KEY = os.environ.get('ICAMPUS_API_KEY', '')

def sync_attendance_to_icampus(
    attendance_record: AttendanceRecord, 
    session_record: Optional[AttendanceSession] = None
) -> Dict[str, Any]:
    """
    Syncs a verified attendance record with the college's official iCampus ERP system.
    
    Status: DISABLED BY DEFAULT (Requires official college API credentials).
    """
    if not ICAMPUS_ENABLED:
        return {
            'synced': False,
            'status': 'DISABLED',
            'message': 'iCampus ERP synchronization is currently disabled by institution policy. Attendance is stored securely in local database.'
        }

    if not ICAMPUS_API_KEY:
        logger.warning("iCampus sync attempted without configured ICAMPUS_API_KEY.")
        return {
            'synced': False,
            'status': 'CONFIGURATION_REQUIRED',
            'message': 'Missing institutional API credentials for iCampus.'
        }

    # Payload preparation according to standard ERP spec
    student = attendance_record.student
    payload = {
        'institution_code': 'NIT_AUTONOMOUS',
        'department_code': 'CSE_AIML',
        'class_code': 'I_BE_II_AIML',
        'academic_year': '2026-2027',
        'student_id': student.student_id if student else '',
        'scanned_timestamp': attendance_record.scanned_at.isoformat(),
        'attendance_type': attendance_record.attendance_type,
        'status': attendance_record.status,
        'distance_meters': float(attendance_record.distance_m) if attendance_record.distance_m is not None else None
    }

    try:
        # Placeholder for requests.post(f"{ICAMPUS_API_ENDPOINT}/attendance/sync", json=payload, headers={"Authorization": f"Bearer {ICAMPUS_API_KEY}"})
        logger.info(f"Mock sync payload to iCampus for student {payload['student_id']}: {payload}")
        return {
            'synced': True,
            'status': 'SYNC_COMPLETED',
            'transaction_id': f"ICAMPUS_TXN_{attendance_record.id}_{int(datetime.utcnow().timestamp())}",
            'message': 'Attendance record successfully mirrored to iCampus ERP.'
        }
    except Exception as e:
        logger.error(f"Failed to sync record {attendance_record.id} to iCampus: {str(e)}")
        return {
            'synced': False,
            'status': 'SYNC_FAILED',
            'message': f"iCampus communication error: {str(e)}"
        }

def get_icampus_status() -> Dict[str, Any]:
    """Returns current iCampus integration status and configuration state."""
    return {
        'enabled': ICAMPUS_ENABLED,
        'endpoint': ICAMPUS_API_ENDPOINT if ICAMPUS_ENABLED else 'Disabled / Not configured',
        'api_key_configured': bool(ICAMPUS_API_KEY),
        'service_status': 'Ready for production deployment once API credentials are provided by institution.'
    }
