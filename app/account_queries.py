"""Read-only, permission-scoped capability dispatch from authenticated Joomla facts.

This is a *precision guard* for requests requiring a trusted DB calculation, not a
keyword replacement for the LangGraph supervisor. Unmatched questions go to the
model. No account facts are accepted from browser input; Joomla signs the payload.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from .schemas import ChatRequest, ChatResponse, PlatformResource


def capability(message: str) -> str | None:
    q = message.casefold().strip()
    personal = bool(re.search(r"\b(my|mine|i|i'm|i’ve|i've|me)\b", q))
    personal_giving = bool(re.search(r"\bmy\s+(?:donations?|giving|contributions?)\b|\b(?:have\s+i|i\s+have|i've|i’ve|i'm|i\s+am)\s+(?:donat|giv|contribut)|\bwhich\s+cause\s+(?:i|i'm|i’ve|i've)\b|\bwhere\s+have\s+i\b", q))
    if personal and re.search(r"\b(bookings?|appointments?|reservations?)\b", q) and re.search(
        r"\b(upcoming|future|next|scheduled|booked|remember|have|show|list|check|when|what)\b", q
    ):
        return 'my_bookings'
    if personal_giving and re.search(r"\b(donat(?:e|ed|ion|ions|ing)|giv(?:e|ing|en)|contribut(?:e|ed|ion|ions))\b", q) and re.search(
        r"\b(most|more|highest|top|biggest|largest|which|where|how much)\b", q
    ):
        return 'my_donations'
    if re.search(r"\b(campaigns?|causes?|fundraisers?)\b", q) and re.search(
        r"\b(highest|most|top|biggest|largest|raised|funded)\b", q
    ) and re.search(r"\b(raised|funded|donations?|support|money|amount)\b", q):
        return 'campaign_raised'
    if re.search(r"\b(services?|providers?|listings?)\b", q) and re.search(
        r"\b(latest|newest|recently added|most recent|newly published)\b", q
    ):
        return 'latest_services'
    return None


def _money(value: float | int | str, currency: str) -> str:
    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            raise InvalidOperation
        return f'{currency} {amount:,.2f}'
    except (InvalidOperation, ValueError):
        return f'{currency} —'


def _account_result(req: ChatRequest, kind: str) -> ChatResponse:
    ctx = req.account_context
    if not ctx.signed_in:
        return ChatResponse(reply='Sign in to your Filantrophy account and I can help you review your own bookings and giving activity.',
                            agents_run=['Account Permission'], mode='signin_required')
    if kind == 'my_bookings':
        if not ctx.bookings_available:
            msg = ('Your booking details are best checked in My Bookings for now. '
                   'I can help you find the booking area, but I won’t guess appointment dates or statuses.')
        elif not ctx.upcoming_bookings:
            msg = 'There are no upcoming appointments in the booking records available to your account right now. You can explore services whenever you’re ready.'
        else:
            lines = [f'{b.service_title or "Service appointment"} — {b.booking_date}' +
                     (f' at {b.start_label}' if b.start_label else '') +
                     f' ({b.status_label})' for b in ctx.upcoming_bookings[:5]]
            msg = 'Here are your upcoming bookings: ' + '; '.join(lines) + '.'
        return ChatResponse(reply=msg, agents_run=['Authenticated Bookings'], mode='account_read')
    if not ctx.donations_available:
        return ChatResponse(reply='Your verified donation totals are available in My Giving. I can compare them here once the completed-donation records are connected.',
                            agents_run=['Authenticated Giving'], mode='account_data_unavailable')
    if not ctx.donation_totals:
        return ChatResponse(reply='Your account does not currently show completed donations in the connected records. Your Giving Plan can still be viewed separately.',
                            agents_run=['Authenticated Giving'], mode='account_read')
    ranked = sorted(ctx.donation_totals, key=lambda d:(d.currency, -d.amount, d.campaign_title.casefold()))
    currencies = sorted({d.currency for d in ranked})
    if len(currencies) == 1:
        top = max(ranked, key=lambda d:d.amount)
        msg = f'Your largest recorded total is {_money(top.amount,top.currency)} for {top.campaign_title}. This includes completed donations associated with your signed-in account.'
    else:
        best=[]
        for currency in currencies[:5]:
            top=max((d for d in ranked if d.currency==currency), key=lambda d:d.amount)
            best.append(f'{top.campaign_title}: {_money(top.amount,currency)}')
        msg = 'Your highest completed donations by currency are ' + '; '.join(best) + '. Different currencies are kept separate.'
    return ChatResponse(reply=msg, agents_run=['Authenticated Giving','Aggregation'], mode='account_read')


def _leaderboard(req: ChatRequest) -> ChatResponse:
    visible = [c for c in req.campaigns if c.public_progress and c.raised is not None]
    if not visible:
        return ChatResponse(reply='The campaign records available for this search do not include comparable public fundraising totals. You can still explore the published causes and their individual progress where it is displayed.',
                            agents_run=['Verified Fundraising Ranking'], mode='ranking_unavailable')
    by_currency: dict[str,list] = defaultdict(list)
    for campaign in visible:
        by_currency[campaign.currency].append(campaign)
    if len(by_currency)==1:
        currency, rows = next(iter(by_currency.items()))
        leader = sorted(rows,key=lambda c:(-c.raised,c.id))[0]
        msg = (f'Among the {len(rows)} campaigns with public fundraising totals in the current catalogue, '
               f'{leader.title} has the highest displayed amount raised: {_money(leader.raised,currency)}. '
               'This is a comparison of the available listings, not a live all-platform ranking.')
        ids=[leader.id]
    else:
        leaders = [(cur,sorted(rows,key=lambda c:(-c.raised,c.id))[0]) for cur,rows in sorted(by_currency.items())]
        msg = 'The highest displayed fundraising totals by currency in the available catalogue are: ' + '; '.join(
            f'{c.title} ({_money(c.raised,cur)})' for cur,c in leaders[:5]
        ) + '. Amounts in different currencies are not directly comparable.'
        ids=[c.id for _,c in leaders[:5]]
    return ChatResponse(reply=msg,campaign_ids=ids,agents_run=['Verified Fundraising Ranking'],mode='verified_ranking')


def _recent_services(req: ChatRequest) -> ChatResponse:
    services = [r for r in req.resources if r.kind=='service']
    # No date field? We can offer the visible catalogue but must not invent order.
    dated=[]
    for r in services:
        if not r.published_at:
            continue
        try:
            stamp=datetime.fromisoformat(r.published_at.replace('Z','+00:00'))
            if stamp.tzinfo is None:
                stamp=stamp.replace(tzinfo=timezone.utc)
            dated.append((stamp,r))
        except ValueError:
            continue
    if dated:
        dated.sort(key=lambda p:(-p[0].timestamp(),p[1].id))
        found=[r for _,r in dated[:5]]
        return ChatResponse(reply='Here are the most recently dated published services in the available listings.',
                            resources=found, resource_result_ids=[r.id for _,r in dated],
                            agents_run=['Verified Service Dates'],mode='platform_search')
    if services:
        return ChatResponse(reply='Here are some published services you can explore. Their publication dates are not included in the available records, so I can’t reliably label one as the newest.',
                            resources=services[:5], resource_result_ids=[r.id for r in services],
                            agents_run=['Service Catalogue'],mode='platform_search')
    return ChatResponse(reply='Let’s explore the Services directory to see what is currently published. The available data does not establish a newest service yet.',
                        agents_run=['Service Catalogue'],mode='platform_search')


def answer_capability(req: ChatRequest) -> ChatResponse | None:
    kind=capability(req.message)
    if kind=='my_bookings' or kind=='my_donations':
        return _account_result(req,kind)
    if kind=='campaign_raised':
        return _leaderboard(req)
    if kind=='latest_services':
        return _recent_services(req)
    return None
