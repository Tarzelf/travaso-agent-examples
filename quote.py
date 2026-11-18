#!/usr/bin/env python3
"""Request hotel quotes and print consumer fields. Uses Python's standard library."""

import argparse
import datetime
from decimal import Decimal, InvalidOperation
import http.client
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


QUOTE_URL = "https://elitetravelsales.com/api/backend/agent/hotel-quotes"
MAX_RESPONSE_BYTES = 2_000_000


class QuoteError(Exception):
    """A message that is safe to show without request or server contents."""


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, url):
        raise QuoteError("The quote endpoint redirected. Check the official setup guide.")


def calendar_date(value):
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Use a date in YYYY-MM-DD format.") from None
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("Use a date in YYYY-MM-DD format.")
    return value


def positive_integer(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Enter a positive whole number.") from None
    if number < 1:
        raise argparse.ArgumentTypeError("Enter a positive whole number.")
    return number


def children_ages(value):
    try:
        ages = [int(part.strip()) for part in value.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError("Use comma-separated children's ages, for example 4,9.") from None
    if len(ages) > 8 or any(age < 0 or age > 17 for age in ages):
        raise argparse.ArgumentTypeError("Provide up to eight ages between 0 and 17.")
    return ages


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--location", required=True, help="City or destination")
    parser.add_argument("--check-in", type=calendar_date, required=True)
    parser.add_argument("--check-out", type=calendar_date, required=True)
    parser.add_argument("--adults", type=positive_integer, required=True)
    parser.add_argument("--rooms", type=positive_integer, default=1)
    parser.add_argument("--children-ages", type=children_ages, default=[], metavar="4,9")
    parser.add_argument("--save-checkout-template", type=Path, metavar="FILE",
                        help="Save the chosen rate and identical trip inputs with traveler placeholders")
    parser.add_argument("--selection", type=positive_integer, default=1,
                        help="One-based returned option to save (default 1)")
    args = parser.parse_args(argv)
    if not args.location.strip():
        parser.error("Enter a destination.")
    if args.check_in < datetime.date.today().isoformat() or args.check_out <= args.check_in:
        parser.error("Use a current or future check-in and a later check-out.")
    return args


def request_quotes(payload, token):
    if not token or any(character.isspace() for character in token):
        raise QuoteError("Set TRAVASO_AGENT_TOKEN in your environment before requesting quotes.")
    request = urllib.request.Request(
        QUOTE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Travaso-Builder-Example/1.0",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(RefuseRedirect())
    try:
        with opener.open(request, timeout=45) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise QuoteError("The key was rejected. Check its validity and quote permission.") from None
        if error.code == 429:
            delay = error.headers.get("Retry-After", "")
            suffix = " Retry after " + delay + " seconds." if delay.isdecimal() else " Wait before retrying."
            raise QuoteError("The quote allowance has been reached." + suffix) from None
        raise QuoteError("The quote service could not complete this request. Check the trip inputs or retry later.") from None
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException):
        raise QuoteError("The quote service could not be reached. Check your connection or retry later.") from None
    if len(body) > MAX_RESPONSE_BYTES:
        raise QuoteError("The quote response was too large. Try a narrower search.")
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise QuoteError("The quote service returned an unreadable response.") from None
    if not isinstance(data, dict) or not isinstance(data.get("recommendations"), list):
        raise QuoteError("The quote service returned an unexpected response.")
    return data


def text(value, missing="Not supplied"):
    if not isinstance(value, str) or not value.strip():
        return missing
    return " ".join(value.split())[:2000]


def money(value):
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return "Not supplied"
    if not amount.is_finite() or amount < 0 or amount > Decimal("999999999"):
        return "Not supplied"
    return format(amount, ".2f")


def display_quotes(recommendations):
    for index, item in enumerate(recommendations, 1):
        if not isinstance(item, dict):
            raise QuoteError("The quote service returned an unexpected option.")
        hotel = item.get("hotel") or {}
        room = item.get("room") or {}
        pricing = item.get("pricing") or {}
        if not all(isinstance(field, dict) for field in (hotel, room, pricing)):
            raise QuoteError("The quote service returned an unexpected option.")
        print("\n" + str(index) + ". " + text(hotel.get("name")))
        print("   Room       " + text(room.get("name")))
        print("   Stay total USD " + money(pricing.get("totalSellPrice")))
        print("   Per room/night USD " + money(pricing.get("effectiveNightlySellPrice")))
        print("   Cancellation " + text(room.get("cancellationPolicy"), "Not supplied. Verify before payment."))
        perks = room.get("rateTags")
        known_perks = [text(perk, "") for perk in perks if isinstance(perk, str)] if isinstance(perks, list) else []
        if isinstance(room.get("hasBreakfast"), (int, bool)) and room["hasBreakfast"] > 0:
            known_perks.insert(0, "Breakfast included, verify the allowance in the rate terms")
        print("   Known perks " + ("; ".join(known_perks) if known_perks else "No included perks supplied"))
        if pricing.get("quoteExpiresAt"):
            print("   Quote valid until " + text(pricing["quoteExpiresAt"]))
    print("\nCoverage: up to 3 ranked options from returned supplier inventory, in USD.")
    print("Review taxes, fees, room terms and perks before approval. Availability and prices can change.")


def save_template(path, payload, recommendations, selection):
    if selection > len(recommendations):
        raise QuoteError("The selected option is outside the returned quote list.")
    selected = recommendations[selection - 1]
    recommendation_id = selected.get("recommendationId")
    if not isinstance(recommendation_id, str) or not recommendation_id:
        raise QuoteError("The selected option has no checkout reference. Request a fresh quote.")
    template = {
        **payload,
        "recommendationId": recommendation_id,
        "firstName": "LEAD_FIRST_NAME",
        "lastName": "LEAD_LAST_NAME",
        "email": "traveler@example.com",
        "phoneNumber": "+15555550100",
    }
    try:
        # Exclusive creation keeps a later quote from silently replacing an approved selection.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(template, output, indent=2, ensure_ascii=False)
            output.write("\n")
    except FileExistsError:
        raise QuoteError("The template file already exists. Use a new filename for a new selection.") from None
    except OSError:
        raise QuoteError("The checkout template could not be saved.") from None
    print("\nSaved a local checkout template for option " + str(selection) + ".")


def main(argv=None):
    args = parse_args(argv)
    payload = {
        "location": args.location.strip(),
        "checkIn": args.check_in,
        "checkOut": args.check_out,
        "adults": args.adults,
        "rooms": args.rooms,
        "childrenAges": args.children_ages,
        "maxResults": 3,
        "paymentCollectionType": "FULL_PAYMENT",
    }
    try:
        result = request_quotes(payload, os.environ.get("TRAVASO_AGENT_TOKEN", ""))
        recommendations = result["recommendations"]
        if result.get("searchCoverage") == "partial":
            print("Some hotels could not be checked. Results show the rates that responded.")
        if not recommendations:
            print("No options matched this trip. Try another destination, date range, or room count.")
            return 0
        display_quotes(recommendations)
        if args.save_checkout_template:
            save_template(args.save_checkout_template, payload, recommendations, args.selection)
    except QuoteError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
