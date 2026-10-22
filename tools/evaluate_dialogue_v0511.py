#!/usr/bin/env python3
"""Privacy-preserving offline routing QA; no LLM/network/database required.

Prints scenario labels and pass/fail only. It deliberately never logs dialogue
content or account information. Model quality needs separate LIVE evaluations.
Run: PYTHONPATH=. python tools/evaluate_dialogue_v0511.py
"""
from __future__ import annotations

from app.dialogue_intelligence import general_only_question, resolve_offer, booking_help, platform_guidance
from app.service_intelligence import is_service_request
from app.schemas import ChatRequest, Campaign, ConversationMessage, PlatformResource, BookingContext

SERVICE=[PlatformResource(id=9,kind='service',title='Yoga & Meditation Session')]
ANIMAL=[Campaign(id=2,title='Animal Shelter Support',category='Animal Welfare')]

CASES=[
  ('movie route', lambda:not is_service_request('provide me sex movies list',SERVICE)),
  ('adult film route', lambda:general_only_question('best sex movie list')),
  ('health education route', lambda:general_only_question('recommend me sex positions')),
  ('animal education route', lambda:not is_service_request('recommend dog breeding techniques',SERVICE)),
  ('booking form guide', lambda:booking_help(ChatRequest(message='guide me booking form',resources=SERVICE,booking_context=BookingContext(active=True,service_id=9,stage='review'))).mode=='booking_guidance'),
  ('campaign wizard', lambda:platform_guidance(ChatRequest(message='how to create a campaign')).mode=='platform_guidance'),
  ('unverified rank', lambda:platform_guidance(ChatRequest(message='top charity')).mode=='ranking_unavailable'),
  ('time tool', lambda:platform_guidance(ChatRequest(message='what is time now',client_timezone='Asia/Kolkata')).mode=='general_knowledge'),
  ('yes executes offer', lambda:resolve_offer(ChatRequest(message='yes',campaigns=ANIMAL,history=[ConversationMessage(role='assistant',content='Would you like me to show animal welfare campaigns?')])).campaign_ids==[2]),
  ('empty offer resolved', lambda:not resolve_offer(ChatRequest(message='yes',history=[ConversationMessage(role='assistant',content='Would you like me to show animal welfare campaigns?')])).campaign_ids),
  ('no invented service', lambda:booking_help(ChatRequest(message='guide my booking form',resources=SERVICE,booking_context=BookingContext(active=True,service_id=999,stage='review'))).mode=='booking_guidance'),
]


def main() -> int:
    passed=0
    for label,check in CASES:
        try: ok=bool(check())
        except Exception: ok=False
        print(f"{'PASS' if ok else 'FAIL'}: {label}")
        passed+=int(ok)
    print(f'Offline routing contracts: {passed}/{len(CASES)} passed. No live-model grading performed.')
    return 0 if passed==len(CASES) else 1

if __name__=='__main__':
    raise SystemExit(main())
