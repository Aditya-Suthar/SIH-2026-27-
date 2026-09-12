"""Deterministic demo decision-support rules. No provider calls or diagnosis."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from statistics import median


def utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def valid(row):
    return (row.status == 'completed' and type(row.distress_score) is int
            and 0 <= row.distress_score <= 100 and row.risk_level in ('low','medium','high','critical'))


def trend(rows, now=None):
    now = utc(now or datetime.now(timezone.utc))
    days = defaultdict(list)
    for row in rows:
        if valid(row) and now - timedelta(days=14) <= utc(row.created_at) <= now:
            days[utc(row.created_at).date()].append(row.distress_score)
    points = [(day, median(scores)) for day,scores in sorted(days.items())][-7:]
    result = {'state':'insufficient_data','days':len(points),'slope_per_day':None,'change':None,
              'explanation':'At least three distinct days of valid analyses within 14 days are needed.'}
    if len(points) < 3:
        return result
    xs = [(day-points[0][0]).days for day,_ in points]
    ys = [value for _,value in points]
    xm, ym = sum(xs)/len(xs), sum(ys)/len(ys)
    slope = sum((x-xm)*(y-ym) for x,y in zip(xs,ys)) / sum((x-xm)**2 for x in xs)
    change = ys[-1]-ys[0]
    if change >= 20 and slope >= 5 and xs[-1] <= 7:
        state = 'rapidly_worsening'
    elif change >= 5 and slope >= 1:
        state = 'worsening'
    elif change <= -5 and slope <= -1:
        state = 'improving'
    else:
        state = 'stable'
    return {'state':state,'days':len(points),'slope_per_day':round(slope,2),'change':round(change,1),
            'explanation':f'{len(points)} daily medians over {xs[-1]} days; change {change:+.1f} points; slope {slope:+.2f} points/day.'}


def prioritize(rows, now=None, current=None):
    now = utc(now or datetime.now(timezone.utc))
    good = sorted((r for r in rows if valid(r) and utc(r.created_at) <= now), key=lambda r:(utc(r.created_at),r.id))
    movement = trend(good, now)
    if not good and not current:
        return {'category':'UNASSESSED','score':None,'reasons':['No successful AI analysis yet.'],
                'alerts':[],'trend':movement,'latest':None,'stale':False,'recent_high_days':0}
    latest = good[-1] if good else None
    state_score = current.get('score') if current else latest.distress_score
    state_risk = current.get('risk') if current else latest.risk_level
    state_time = current.get('observed_at') if current else utc(latest.created_at)
    stale = bool(state_time and now - state_time > timedelta(days=7))
    high_days = len({utc(r.created_at).date() for r in good
                     if r.risk_level in ('high','critical') and now - timedelta(days=7) <= utc(r.created_at)})
    points = (state_score or 0) * .5
    reasons = ([f'Latest authoritative distress indicator: {state_score}/100 (+{points:g}).']
               if state_score is not None else ['Current authoritative state has no numeric legacy score.'])
    risk_points = {'low':0,'medium':8,'high':18,'critical':30}[state_risk]
    points += risk_points
    reasons.append(f'{state_risk.title()} risk indicator (+{risk_points}).')
    alerts = []
    if state_risk in ('high','critical'):
        alerts.append('High distress detected — review recommended')
    attention = state_risk in ('high','critical') if current else latest.requires_attention
    if attention:
        points += 12; reasons.append('Requires attention (+12).'); alerts.append('Requires attention')
    bonus = {'worsening':10,'rapidly_worsening':25}.get(movement['state'],0)
    if bonus:
        points += bonus; reasons.append(f"{movement['state'].replace('_',' ').title()} trend (+{bonus}).")
        alerts.append('Rapid deterioration detected' if bonus==25 else 'Rising distress indicators')
    if high_days >= 2:
        points += 8; reasons.append(f'High/critical indicators on {high_days} days in the last 7 days (+8).')
        alerts.append('Repeated high distress indicators')
    score = min(100, round(points,1))
    category = 'URGENT' if score >= 80 else 'HIGH' if score >= 55 else 'MEDIUM' if score >= 30 else 'NORMAL'
    floors = {'critical':('URGENT',80),'high':('HIGH',55),'medium':('MEDIUM',30)}
    if state_risk in floors:
        floor_category, _ = floors[state_risk]
        rank = {'NORMAL':0,'MEDIUM':1,'HIGH':2,'URGENT':3}
        if rank[category] < rank[floor_category]:
            category = floor_category
            reasons.append(f'{state_risk.title()} current risk applies a {floor_category} priority floor.')
    if stale:
        reasons.append('Last successful analysis is over 7 days old; current condition is unknown.')
    return {'category':category,'score':score,'reasons':reasons,'alerts':alerts,'trend':movement,
            'latest':latest,'stale':stale,'recent_high_days':high_days}
