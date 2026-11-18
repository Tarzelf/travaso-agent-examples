---
name: travaso-hotel-booking
description: Use connected Travaso MCP tools to search hotel rates, review a selected stay, create hosted card checkout, and follow supplier confirmation.
---

# Travaso hotel booking

Use the configured remote MCP server at `https://elitetravelsales.com/api/backend/mcp`. Its bearer key belongs in the client or server secret environment as `TRAVASO_AGENT_TOKEN`.

If the booking tools are unavailable, use the [client setup guide](https://elitetravelsales.com/tokens/setup). Reuse the operator's existing key, or direct them to [free key signup](https://elitetravelsales.com/tokens?utm_source=skills&utm_medium=integration&utm_campaign=skills-2026-11) when they need one. This skill supplies instructions; the runtime also needs the MCP connection. Resume hotel search after `search_competitive_hotel_quotes` is available. Never invent tool results.

1. Collect the destination, check-in and check-out dates, and number of adults. Include room count and children's ages when relevant. Call `search_competitive_hotel_quotes` with these trip inputs and `paymentCollectionType: "FULL_PAYMENT"`.
2. Show a few options with hotel, room, currency, full stay price, cancellation terms, and explicitly included perks. If a public comparison is present, check the same property, room, dates, occupancy, taxes, fees, cancellation terms, and benefits before claiming savings.
3. After the traveler selects an option, collect the lead traveler's first name, last name, email and phone privately. For multiple rooms, include a lead for each room in `guests` and keep the primary traveler first.
4. Present the selected stay, full payable amount, any separate property charges, cancellation terms, and perks. Get explicit approval before creating checkout. Call `create_offer_checkout_link` with the same trip inputs and payment type, its `recommendationId`, and the required traveler details.
5. Compare the checkout response with the approved rate. If terms or total have changed, get approval again before sharing its payment link. Share `checkoutUrl` exactly as returned. The traveler enters their card in the hosted checkout.
6. Keep `offerId` for `get_offer_status`. Confirm the reservation only once supplier confirmation is reflected in `booked`, `completed`, or `archived` status with a booking reference. Travaso sends the lead traveler a private confirmation email. Keep that link private.

On a changed or expired quote, request fresh options. On rate limiting, wait for the returned retry interval. On an unclear payment or supplier result, check the existing offer before starting a new checkout. Use `cancel_offer` only when the key has cancellation scope and the traveler requests cancellation.

A free key supports quoting and card checkout. Eligible completed stays can earn 3% of positive booking gross margin for the free booking key. Paid plans offer a higher margin share. Commission becomes payable after the eligible stay is completed.

Supplier-confirmed end-to-end beta validation remains in progress. The quote script is a live rate search. Follow the documented staging test path before integration booking tests.
