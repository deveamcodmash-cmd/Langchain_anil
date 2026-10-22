"""Optional real-model evaluation; requires existing OPENAI_API_KEY in environment.

Runs READ-ONLY chat scenarios and writes aggregate scores. The model's factual
correctness and conversational quality still require human review. No payment,
booking, profile change, or database operation is performed by this script.

Usage:
  python tools/evaluate_live_intelligence.py --limit 10
  python tools/evaluate_live_intelligence.py --limit 60 --out result.json
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.graph import run_workflow
from app.schemas import ChatRequest
from app.conversation_voice import tone_flags


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cases',type=Path,default=Path(__file__).resolve().parents[1]/'evaluation/intelligence_cases.jsonl')
    parser.add_argument('--limit',type=int,default=10,help='Cap paid model calls (1-60 scenarios)')
    parser.add_argument('--out',type=Path,default=None)
    args=parser.parse_args()
    if not os.getenv('OPENAI_API_KEY'):
        parser.error('Set OPENAI_API_KEY on your trusted Python host before running live evaluation')
    count=max(1,min(60,args.limit))
    scenarios=[json.loads(line) for line in args.cases.read_text().splitlines() if line.strip()][:count]
    # Public demo data; replace with sanitized real public catalogue snapshots for
    # a meaningful deployment evaluation. No user records are included.
    catalogue=[
        {'id':501,'title':'Flood Recovery Aid','category':'Relief','summary':'Support homes after flooding','currency':'USD','tags':['Disaster Relief']},
        {'id':502,'title':'School Supply Program','category':'Education','summary':'Classroom materials for children','currency':'USD'},
        {'id':503,'title':'Community Health Program','category':'Healthcare','summary':'Care for community patients','currency':'USD'},
    ]
    results=[]
    for item in scenarios:
        try:
            result=run_workflow(ChatRequest(message=item['message'], history=item.get('history',[]),campaigns=catalogue))
            detected='Discovery' if 'Discovery' in result.agents_run else 'Knowledge' if 'Knowledge' in result.agents_run else '+'.join(result.agents_run)
            passed=detected==item['expected_agent']
            # This metric proves only routing and nonempty output, not truth or empathy.
            results.append({'id':item['id'],'expected':item['expected_agent'], 'actual':detected,
                            'route_pass':passed,'nonempty':bool(result.reply.strip()),
                            'response_chars':len(result.reply),'tone_signals':tone_flags(result.reply),
                            'reply_for_manual_review':result.reply[:750]})
        except Exception as exc:
            results.append({'id':item['id'],'expected':item['expected_agent'],'route_pass':False,
                            'error_type':type(exc).__name__})
    passed=sum(r['route_pass'] for r in results)
    flagged=sum(bool(r.get('tone_signals')) for r in results)
    report={'tested':len(results),'routing_passes':passed,'routing_pass_rate':round(passed/len(results),3) if results else 0,
            'responses_with_tone_flags':flagged,
            'notice':'Routing and heuristic tone signals only. Human review is required for factual accuracy, sensitivity, grounded suggestions and actual user experience.',
            'results':results}
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
    if args.out:
        args.out.write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
