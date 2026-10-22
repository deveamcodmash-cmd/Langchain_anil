"""Auditable Filantrophy AI capability catalogue.

The catalogue is *not* a permission-granting mechanism. Signed requests come from
Filantrophy's server. Any future state-changing tool must re-check the actor,
record, action, plan version, and user approval in the authoritative backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CapabilityStatus = Literal['available', 'limited', 'planned']

SUPPORTED_ROLES = frozenset({
    'guest', 'individual', 'corporate', 'volunteer',
    'event_organiser', 'service_provider', 'admin'
})
ALL_ROLES = tuple(sorted(SUPPORTED_ROLES))
MEMBER_ROLES = tuple(r for r in ALL_ROLES if r != 'guest')


@dataclass(frozen=True, slots=True)
class Capability:
    key: str
    area: str
    title: str
    description: str
    status: CapabilityStatus
    roles: tuple[str, ...]
    approval: Literal['none', 'draft', 'explicit', 'privileged']
    action_type: Literal['read', 'draft', 'transaction', 'admin']
    integration: str


CATALOGUE: tuple[Capability, ...] = (
    Capability('campaign.search', 'campaigns', 'Find Campaigns',
        'Search campaigns from the currently supplied published catalogue; pagination is not yet connected.',
        'limited', ALL_ROLES, 'none', 'read', 'Existing Campaign Catalogue'),
    Capability('campaign.recommend', 'campaigns', 'Recommend Campaigns',
        'Recommend eligible campaigns from current verified catalogue results.',
        'limited', ALL_ROLES, 'none', 'read', 'Existing Campaign Catalogue'),
    Capability('giving.plan_propose', 'giving', 'Prepare A Giving Plan',
        'Propose allocations for user review; never initiate a charge.',
        'available', ALL_ROLES, 'draft', 'draft', 'Python LangGraph And Existing Joomla Module'),
    Capability('giving.plan_edit', 'giving', 'Edit A Draft Giving Plan',
        'Update a browser draft through validated actions; changes remain unsaved until the user saves them.',
        'available', ALL_ROLES, 'draft', 'draft', 'Existing Joomla Module'),
    Capability('giving.single_checkout', 'giving', 'One-Payment Checkout',
        'Review a plan and use the existing embedded checkout; server verifies each payment and allocations.',
        'limited', ALL_ROLES, 'explicit', 'transaction', 'Existing Joomla Payment Module; Sandbox QA Required'),
    Capability('giving.save_plan', 'giving', 'Save Giving Plan',
        'Persist an authenticated user giving plan in the existing module storage.',
        'available', MEMBER_ROLES, 'explicit', 'draft', 'Existing Joomla Module'),
    Capability('giving.history', 'giving', 'Donation History',
        'Access the authenticated user donation history with existing frontend controls.',
        'limited', MEMBER_ROLES, 'none', 'read', 'Existing Joomla Module'),
    Capability('volunteering.search', 'volunteering', 'Find Volunteer Opportunities',
        'Discover and filter live volunteer opportunities with role-appropriate access.',
        'planned', ALL_ROLES, 'none', 'read', 'Volunteer Module API Required'),
    Capability('volunteering.apply', 'volunteering', 'Apply For Volunteering',
        'Prepare and submit an application after user confirmation.',
        'planned', MEMBER_ROLES, 'explicit', 'transaction', 'Volunteer Module API Required'),
    Capability('volunteering.hours', 'volunteering', 'View Verified Volunteer Hours',
        'Retrieve verified participation and attendance information.',
        'planned', MEMBER_ROLES, 'none', 'read', 'QR Attendance API Required'),
    Capability('events.search', 'events', 'Discover Events',
        'Search published events by location and date.',
        'planned', ALL_ROLES, 'none', 'read', 'Event Booking API Required'),
    Capability('events.register', 'events', 'Register For An Event',
        'Prepare an event registration and request final user approval.',
        'planned', MEMBER_ROLES, 'explicit', 'transaction', 'Event Booking API Required'),
    Capability('events.organise', 'events', 'Organise Events',
        'Help authorised organisers manage event details and attendance.',
        'planned', ('event_organiser','admin'), 'privileged', 'admin', 'Event Organiser API Required'),
    Capability('services.search', 'services', 'Find Services',
        'Explore public service providers, categories and listings.',
        'planned', ALL_ROLES, 'none', 'read', 'Service Provider API Required'),
    Capability('services.book', 'services', 'Book A Service',
        'Prepare an appointment booking using verified availability and user approval.',
        'planned', MEMBER_ROLES, 'explicit', 'transaction', 'Service Booking API Required'),
    Capability('services.manage', 'services', 'Manage Provider Services',
        'Help authorised service providers manage their listings and bookings.',
        'planned', ('service_provider','admin'), 'privileged', 'admin', 'Provider Operations API Required'),
    Capability('corporate.impact', 'corporate', 'Corporate Impact Summary',
        'Retrieve organisation-authorised donation, participation and impact reporting.',
        'planned', ('corporate','admin'), 'none', 'read', 'Corporate Dashboard API Required'),
    Capability('profiles.personal', 'profiles', 'Personal Giving Profile',
        'Answer account-specific questions with authenticated, consented profile data.',
        'planned', MEMBER_ROLES, 'none', 'read', 'Profile API Required'),
    Capability('rankings.explain', 'rankings', 'Explain Platform Rankings',
        'Explain published ranking methodology using authoritative metrics and definitions.',
        'planned', ALL_ROLES, 'none', 'read', 'Ranking System API And Policy Required'),
    Capability('admin.operations', 'administration', 'Administrative Operations',
        'Review operational signals and prepare actions for authorised administrators.',
        'planned', ('admin',), 'privileged', 'admin', 'Admin Audit And Moderation APIs Required'),
)

_KEYS = {cap.key for cap in CATALOGUE}
assert len(_KEYS) == len(CATALOGUE), 'Duplicate capability key'
assert all(set(cap.roles).issubset(SUPPORTED_ROLES) for cap in CATALOGUE), 'Invalid role in catalogue'


def list_capabilities(role: str = 'guest', area: str | None = None) -> list[dict]:
    """Informational readiness map; not authorization to execute a tool."""
    if role not in SUPPORTED_ROLES:
        raise ValueError('Unknown role')
    return [
        {
            'key': c.key,
            'area': c.area,
            'title': c.title,
            'description': c.description,
            'status': c.status,
            'eligible_role': role in c.roles,
            'approval': c.approval,
            'action_type': c.action_type,
            'integration': c.integration,
            'executable_by_python': False,  # No generic mutation tool is exposed.
        }
        for c in CATALOGUE if not area or c.area == area
    ]


def policy_decision(capability_key: str, role: str, *, consent: bool = False) -> dict:
    """Conservative preflight, never sufficient for a real sensitive operation."""
    c = next((c for c in CATALOGUE if c.key == capability_key), None)
    if c is None or role not in SUPPORTED_ROLES:
        return {'allowed': False, 'reason': 'unknown_capability_or_role'}
    if role not in c.roles:
        return {'allowed': False, 'reason': 'role_not_eligible'}
    if c.status == 'planned':
        return {'allowed': False, 'reason': 'integration_not_available'}
    if c.approval in {'explicit', 'privileged'} and not consent:
        return {'allowed': False, 'reason': 'approval_required'}
    if c.action_type in {'transaction', 'admin'}:
        return {'allowed': False, 'reason': 'authoritative_backend_required'}
    return {'allowed': True, 'reason': 'read_or_draft_only', 'backend_authorization_required': True}
