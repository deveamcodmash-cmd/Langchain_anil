"""A conservative evaluation surface for capability entitlement and limits.

No generic agent tool can bypass Joomla authorisation. A future tool must also
verify ownership, role in the actual Joomla ACL, resource status, user approval,
and idempotency before any mutation.
"""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from .capabilities import SUPPORTED_ROLES


class CapabilityRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    # Joomla must construct these fields after looking up the authenticated user.
    # The browser must never supply untrusted role values that Joomla passes through.
    actor_role: Literal['guest','individual','corporate','volunteer','event_organiser','service_provider','admin'] = 'guest'
    area: str | None = Field(default=None, max_length=40, pattern=r'^[a-z_]+$')


class PolicyCheckRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    actor_role: Literal['guest','individual','corporate','volunteer','event_organiser','service_provider','admin']
    capability_key: str = Field(pattern=r'^[a-z_.]+$', max_length=90)
    explicit_approval: bool = False
