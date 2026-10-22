from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator


class Campaign(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(default='Campaign', max_length=80)
    location: str = Field(default='', max_length=160)
    summary: str = Field(default='', max_length=240)
    tags: list[str] = Field(default_factory=list, max_length=8)
    currency: str = Field(default='NGN', pattern=r'^[A-Z]{3}$')
    goal: float | None = Field(default=None, ge=0)
    raised: float | None = Field(default=None, ge=0)
    public_progress: bool = False



class ConversationMessage(BaseModel):
    role: Literal['user','assistant']
    content: str = Field(min_length=1,max_length=650)


class CurrentPlanItem(BaseModel):
    id: int = Field(gt=0)
    amount: int = Field(ge=0, le=1000000000)

class CurrentPlan(BaseModel):
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    budget: int = Field(ge=1,le=1000000000)
    items: list[CurrentPlanItem] = Field(default_factory=list,max_length=10)

class PlatformResource(BaseModel):
    id: int = Field(gt=0)
    title: str = Field(min_length=1,max_length=160)
    kind: Literal['event','volunteering','service']
    location: str = Field(default='',max_length=180)
    summary: str = Field(default='',max_length=260)
    url: str = Field(default='',max_length=500)
    published_at: str = Field(default='', max_length=40)

class UpcomingBooking(BaseModel):
    booking_id: int = Field(gt=0)
    service_title: str = Field(default='', max_length=160)
    booking_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    start_label: str = Field(default='', max_length=30)
    status_label: str = Field(default='Scheduled', max_length=30)


class DonationTotal(BaseModel):
    campaign_id: int = Field(gt=0)
    campaign_title: str = Field(default='Campaign', max_length=160)
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    amount: float = Field(ge=0)


class AccountContext(BaseModel):
    signed_in: bool = False
    bookings_available: bool = False
    donations_available: bool = False
    upcoming_bookings: list[UpcomingBooking] = Field(default_factory=list, max_length=12)
    donation_totals: list[DonationTotal] = Field(default_factory=list, max_length=30)


class BookingContext(BaseModel):
    # UI state only. The service ID must match a trusted published catalogue row.
    active: bool = False
    service_id: int | None = Field(default=None, gt=0)
    stage: Literal['service','details','date','time','contact','review'] = 'service'


class SiteFact(BaseModel):
    # Server-selected, reviewed website fact (never a user-authored instruction).
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-z][a-z0-9_]{2,55}$')
    title: str = Field(min_length=1,max_length=90)
    content: str = Field(min_length=1,max_length=950)


class RankingRow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rank: int = Field(ge=1)
    title: str = Field(min_length=1,max_length=140)
    score: float | None = Field(default=None, ge=0)
    category: str = Field(default='',max_length=60)

class RankingContext(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: str = Field(pattern=r'^(providers|campaigns|individual|corporate|volunteers|followers)$')
    count: int = Field(default=10,ge=1,le=20)
    period: str = Field(default='all_time',pattern=r'^(all_time|month|last_month|year)$')
    # Backwards compatibility: Joomla v0.5.24 sent this internal fail-closed
    # filter marker and v0.5.15 rejected it with HTTP 422. Do not allow any
    # other extra request keys. New Joomla releases omit this transport field.
    unsupported_filter: bool = False

class GivingSummary(BaseModel):
    model_config = ConfigDict(extra='forbid')
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    donations: int = Field(ge=0)
    contributors: int = Field(ge=0)
    amount: float = Field(ge=0)


class RankingEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: str = Field(pattern=r'^(published|not_published)$')
    type: str = Field(pattern=r'^(providers|campaigns|individual|corporate|volunteers|followers|unknown)$')
    period: str = Field(pattern=r'^(all_time|month|last_month|year)$')
    verified: bool = False
    # Trusted Joomla-supplied scope; never inferred from user prompts.
    scope: Literal['public','administrator'] = 'public'
    # Currency-separated gross transaction summary, no donor identity.
    summary: GivingSummary | None = None
    rows: list[RankingRow] = Field(default_factory=list,max_length=20)
    total: int = Field(default=0,ge=0)
    last_updated: str | None = None
    next_offset: int | None = Field(default=None,ge=0)
    message: str = Field(default='',max_length=500)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=600)
    history: list[ConversationMessage] = Field(default_factory=list, max_length=20)
    # Explicitly consented, account-scoped preferences loaded by authenticated Joomla.
    # Untrusted as instructions; never a source of payment, booking or account facts.
    memory: list[str] = Field(default_factory=list, max_length=8)
    campaigns: list[Campaign] = Field(default_factory=list,max_length=30)
    # Server-side Joomla session: exact IDs displayed in the most recent result.
    recent_campaign_ids: list[int] = Field(default_factory=list, max_length=30)
    current_plan: CurrentPlan | None = None
    resources: list[PlatformResource] = Field(default_factory=list,max_length=80)
    account_context: AccountContext = Field(default_factory=AccountContext)
    booking_context: BookingContext | None = None
    client_timezone: str = Field(default='UTC', pattern=r'^[A-Za-z0-9_+./-]{1,64}$')
    site_facts: list[SiteFact] = Field(default_factory=list,max_length=8)
    ranking_data: RankingEvidence | None = None
    ranking_context: RankingContext | None = None

    @field_validator('memory')
    @classmethod
    def limited_memory(cls, values: list[str]) -> list[str]:
        if any(not isinstance(v, str) or not v.strip() or len(v) > 250 for v in values):
            raise ValueError("Invalid memory preference")
        return values

    @field_validator('message')
    @classmethod
    def nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class SuggestedAllocation(BaseModel):
    id: int = Field(gt=0)
    amount: int = Field(gt=0)


class SuggestedPlan(BaseModel):
    currency: str
    budget: int = Field(gt=0)
    items: list[SuggestedAllocation] = Field(min_length=1,max_length=10)


class ChatResponse(BaseModel):
    reply: str = Field(max_length=3000)
    campaign_ids: list[int] = Field(default_factory=list)
    # Ranked, server-verified candidate IDs (not only those in the first page).
    # Joomla owns the cursor; the model never decides which records are already shown.
    catalogue_result_ids: list[int] = Field(default_factory=list, max_length=30)
    plan_proposal: SuggestedPlan | None = None
    action_proposal: dict | None = None
    agents_run: list[str] = Field(default_factory=list)
    resources: list[PlatformResource] = Field(default_factory=list)
    resource_result_ids: list[int] = Field(default_factory=list, max_length=80)
    mode: str = 'langgraph'
