# Flight Booking Automation - User Guide

## Overview

The Flight Booking Automation system provides an interactive way to book flights by collecting all necessary information from you and then automating the search and selection process.

## How to Use

### Method 1: Using the dedicated script (Recommended)

```bash
python book_flight.py
```

### Method 2: Using main.py

```bash
python main.py --flight-booking
# OR
python main.py --book-flight
# OR
python main.py -f
```

## What Information You'll Need

The system will ask you for:

1. **Origin City** - Where you're departing from
2. **Destination City** - Where you're traveling to
3. **Departure Date** - When you want to leave (formats: YYYY-MM-DD or DD/MM/YYYY)
4. **Trip Type** - One-way or Round-trip
5. **Return Date** - If round-trip (must be after departure)
6. **Time Preference** - Morning, Afternoon, Evening, Night, or Any time
7. **Passengers** - Number of adults, children, and infants
8. **Class** - Economy, Premium Economy, Business, or First Class
9. **Date Flexibility** - How flexible you are with dates (0-3 days)

## Example Session

```
✈️  Flight Booking Automation
============================

📍 From which city are you departing?
> Delhi

📍 To which city are you traveling?
> Mumbai

📅 Departure date
   Formats: YYYY-MM-DD or DD/MM/YYYY
   Example: 2026-02-10 or 10/02/2026
> 10/02/2026

🔄 Trip type
   1. One-way
   2. Round-trip
> 1

⏰ Preferred departure time
   1. Morning (6AM-12PM)
   2. Afternoon (12PM-6PM)
   3. Evening (6PM-12AM)
   4. Night (12AM-6AM)
   5. Any time
> 1

👥 Number of passengers
   Adults (12+ years): 1
   Children (2-12 years): 0
   Infants (under 2 years): 0

💺 Preferred class
   1. Economy
   2. Premium Economy
   3. Business
   4. First Class
> 1

📆 Date flexibility
   0. Exact dates only
   1. ±1 day
   2. ±2 days
   3. ±3 days
> 0

============================================================
📋 BOOKING SUMMARY
============================================================

From: Delhi
To: Mumbai
Departure: February 10, 2026
Type: One-Way
Time: Morning
Passengers: 1 Adult(s)
Class: Economy

============================================================

✅ Proceed with booking? (Y/N)
> Y

🚀 Starting flight booking automation...
```

## What the System Does

1. **Collects Information** - Asks you for all flight details
2. **Shows Summary** - Displays everything for your confirmation
3. **Opens Browser** - Launches browser and navigates to booking site
4. **Fills Form** - Automatically fills the search form
5. **Searches Flights** - Executes the search
6. **Selects Flight** - Helps select based on your preferences
7. **Stops Before Payment** - For safety, stops at payment page

## Important Safety Notes

⚠️ **The system will NOT enter any payment information**

The automation will stop at the payment page, and you must complete the payment manually. This is a safety feature to protect your financial information.

## Supported Booking Websites

Currently optimized for:
- Google Flights (default)
- Can be adapted for MakeMyTrip, Goibibo, Cleartrip, etc.

## Troubleshooting

### "Invalid city name"
- Make sure you're entering only letters and spaces
- City name must be at least 2 characters

### "Invalid date"
- Use format: YYYY-MM-DD or DD/MM/YYYY
- Departure date must be in the future
- Return date must be after departure

### "Number of infants cannot exceed number of adults"
- Each infant must have an accompanying adult

## Tips for Best Results

1. **Be Specific** - Use full city names (e.g., "New Delhi" instead of "Delhi")
2. **Check Dates** - Double-check your dates before confirming
3. **Time Preference** - Select a specific time range for better results
4. **Stay Nearby** - Keep the browser window visible during automation
5. **Manual Override** - You can always take manual control if needed

## Emergency Stop

Press **Ctrl+C** at any time to stop the automation and close the browser.

## Questions?

For issues or questions, check the main README.md or create an issue in the repository.
