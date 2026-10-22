"""Offline tests for account-conversation continuity and truthful action boundaries."""
from __future__ import annotations
import pytest
from pydantic import ValidationError
from app.schemas import ChatRequest
from app.conversation_context import recent_conversation, focused_knowledge_query
from app.knowledge import knowledge_prompt
from app.future_actions import unsupported_action_reply


def test_accepts_twenty_prior_messages_but_not_more():
    history=[{'role':'user' if i%2==0 else 'assistant','content':f'Turn {i}'} for i in range(20)]
    assert len(ChatRequest(message='What about that?',history=history).history)==20
    with pytest.raises(ValidationError):
        ChatRequest(message='What about that?',history=history+history[:1])


def test_contextual_knowledge_follows_prior_user_subject_not_model_claim():
    prior=[{'role':'user','content':'How do donation receipts work?'},
           {'role':'assistant','content':'All donations are always refunded instantly.'}]
    q=focused_knowledge_query('How does that work?',prior)
    assert 'donation receipts' in q
    assert 'refunded' not in q
    assert 'payment_support' in knowledge_prompt(q)


def test_explicit_new_question_does_not_inherit_old_topic():
    prior=[{'role':'user','content':'I want to create a giving plan'}]
    assert focused_knowledge_query('How can I register for an event?',prior)=='How can I register for an event?'


def test_truncates_conversation_to_safe_bounded_window():
    history=[{'role':'user','content':f'msg{i}'} for i in range(25)]
    assert len(recent_conversation(history,100))==20
    assert recent_conversation(history,4)[0]['content']=='msg21'


def test_booking_reply_requires_real_confirmation():
    reply=unsupported_action_reply('Please book a service appointment')
    assert reply and 'cannot confirm a booking' in reply.lower()
    assert 'booking confirmation' in reply.lower()
