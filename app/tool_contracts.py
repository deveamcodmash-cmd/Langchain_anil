"""Typed contracts for the upcoming Filantrophy tools.

These models define the interface only. No execution endpoints are mounted
until the corresponding trusted Filantrophy APIs and permission checks exist.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CampaignSearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(default='', max_length=160)
    category: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=100)
    currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    page: int = Field(default=1, ge=1, le=100000)
    per_page: int = Field(default=12, ge=1, le=30)


class PlanAllocation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    campaign_id: int = Field(gt=0)
    amount_minor: int = Field(ge=1)


class PlanUpdateArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plan_id: int = Field(gt=0)
    expected_version: int = Field(ge=1)
    action_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{16,96}$')
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    amount_minor: int = Field(gt=0)
    allocations: list[PlanAllocation] = Field(min_length=1, max_length=10)

    @model_validator(mode='after')
    def amounts_balance(self):
        ids=[item.campaign_id for item in self.allocations]
        if len(set(ids))!=len(ids):
            raise ValueError('Duplicate campaign allocation')
        if sum(item.amount_minor for item in self.allocations)!=self.amount_minor:
            raise ValueError('Allocations must equal giving-plan budget')
        return self


class ProposedAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    capability_key: str = Field(pattern=r'^[a-z_.]+$', max_length=90)
    action_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{16,96}$')
    status: Literal['proposal', 'approved', 'executed', 'rejected'] = 'proposal'
    requires_confirmation: bool = True
    # Only trusted Joomla-generated record tokens, not arbitrary user IDs.
    resource_token: str | None = Field(default=None, max_length=160)


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['success','rejected','conflict','pending','unavailable']
    action_id: str
    authoritative_version: int | None = Field(default=None, ge=1)
    message: str = Field(max_length=300)


class VolunteerOpportunitySearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    location: str | None = Field(default=None, max_length=140)
    cause: str | None = Field(default=None, max_length=80)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=30)


class EventSearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    location: str | None = Field(default=None, max_length=140)
    date_from: str | None = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    date_to: str | None = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=30)


class ServiceSearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(default='', max_length=160)
    location: str | None = Field(default=None, max_length=140)
    category_id: int | None = Field(default=None, gt=0)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=9, ge=1, le=30)
