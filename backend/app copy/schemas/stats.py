"""Contracts for the dashboard analytics endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class IntentCount(BaseModel):
    intent: str
    count: int


class DailyVolume(BaseModel):
    date: str  # ISO date, e.g. "2026-07-09"
    inbound: int
    outbound: int


class DashboardStats(BaseModel):
    total_conversations: int
    open_conversations: int
    needs_human: int
    resolved_conversations: int
    total_messages: int
    total_customers: int
    total_orders: int
    ai_resolution_rate: float  # 0..100, % of convos resolved without escalation
    avg_confidence: float  # 0..100 average AI confidence
    intents: list[IntentCount]
    daily_volume: list[DailyVolume]
    top_faqs: list[dict]
