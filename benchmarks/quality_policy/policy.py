"""Deterministic recommendations only: never changes OS, driver or GLES state."""
from dataclasses import dataclass
import math

PRESETS = (
    dict(render_scale=1.0, msaa=4, shadow_size=2048, postprocess=['tone_map','bloom'], particle_budget=2000, lod_bias=0, anisotropy=8),
    dict(render_scale=.85, msaa=2, shadow_size=1024, postprocess=['tone_map'], particle_budget=1200, lod_bias=1, anisotropy=4),
    dict(render_scale=.7, msaa=1, shadow_size=512, postprocess=['tone_map'], particle_budget=600, lod_bias=2, anisotropy=1),
)

def number(x, name, minimum=0):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<minimum:
        raise ValueError(name)
    return float(x)

@dataclass
class QualityPolicy:
    pressure_seconds: float = 3.0
    recovery_seconds: float = 8.0
    minimum_residency: float = 10.0
    cooldown: float = 10.0
    maximum_sample_gap: float = 2.0
    floor: int = 2
    state: str = 'NORMAL'
    level: int = 0
    last_t: float = -1.0
    changed_at: float = -1e30
    pressure_since: float | None = None
    recovery_since: float | None = None

    def __post_init__(self):
        for name in ('pressure_seconds','recovery_seconds','minimum_residency','cooldown','maximum_sample_gap'):
            number(getattr(self,name),name,.001)
        if type(self.floor) is not int or self.floor not in (0,1,2) or self.level not in range(self.floor+1):raise ValueError('quality floor/level')

    def step(self, sample, *, enabled=True, capabilities=None, approved_levels=()):
        t=number(sample['t_s'],'time');budget=number(sample['budget_ms'],'budget',.001)
        p95=number(sample['p95_ms'],'p95');thermal=sample.get('thermal_status')
        if thermal is not None and (type(thermal) is not int or thermal not in range(7)):raise ValueError('thermal_status')
        if t<=self.last_t:raise ValueError('timestamps must increase')
        if self.last_t>=0 and t-self.last_t>self.maximum_sample_gap:
            self.pressure_since=None;self.recovery_since=None
        self.last_t=t
        backend=sample.get('backend','unknown')
        if backend not in ('native_gles','angle','vulkan','software','unknown'):raise ValueError('backend')
        preference=sample.get('preference','balanced')
        if preference not in ('balanced','quality','battery'):raise ValueError('preference')
        trend=sample.get('thermal_trend_c_per_min')
        if trend is not None and (isinstance(trend,bool) or not isinstance(trend,(int,float)) or not math.isfinite(trend)):raise ValueError('thermal trend')
        if any(type(x) is not int or x not in (0,1,2) for x in approved_levels):raise ValueError('visual approval levels')
        high=p95>budget*(1.2 if preference=='quality' else 1.0 if preference=='battery' else 1.1) or (thermal is not None and thermal>=3)
        low=p95<budget*.8 and (thermal is None or thermal<=1) and (trend is None or trend<=.5)
        before=self.level;reason='hold'
        if not enabled:
            self.state='NORMAL';self.pressure_since=None;self.recovery_since=None;reason='disabled: retain current level'
        elif not sample.get('foreground',True):
            self.pressure_since=None;self.recovery_since=None;reason='background: no quality decision'
        elif high:
            self.recovery_since=None
            if self.pressure_since is None:self.pressure_since=t
            self.state='PRESSURED' if self.level==0 else 'DEGRADED'
            if t-self.pressure_since>=self.pressure_seconds and t-self.changed_at>=max(self.minimum_residency,self.cooldown) and self.level<self.floor:
                self.level+=1;self.changed_at=t;self.pressure_since=t;self.state='DEGRADED';reason='sustained pressure'
        elif low:
            self.pressure_since=None
            if self.level:
                self.state='RECOVERING'
                if self.recovery_since is None:self.recovery_since=t
                if t-self.recovery_since>=self.recovery_seconds and t-self.changed_at>=max(self.minimum_residency,self.cooldown):
                    self.level-=1;self.changed_at=t;self.recovery_since=t;reason='stable recovery'
                    if not self.level:self.state='NORMAL'
            else:self.state='NORMAL';self.recovery_since=None
        else:
            self.pressure_since=None;self.recovery_since=None;self.state='DEGRADED' if self.level else 'NORMAL'
        caps=capabilities or {};preset=dict(PRESETS[self.level]);missing=[]
        supported=caps.get('msaa_samples',[])
        if not isinstance(supported,list) or any(type(x)is not int or x<1 for x in supported):raise ValueError('msaa capabilities')
        options=[v for v in supported if v<=preset['msaa']]
        preset['msaa']=max(options) if options else None
        if not options:missing.append('MSAA sample capability')
        max_texture=caps.get('max_texture_size')
        if type(max_texture)is int and max_texture>=512:preset['shadow_size']=min(preset['shadow_size'],max_texture)
        else:preset['shadow_size']=None;missing.append('texture-size capability')
        max_aniso=caps.get('max_anisotropy')
        if isinstance(max_aniso,(int,float)) and not isinstance(max_aniso,bool) and math.isfinite(max_aniso) and max_aniso>=1:
            preset['anisotropy']=min(preset['anisotropy'],max_aniso)
        else:preset['anisotropy']=1 # Legal no-extension fallback, never emits anisotropy GL calls.
        approved=self.level in approved_levels
        return dict(t_s=t,state=self.state,level=self.level,changed=self.level!=before,reason=reason,
                    backend=backend,recommendation=preset,enabled=enabled,capability_missing=missing,
                    visual_acceptance='APPROVED' if approved else 'UNVERIFIED',
                    may_apply=bool(enabled and sample.get('foreground',True) and not missing and approved),
                    operating_system_changes=False,performance_claim='NOT_MEASURED')
