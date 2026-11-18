# Travaso hotel booking for agents

Connect an agent to live hotel quotes, let a traveler approve a room, and create a hosted card checkout. This repository contains a Python quote example and remote MCP configuration for builders.

[Get a free key](https://elitetravelsales.com/tokens?utm_source=github&utm_medium=referral&utm_campaign=github-2026-11) · [Quickstart](https://elitetravelsales.com/hotel-booking-mcp?utm_source=github&utm_medium=referral&utm_campaign=github-2026-11) · [Client setup](https://elitetravelsales.com/tokens/setup)

## Request your first quote

Use Python 3.9 or newer. Save the key in your environment as `TRAVASO_AGENT_TOKEN` through your terminal or secret manager. Keep it out of chat, source control, and screenshots.

Choose future dates for your actual trip, then run this command.

```sh
python3 quote.py \
  --location Boston \
  --check-in YYYY-MM-DD \
  --check-out YYYY-MM-DD \
  --adults 2
```

For a family or multiple rooms, add `--rooms 2` or `--children-ages 4,9`. Quotes require destination, dates and party size. Names, email and phone are collected after a room is selected.

The script requests up to three ranked options through `POST https://elitetravelsales.com/api/backend/agent/hotel-quotes`. It shows the hotel, room, USD stay and nightly prices, cancellation terms, and supplied perks. It performs a rate search. Any checkout JSON it writes is a local template.

Save an option's exact trip inputs for the checkout step by adding these flags to the same quote command.

```sh
  --selection 1 --save-checkout-template checkout-request.json
```

Use a new filename when requesting a new selection. The script preserves the original destination, dates, adults, children, rooms, result count, payment type, and selected recommendation ID. `checkout-request.example.json` shows the expected shape.

## Connect a remote MCP client

The server uses Streamable HTTP at `https://elitetravelsales.com/api/backend/mcp`. Authentication uses `Authorization: Bearer <key>`.

- **Cursor** — merge `cursor-mcp.example.json` into your client's MCP settings. Set `TRAVASO_AGENT_TOKEN` where Cursor runs, then reload the client.
- **Codex** — add `codex-mcp.example.toml` to your MCP configuration. Set the same environment variable where Codex runs, then restart the client.
- **Other clients** — use Streamable HTTP with the server URL and a bearer header from the client's secret settings. The [setup guide](https://elitetravelsales.com/tokens/setup) includes Claude Code and other examples.

Check discovery from a terminal that already has `TRAVASO_AGENT_TOKEN` set.

```sh
printf 'Authorization: Bearer %s\n' "${TRAVASO_AGENT_TOKEN:?Set TRAVASO_AGENT_TOKEN first}" |
  curl --silent --show-error --fail-with-body \
    --request POST https://elitetravelsales.com/api/backend/mcp \
    --header @- \
    --header 'Content-Type: application/json' \
    --header 'Accept: application/json, text/event-stream' \
    --data '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Discovery lists the available tools. Use `SKILL.md` as the booking-agent instructions after the server is connected.

## From an approved room to checkout

1. Present the selected room's total, currency, cancellation terms, and included perks. Verify any separate property fees. A cheaper public nightly reference alone does not establish matching stay savings.
2. Collect the lead traveler's `firstName`, `lastName`, `email`, and `phoneNumber` in a private chat or form. Replace the placeholders in the saved checkout template. For multiple rooms, provide the full named `guests` list with one lead per room and the primary traveler first.
3. Ask the traveler to approve the complete rate. Pass the same quote inputs and selected `recommendationId` to `create_offer_checkout_link`, or use `POST /api/backend/agent/checkout-link` from your server.
4. Review the response against the approved price and terms. Get approval again if they changed, then share the returned hosted `checkoutUrl`. The traveler enters their card details there.
5. Save `offerId` and follow `get_offer_status`. Travaso emails a private confirmation link after the hotel confirms. Keep the link and traveler details out of public logs.

This prompt can be pasted into a connected agent's chat after checkout.

```text
Use get_offer_status for the offerId from my existing checkout.
Report whether payment is pending or the hotel has confirmed the reservation.
If the result is unclear, check the same offer before creating another checkout.
Tell me when Travaso reports supplier confirmation and sends the private email.
```

## Free access and earnings

A free key can request quotes, create card checkout links, and check booking status. Booking does not require a subscription. The free booking key can earn 3% of positive booking gross margin on eligible completed stays. That share is based on booking margin, and commission becomes payable after the eligible stay is completed. Monthly and annual plans offer a higher share. [Current plans and terms](https://elitetravelsales.com/tokens?utm_source=github&utm_medium=referral&utm_campaign=github-2026-11).

## Beta and coverage

Live rate search is available. Supplier-confirmed end-to-end beta validation is still in progress, including the approved supplier sandbox, hosted payment and private confirmation email. The quote example is intended for evaluating returned rates. Follow the [integration guide](https://elitetravelsales.com/hotel-booking-mcp) and the approved staging test path for booking validation.

Returned options cover the supplier inventory available for the requested trip. Rates, availability, taxes, property charges and benefits depend on each stay. Review exact terms before payment. A resort credit, room upgrade or late checkout applies only when explicitly included in the selected rate.

The server applies per-partner usage allowances. If it responds with HTTP 429, wait for `Retry-After` before retrying. A changed or expired rate needs a fresh quote and renewed traveler approval.
