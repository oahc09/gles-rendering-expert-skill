"""Finite explicit attachment event model. Logical transfers, never DRAM."""
from decimal import Decimal
import math


def bounded_integer(value, low, high, name):
    """Accept JSON mathematical integers, not bool, a fraction, or nonfinite input."""
    if type(value) is Decimal:
        valid = value.is_finite() and low <= value <= high and value == value.to_integral_value()
    elif type(value) is float:
        valid = math.isfinite(value) and value.is_integer() and low <= value <= high
    else:
        valid = type(value) is int and low <= value <= high
    if not valid:
        raise ValueError('invalid ' + name)
    return int(value)


FORMATS={'RGBA8':4,'RGB8':3,'RG8':2,'R8':1,'RGBA16F':8,'RG16F':4,'R16F':2,'DEPTH24_STENCIL8':4,'DEPTH16':2,'RGBA32F':16}
def lifecycle(data):
    attachments=data.get('attachments')
    if not isinstance(attachments,list) or not attachments: raise ValueError('attachments required')
    state={}
    for a in attachments:
        name=a.get('id')
        if not isinstance(name,str) or not name or name in state: raise ValueError('unique attachment id required')
        a = dict(a)
        for k in ('width', 'height', 'samples'):
            a[k] = bounded_integer(a.get(k), 1, 65536, k)
        if a['samples'] not in (1,2,4,8,16):raise ValueError('invalid samples')
        if type(a.get('initially_defined',False)) is not bool:raise ValueError('initially_defined boolean')
        state[name]={'spec':a,'defined':a.get('initially_defined',False),'stored':a.get('initially_defined',False),'upper':0,'events':[]}
    condition=data.get('driver_condition',{'fbo_switch':'unknown'})
    if not isinstance(condition,dict) or condition.get('fbo_switch') not in ('unknown','preserves_tile','flushes_tile'):raise ValueError('driver FBO condition required')
    if condition['fbo_switch']!='unknown':
        for k in ('device','gpu','driver','backend','source'):
            if not isinstance(condition.get(k),str) or not condition[k].strip():raise ValueError('scoped condition missing '+k)
    events=data.get('lifecycle')
    if not isinstance(events,list) or not events:raise ValueError('lifecycle events required')
    active=None;bound=[];seen=set();switches=0
    def transfer(name,multiplier,reason,index):
        s=state[name];a=s['spec'];bpp=FORMATS.get(a.get('format'))
        value=None if bpp is None else a['width']*a['height']*bpp*multiplier
        s['upper']=None if value is None or s['upper'] is None else s['upper']+value
        s['events'].append({'event_index':index,'reason':reason,'logical_upper_bytes':value})
    for i,e in enumerate(events):
        if not isinstance(e,dict):raise ValueError('event object required')
        op=e.get('op')
        if op=='begin':
            if active is not None:raise ValueError('nested pass')
            if not isinstance(e.get('fbo'),str) or not e['fbo']:raise ValueError('FBO name required')
            loads=e.get('loads')
            if not isinstance(loads,dict) or not loads or any(n not in state for n in loads):raise ValueError('known attachments required')
            active=e['fbo'];bound=list(loads);seen.update(bound)
            for n,action in loads.items():
                s=state[n]
                if action=='load':
                    if not s['stored']:raise ValueError('load of discarded/uninitialized data')
                    transfer(n,s['spec']['samples'],'pass_load',i);s['defined']=True
                elif action=='clear':s['defined']=True;s['stored']=False
                elif action=='discard':s['defined']=False;s['stored']=False
                else:raise ValueError('invalid load operation')
        elif op=='draw':
            if active is None:raise ValueError('draw outside pass')
            if e.get('coverage') not in ('full_overwrite','partial'):raise ValueError('explicit coverage required')
            writes=e.get('writes')
            if not isinstance(writes,list) or not writes or len(writes)!=len(set(writes)) or any(n not in bound for n in writes):raise ValueError('bound writes required')
            for n in writes:
                if e['coverage']=='partial' and not state[n]['defined']:raise ValueError('partial write to undefined attachment')
                state[n]['defined']=True;state[n]['stored']=False
        elif op=='switch':
            if active is None or not isinstance(e.get('fbo'),str) or not e['fbo'] or e['fbo']==active:raise ValueError('distinct FBO switch required')
            # Bounded contract: same attachment set retained; unknown takes worst
            # logical spill/reload, without claiming physical residency.
            switches+=1
            if condition['fbo_switch']!='preserves_tile':
                for n in bound:
                    if state[n]['defined']:transfer(n,2*state[n]['spec']['samples'],'conditional_switch_spill_reload',i)
            active=e['fbo']
        elif op=='resolve':
            n=e.get('attachment')
            if active is None or n not in bound or not state[n]['defined'] or state[n]['spec']['samples']==1:raise ValueError('resolve requires defined multisample bound attachment')
            transfer(n,state[n]['spec']['samples']+1,'resolve_read_write',i)
        elif op=='end':
            if active is None:raise ValueError('end outside pass')
            stores=e.get('stores')
            if not isinstance(stores,dict) or set(stores)!=set(bound):raise ValueError('explicit store for each attachment')
            for n,action in stores.items():
                s=state[n]
                if action=='store':
                    if not s['defined']:raise ValueError('store undefined data')
                    transfer(n,s['spec']['samples'],'pass_store',i);s['stored']=True
                elif action=='discard':s['defined']=False;s['stored']=False
                else:raise ValueError('invalid store')
            active=None;bound=[]
        elif op=='consume':
            n=e.get('attachment')
            if active is not None or n not in state or not state[n]['stored']:raise ValueError('external consume requires stored attachment outside pass')
            transfer(n,state[n]['spec']['samples'],'external_logical_read',i)
        else:raise ValueError('unknown event')
    if active is not None:raise ValueError('unterminated pass')
    if seen!=set(state):raise ValueError('unused attachment')
    unknown=any(s['upper'] is None for s in state.values())
    return {'status':'ESTIMATE_ONLY','model':'explicit-lifecycle-v1','logical_lower_bytes':0,
            'logical_upper_bytes':None if unknown else sum(s['upper'] for s in state.values()),'dram_bytes':None,
            'driver_condition':condition,'condition_authenticity':'NOT_AUTHENTICATED','fbo_switches':switches,
            'attachments':[{'id':n,'logical_lower_bytes':0,'logical_upper_bytes':s['upper'],'events':s['events']} for n,s in state.items()],
            'assumptions':['Explicit full-attachment load/store; draw coverage must be explicitly full-overwrite or partial over defined data.',
            'Switch retains the same attachment set; unknown condition uses conditional spill/reload upper bound.',
            'No compression, cache, tile size, bus amplification or physical residency claim.'],
            'unknowns':['Physical device counters and independent condition evidence required for calibration.']}
