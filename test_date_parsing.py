"""
Quick test for natural language date parsing in flight booking.
"""

from utils.flight_booking_input import FlightBookingInput

def test_date_parsing():
    """Test various date input formats."""
    collector = FlightBookingInput()
    
    test_dates = [
        "10 feb",
        "15 february",
        "tomorrow",
        "next monday",
        "5 days",
        "next week",
        "2026-02-15",
        "10/02/2026",
        "feb 20",
        "20 february 2026",
    ]
    
    print("Testing Natural Language Date Parsing")
    print("=" * 50)
    
    for date_str in test_dates:
        result = collector._validate_date(date_str, is_departure=True)
        status = "✅" if result else "❌"
        print(f"{status} '{date_str}' → {result}")

if __name__ == "__main__":
    test_date_parsing()
