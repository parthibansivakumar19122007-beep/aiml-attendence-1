import math
from typing import Tuple, Optional

def haversine_distance_meters(
    lat1: float, 
    lon1: float, 
    lat2: float, 
    lon2: float
) -> float:
    """
    Calculates the great-circle distance between two GPS points on Earth
    using the standard Haversine formula in meters.
    
    Formula:
    a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
    c = 2 * atan2(√a, √(1−a))
    d = R * c
    where R = 6,371,000 meters (Earth's mean radius)
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        raise ValueError("Latitude and longitude coordinates cannot be None.")

    # Earth radius in meters
    R = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c

    return round(distance, 2)

def verify_geofence_proximity(
    faculty_lat: float,
    faculty_lng: float,
    student_lat: float,
    student_lng: float,
    max_radius_meters: float = 50.0
) -> Tuple[bool, float, str]:
    """
    Validates whether the student's GPS coordinates fall within the allowed security radius.
    
    Returns:
    (is_within_geofence: bool, distance_meters: float, message: str)
    """
    try:
        dist = haversine_distance_meters(faculty_lat, faculty_lng, student_lat, student_lng)
    except Exception as e:
        return False, 0.0, f"Location calculation error: {str(e)}"

    if dist <= max_radius_meters:
        return True, dist, f"Location verified: You are {dist}m from the classroom center (within {max_radius_meters}m area)."
    else:
        return False, dist, f"Attendance rejected: You are outside the {max_radius_meters:.0f}-meter attendance area ({dist:.1f}m away)."
