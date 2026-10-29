"""Booking payloads used as the columns of the API matrix.

Every API operation is run against each dataset, so a regression that only
affects one kind of data (unicode names, unpaid deposits...) shows up as a
single red cell instead of hiding behind a green "happy path".
"""

DATASETS = {
    "standard": {
        "firstname": "Jim",
        "lastname": "Brown",
        "totalprice": 111,
        "depositpaid": True,
        "bookingdates": {"checkin": "2026-11-01", "checkout": "2026-11-05"},
        "additionalneeds": "Breakfast",
    },
    "no_deposit": {
        "firstname": "Sara",
        "lastname": "Levy",
        "totalprice": 80,
        "depositpaid": False,
        "bookingdates": {"checkin": "2026-12-10", "checkout": "2026-12-11"},
        "additionalneeds": "None",
    },
    "unicode_name": {
        "firstname": "Zoë",
        "lastname": "Ben-Ami",
        "totalprice": 250,
        "depositpaid": True,
        "bookingdates": {"checkin": "2027-01-15", "checkout": "2027-01-18"},
        "additionalneeds": "Late check-out",
    },
    "long_stay": {
        "firstname": "Marc",
        "lastname": "Dupont",
        "totalprice": 5400,
        "depositpaid": True,
        "bookingdates": {"checkin": "2027-03-01", "checkout": "2027-06-30"},
        "additionalneeds": "Lunch",
    },
}
