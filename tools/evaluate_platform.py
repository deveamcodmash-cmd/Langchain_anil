"""Offline regression checks; no API keys or LLM calls required.

Run: python tools/evaluate_platform.py
This is NOT an evaluation of the live LLM: use traced end-to-end tests later.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from app.intent_guard import assess, parse_plan_action
from app.future_actions import unsupported_action_reply


def main() -> int:
    cases=ROOT/'evaluation/scenarios.jsonl'
    failures=[]; total=0
    for line in cases.read_text().splitlines():
        if not line.strip(): continue
        item=json.loads(line);total+=1
        question=item['utterance']
        scope=assess(question)
        if scope != item['expected_scope']:
            failures.append(f"{item['id']}: scope {scope!r}, expected {item['expected_scope']!r}")
        if item.get('expected_action'):
            parsed=parse_plan_action(question)
            if not parsed or parsed.get('type')!=item['expected_action']:
                failures.append(f"{item['id']}: action {parsed!r}, expected {item['expected_action']!r}")
        if item.get('expected_unavailable') and not unsupported_action_reply(question):
            failures.append(f"{item['id']}: unavailable operation not blocked")
    print(f"Filantrophy Offline Evaluation: {total} scenarios; {len(failures)} failure(s)")
    if failures:
        for issue in failures: print('  - '+issue)
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
