#!/usr/bin/env python3
"""
Interactive Flight Booking Automation.

This script guides you through booking a flight by asking for all necessary
details and then automating the search and selection process.

Usage:
    python book_flight.py
"""

import sys
from colorama import Fore, Style

# Add parent directory to path
sys.path.insert(0, '.')

from utils.flight_booking_input import (
    collect_flight_details,
    format_booking_summary,
    confirm_booking,
)
from utils.flight_booking_workflow import execute_flight_booking


def main():
    """Main entry point for flight booking automation."""
    try:
        # Collect flight details from user
        booking_details = collect_flight_details()
        
        # Show summary
        summary = format_booking_summary(booking_details)
        print(summary)
        
        # Confirm booking
        if not confirm_booking():
            print(f"\n{Fore.RED}❌ Booking cancelled by user.{Style.RESET_ALL}\n")
            return
        
        # Execute booking workflow
        print(f"\n{Fore.GREEN}🚀 Starting flight booking automation...{Style.RESET_ALL}\n")
        execute_flight_booking(booking_details)
        
    except KeyboardInterrupt:
        print(f"\n\n{Fore.RED}🛑 Interrupted by user{Style.RESET_ALL}\n")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error: {e}{Style.RESET_ALL}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
