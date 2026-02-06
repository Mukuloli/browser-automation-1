"""
Flight Booking Input Collector.

This module provides an interactive interface to collect all necessary
information from users for flight booking automation.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from colorama import Fore, Style, init

# Initialize colorama for Windows
init(autoreset=True)


class FlightBookingInput:
    """Interactive flight booking information collector."""
    
    def __init__(self):
        """Initialize the input collector."""
        self.booking_details = {}
    
    def collect_flight_details(self) -> Dict:
        """
        Collect all flight booking details from user interactively.
        
        Returns:
            Dictionary with all booking details
        """
        print(f"\n{Fore.CYAN}{'=' * 60}")
        print(f"{Fore.CYAN}✈️  Flight Booking Automation")
        print(f"{Fore.CYAN}{'=' * 60}\n")
        
        # Collect details
        self.booking_details["origin"] = self._get_origin()
        self.booking_details["destination"] = self._get_destination()
        self.booking_details["departure_date"] = self._get_departure_date()
        self.booking_details["trip_type"] = self._get_trip_type()
        
        if self.booking_details["trip_type"] == "round-trip":
            self.booking_details["return_date"] = self._get_return_date()
        
        self.booking_details["time_preference"] = self._get_time_preference()
        self.booking_details["passengers"] = self._get_passenger_count()
        self.booking_details["class"] = self._get_class_preference()
        self.booking_details["flexible_dates"] = self._get_date_flexibility()
        
        return self.booking_details
    
    def _get_origin(self) -> str:
        """Get origin city from user."""
        while True:
            origin = input(f"{Fore.GREEN}📍 From which city are you departing?\n{Fore.WHITE}> ").strip()
            if self._validate_city(origin):
                return origin
            print(f"{Fore.RED}❌ Please enter a valid city name.")
    
    def _get_destination(self) -> str:
        """Get destination city from user."""
        while True:
            destination = input(f"\n{Fore.GREEN}📍 To which city are you traveling?\n{Fore.WHITE}> ").strip()
            if self._validate_city(destination):
                if destination.lower() == self.booking_details.get("origin", "").lower():
                    print(f"{Fore.RED}❌ Destination cannot be the same as origin.")
                    continue
                return destination
            print(f"{Fore.RED}❌ Please enter a valid city name.")
    
    def _get_departure_date(self) -> str:
        """Get departure date from user."""
        print(f"\n{Fore.GREEN}📅 Departure date")
        print(f"{Fore.YELLOW}   Examples: 10 feb, 15 february 2026, tomorrow, next monday")
        print(f"{Fore.YELLOW}   Or use: 2026-02-10 or 10/02/2026")
        
        while True:
            date_str = input(f"{Fore.WHITE}> ").strip()
            parsed_date = self._validate_date(date_str, is_departure=True)
            if parsed_date:
                return parsed_date
            print(f"{Fore.RED}❌ Invalid date. Try: 10 feb, tomorrow, or 2026-02-10")
    
    def _get_trip_type(self) -> str:
        """Get trip type (one-way or round-trip)."""
        print(f"\n{Fore.GREEN}🔄 Trip type")
        print(f"{Fore.YELLOW}   1. One-way")
        print(f"{Fore.YELLOW}   2. Round-trip")
        
        while True:
            choice = input(f"{Fore.WHITE}> ").strip()
            if choice in ["1", "one", "oneway", "one-way"]:
                return "one-way"
            elif choice in ["2", "round", "roundtrip", "round-trip"]:
                return "round-trip"
            print(f"{Fore.RED}❌ Please enter 1 for one-way or 2 for round-trip.")
    
    def _get_return_date(self) -> str:
        """Get return date for round-trip."""
        print(f"\n{Fore.GREEN}📅 Return date")
        print(f"{Fore.YELLOW}   Examples: 20 feb, next week, 5 days later")
        
        departure = datetime.strptime(self.booking_details["departure_date"], "%Y-%m-%d")
        
        while True:
            date_str = input(f"{Fore.WHITE}> ").strip()
            parsed_date = self._validate_date(date_str, is_departure=False)
            if parsed_date:
                return_date = datetime.strptime(parsed_date, "%Y-%m-%d")
                if return_date <= departure:
                    print(f"{Fore.RED}❌ Return date must be after departure date.")
                    continue
                return parsed_date
            print(f"{Fore.RED}❌ Invalid date. Try: 20 feb, next week, or 2026-02-20")
    
    def _get_time_preference(self) -> str:
        """Get preferred departure time."""
        print(f"\n{Fore.GREEN}⏰ Preferred departure time")
        print(f"{Fore.YELLOW}   1. Morning (6AM-12PM)")
        print(f"{Fore.YELLOW}   2. Afternoon (12PM-6PM)")
        print(f"{Fore.YELLOW}   3. Evening (6PM-12AM)")
        print(f"{Fore.YELLOW}   4. Night (12AM-6AM)")
        print(f"{Fore.YELLOW}   5. Any time")
        
        while True:
            choice = input(f"{Fore.WHITE}> ").strip()
            if choice == "1":
                return "morning"
            elif choice == "2":
                return "afternoon"
            elif choice == "3":
                return "evening"
            elif choice == "4":
                return "night"
            elif choice == "5":
                return "any"
            print(f"{Fore.RED}❌ Please enter a number between 1 and 5.")
    
    def _get_passenger_count(self) -> Dict[str, int]:
        """Get passenger count details."""
        print(f"\n{Fore.GREEN}👥 Number of passengers")
        
        passengers = {}
        
        # Adults
        while True:
            try:
                adults = int(input(f"{Fore.YELLOW}   Adults (12+ years): {Fore.WHITE}").strip())
                if adults > 0 and adults <= 9:
                    passengers["adults"] = adults
                    break
                print(f"{Fore.RED}   ❌ Please enter a number between 1 and 9.")
            except ValueError:
                print(f"{Fore.RED}   ❌ Please enter a valid number.")
        
        # Children
        while True:
            try:
                children = int(input(f"{Fore.YELLOW}   Children (2-12 years): {Fore.WHITE}").strip())
                if children >= 0 and children <= 9:
                    passengers["children"] = children
                    break
                print(f"{Fore.RED}   ❌ Please enter a number between 0 and 9.")
            except ValueError:
                print(f"{Fore.RED}   ❌ Please enter a valid number.")
        
        # Infants
        while True:
            try:
                infants = int(input(f"{Fore.YELLOW}   Infants (under 2 years): {Fore.WHITE}").strip())
                if infants >= 0 and infants <= passengers["adults"]:
                    passengers["infants"] = infants
                    break
                print(f"{Fore.RED}   ❌ Number of infants cannot exceed number of adults.")
            except ValueError:
                print(f"{Fore.RED}   ❌ Please enter a valid number.")
        
        return passengers
    
    def _get_class_preference(self) -> str:
        """Get travel class preference."""
        print(f"\n{Fore.GREEN}💺 Preferred class")
        print(f"{Fore.YELLOW}   1. Economy")
        print(f"{Fore.YELLOW}   2. Premium Economy")
        print(f"{Fore.YELLOW}   3. Business")
        print(f"{Fore.YELLOW}   4. First Class")
        
        while True:
            choice = input(f"{Fore.WHITE}> ").strip()
            if choice == "1":
                return "economy"
            elif choice == "2":
                return "premium-economy"
            elif choice == "3":
                return "business"
            elif choice == "4":
                return "first"
            print(f"{Fore.RED}❌ Please enter a number between 1 and 4.")
    
    def _get_date_flexibility(self) -> int:
        """Get date flexibility preference."""
        print(f"\n{Fore.GREEN}📆 Date flexibility")
        print(f"{Fore.YELLOW}   0. Exact dates only")
        print(f"{Fore.YELLOW}   1. ±1 day")
        print(f"{Fore.YELLOW}   2. ±2 days")
        print(f"{Fore.YELLOW}   3. ±3 days")
        
        while True:
            choice = input(f"{Fore.WHITE}> ").strip()
            if choice in ["0", "1", "2", "3"]:
                return int(choice)
            print(f"{Fore.RED}❌ Please enter a number between 0 and 3.")
    
    def _validate_city(self, city: str) -> bool:
        """
        Validate city name.
        
        Args:
            city: City name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not city or len(city) < 2:
            return False
        # Basic validation - only letters and spaces
        return all(c.isalpha() or c.isspace() for c in city)
    
    def _validate_date(self, date_str: str, is_departure: bool = True) -> Optional[str]:
        """
        Validate and parse date string (supports natural language).
        
        Args:
            date_str: Date string to validate
            is_departure: Whether this is a departure date (must be future)
            
        Returns:
            Formatted date string (YYYY-MM-DD) if valid, None otherwise
        """
        date_str_lower = date_str.lower().strip()
        today = datetime.now().date()
        parsed_date = None
        
        # Try natural language dates first
        try:
            # Relative dates
            if date_str_lower in ["today"]:
                parsed_date = datetime.now()
            elif date_str_lower in ["tomorrow", "tmrw"]:
                parsed_date = datetime.now() + timedelta(days=1)
            elif date_str_lower in ["day after tomorrow", "day after"]:
                parsed_date = datetime.now() + timedelta(days=2)
            elif "next week" in date_str_lower:
                parsed_date = datetime.now() + timedelta(weeks=1)
            elif "next month" in date_str_lower:
                # Add approximately 30 days
                parsed_date = datetime.now() + timedelta(days=30)
            
            # Days later (e.g., "5 days later", "3 days")
            elif "day" in date_str_lower:
                import re
                match = re.search(r'(\d+)\s*day', date_str_lower)
                if match:
                    days = int(match.group(1))
                    parsed_date = datetime.now() + timedelta(days=days)
            
            # Weekday names (e.g., "next monday", "monday")
            elif any(day in date_str_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                weekdays = {
                    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                    "friday": 4, "saturday": 5, "sunday": 6
                }
                for day_name, day_num in weekdays.items():
                    if day_name in date_str_lower:
                        current_weekday = datetime.now().weekday()
                        days_ahead = day_num - current_weekday
                        if days_ahead <= 0 or "next" in date_str_lower:
                            days_ahead += 7
                        parsed_date = datetime.now() + timedelta(days=days_ahead)
                        break
            
            # Short date formats (e.g., "10 feb", "15 february", "10 feb 2026")
            else:
                # Try various natural formats
                natural_formats = [
                    "%d %b",           # 10 feb
                    "%d %B",           # 10 february
                    "%d %b %Y",        # 10 feb 2026
                    "%d %B %Y",        # 10 february 2026
                    "%b %d",           # feb 10
                    "%B %d",           # february 10
                    "%b %d %Y",        # feb 10 2026
                    "%B %d %Y",        # february 10 2026
                ]
                
                for fmt in natural_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        # If no year specified, use current or next year
                        if "%Y" not in fmt:
                            current_year = datetime.now().year
                            parsed_date = parsed_date.replace(year=current_year)
                            # If date is in the past, use next year
                            if parsed_date.date() < today:
                                parsed_date = parsed_date.replace(year=current_year + 1)
                        break
                    except ValueError:
                        continue
        
        except Exception:
            pass
        
        # If natural language didn't work, try standard formats
        if not parsed_date:
            standard_formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]
            
            for fmt in standard_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
        
        # Validate the parsed date
        if parsed_date:
            # Check if date is in the future (for departure)
            if is_departure:
                if parsed_date.date() < today:
                    print(f"{Fore.RED}❌ Departure date must be in the future.")
                    return None
            
            # Return in standard format
            return parsed_date.strftime("%Y-%m-%d")
        
        return None
    
    def format_booking_summary(self) -> str:
        """
        Format booking details as a summary string.
        
        Returns:
            Formatted summary string
        """
        details = self.booking_details
        
        summary = f"\n{Fore.CYAN}{'=' * 60}\n"
        summary += f"{Fore.CYAN}📋 BOOKING SUMMARY\n"
        summary += f"{Fore.CYAN}{'=' * 60}\n\n"
        
        summary += f"{Fore.GREEN}From:{Style.RESET_ALL} {details['origin']}\n"
        summary += f"{Fore.GREEN}To:{Style.RESET_ALL} {details['destination']}\n"
        summary += f"{Fore.GREEN}Departure:{Style.RESET_ALL} {self._format_date(details['departure_date'])}\n"
        
        if details["trip_type"] == "round-trip":
            summary += f"{Fore.GREEN}Return:{Style.RESET_ALL} {self._format_date(details['return_date'])}\n"
        
        summary += f"{Fore.GREEN}Type:{Style.RESET_ALL} {details['trip_type'].title()}\n"
        summary += f"{Fore.GREEN}Time:{Style.RESET_ALL} {details['time_preference'].title()}\n"
        
        # Passengers
        passengers = details["passengers"]
        passenger_str = f"{passengers['adults']} Adult(s)"
        if passengers["children"] > 0:
            passenger_str += f", {passengers['children']} Child(ren)"
        if passengers["infants"] > 0:
            passenger_str += f", {passengers['infants']} Infant(s)"
        summary += f"{Fore.GREEN}Passengers:{Style.RESET_ALL} {passenger_str}\n"
        
        summary += f"{Fore.GREEN}Class:{Style.RESET_ALL} {details['class'].replace('-', ' ').title()}\n"
        
        if details["flexible_dates"] > 0:
            summary += f"{Fore.GREEN}Flexibility:{Style.RESET_ALL} ±{details['flexible_dates']} day(s)\n"
        
        summary += f"\n{Fore.CYAN}{'=' * 60}\n"
        
        return summary
    
    def _format_date(self, date_str: str) -> str:
        """Format date string for display."""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%B %d, %Y")


def collect_flight_details() -> Dict:
    """
    Convenience function to collect flight booking details.
    
    Returns:
        Dictionary with all booking details
    """
    collector = FlightBookingInput()
    return collector.collect_flight_details()


def format_booking_summary(booking_details: Dict) -> str:
    """
    Format booking details as summary.
    
    Args:
        booking_details: Booking details dictionary
        
    Returns:
        Formatted summary string
    """
    collector = FlightBookingInput()
    collector.booking_details = booking_details
    return collector.format_booking_summary()


def confirm_booking() -> bool:
    """
    Ask user to confirm booking.
    
    Returns:
        True if confirmed, False otherwise
    """
    while True:
        response = input(f"\n{Fore.GREEN}✅ Proceed with booking? (Y/N)\n{Fore.WHITE}> ").strip().upper()
        if response in ["Y", "YES"]:
            return True
        elif response in ["N", "NO"]:
            return False
        print(f"{Fore.RED}❌ Please enter Y or N.")
