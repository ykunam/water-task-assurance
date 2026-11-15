"""Decision-relevant calibration with explicit support and invalid-outcome handling.

The generic conformal set-inclusion principle is established prior work. This
module implements and audits its task-set instantiation for this water study.
"""
import math
from analyze import severity


def forecast_summary(forecasts):
    valid = bool(forecasts) and all('error' not in x and x['assessable'] and
                                  x['realized'] == 1 for x in forecasts)
    predicted = max(map(severity, forecasts), default=math.inf)
    return valid and predicted < 1, predicted


def actual_severity(actual):
    # Invalid hydraulics and failed actuation cannot be silently dropped.
    if 'error' in actual or not actual['assessable'] or actual['realized'] != 1:
        return math.inf
    return severity(actual)


def task_score(candidates):
    eligible = [(r, forecast_summary(r['forecasts'])[1]) for r in candidates
                if forecast_summary(r['forecasts'])[0]]
    return dict(eligible=len(eligible),
                score=max([0.] + [max(0., actual_severity(r['actual'])-p)
                                 for r, p in eligible]))


def quantile(scores, alpha=.1):
    rank = math.ceil((len(scores)+1)*(1-alpha))
    return (math.inf if rank > len(scores) else sorted(scores)[rank-1]), rank


def calibrate(tasks, alpha=.1, opportunity_only=False):
    scored = [dict(task_id=t['task_id'], **task_score(t['candidates'])) for t in tasks]
    selected = [r['score'] for r in scored if r['eligible'] or not opportunity_only]
    margin, rank = quantile(selected, alpha)
    return dict(alpha=alpha, opportunity_only=opportunity_only, margin=margin,
                tasks=len(scored), score_count=len(selected), order_rank=rank,
                opportunity_tasks=sum(r['eligible']>0 for r in scored),
                eligible_candidates=sum(r['eligible'] for r in scored), scores=scored)


def allow(forecasts, margin):
    eligible, predicted = forecast_summary(forecasts)
    return bool(eligible and math.isfinite(margin) and predicted+margin < 1)


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):return 'infinity'
    if isinstance(value, dict):return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value, list):return [json_safe(v) for v in value]
    return value


def from_frame(frame):
    return [dict(task_id=tid,candidates=[dict(forecasts=r.forecasts,actual=r.actual)
                 for r in group.itertuples()]) for tid,group in frame.groupby('task_id',sort=True)]
