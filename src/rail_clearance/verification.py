"""既存と同じ断面分割・一定半径評価と、全平面輪郭の分離軸試験。"""
import itertools
import json
import math
from .configuration import validate
from .paths import DATA_DIR
from .geometry import dimensions, formation, polygons, separation, coupled, reference, rect, tangent_gap

PROFILES = json.loads((DATA_DIR/'profiles.json').read_text(encoding='utf-8'))

def half_width(profile,z):
    values=[]
    for (y0,z0),(y1,z1) in zip(profile,profile[1:]):
        if z0-1e-9 <= z <= z1+1e-9:
            values.extend((y0,y1) if z0==z1 else [y0+(y1-y0)*(z-z0)/(z1-z0)])
    if not values:
        raise ValueError(f'断面の高さ範囲外: {z}')
    return max(values)

def building_profile(radius):
    t=100/radius if radius else 0
    return [(a[0]+t*(b[0]-a[0]),a[1]) for a,b in zip(PROFILES['straight'],PROFILES['curve'])]

def building_margin(profile,lo,hi,spacing,radius):
    """支持点中点基準。既存同様、非対称車体は左右最大張出しの包絡で評価。"""
    building=building_profile(radius)
    levels=sorted(set(z for _,z in profile)|{z for _,z in building if profile[0][1]<=z<=profile[-1][1]})
    result=(math.inf,0)
    distance=math.sqrt(radius**2-spacing**2/4) if radius else 0
    extent=max(abs(lo),abs(hi))
    for a,b in zip(levels,levels[1:]):
        for j in range(21):
            z=a+(b-a)*j/20
            w=half_width(profile,z)
            if radius:
                inner=w+spacing**2/4/(radius+distance)
                delta=w-spacing**2/4/(radius+distance)
                outer=(2*radius*delta+delta**2+extent**2)/(math.hypot(distance+w,extent)+radius)
            else:
                inner=outer=w
            margin=half_width(building,z)-max(inner,outer)
            result=min(result,(margin,z))
    return result

def link_margin(pivots,radius,sign):
    """接続リンク全体の幅360mm・高さ750～1050mmを建築限界と照合。"""
    a,b=pivots
    poly=rect((*a,math.atan2(b[1]-a[1],b[0]-a[0])),0,math.dist(a,b),.18)
    if radius:
        q=[(x,y-sign*radius) for x,y in poly]
        nearest=math.inf
        for a,b in zip(q,q[1:]+q[:1]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            denom=dx*dx+dy*dy
            t=max(0,min(1,-(a[0]*dx+a[1]*dy)/denom)) if denom else 0
            nearest=min(nearest,math.hypot(a[0]+dx*t,a[1]+dy*t))
        occupied=max(radius-nearest,max(math.hypot(*v) for v in q)-radius)
    else:occupied=max(abs(y) for x,y in poly)
    bp=building_profile(radius)
    zs=[.75,1.05]+[z for _,z in bp if .75<=z<=1.05]
    # At horizontal ledges compare the one-sided limits as well as the breakpoint.
    zs+= [z-1e-7 for z in zs if z>.75]+[z+1e-7 for z in zs if z<1.05]
    return min(half_width(bp,z)-occupied for z in zs)

def pair_rows(d,arrangement,kind):
    ps=polygons(d,arrangement,kind)
    n=len(d['cars'])
    rows=[]
    for i,j in itertools.combinations(range(len(ps)),2):
        rows.append(dict(pair=[i,j],category='car_car' if j<n else 'car_equipment' if i<n else 'equipment_equipment',
                         margin_m=separation(ps[i],ps[j])))
    return rows

def run(config,progress=lambda s:None):
    config=validate(config)
    d=dimensions(config)
    radii=sorted(set([0,config['radius_m']]+config['test_radii_m']))
    report=dict(config=config,method='一定半径・左右曲線・カント0・動揺0。分離余裕は平面SATの下限で3D最短距離ではない。',
                building=[],pairs=[],coupled=[],adjacent_tangent_gaps=[],errors=[])
    for r in radii:
        progress(f'断面・接触試験 R={r or "直線"}')
        for i,car in enumerate(d['cars']):
            offset=(car['a']+car['b'])/2
            for kind in ('body','gauge','pantograph'):
                profile=PROFILES[kind] if kind!='pantograph' else [(.65,4.29),(.65,4.515)]
                length=car['length'] if kind!='pantograph' else 2
                m,z=building_margin(profile,-length/2-offset,length/2-offset,car['spacing'],r)
                report['building'].append(dict(car=i,kind=kind,radius=r,margin_m=m,z=z))
        for i,e in enumerate(d['equipment']):
            m,z=building_margin(PROFILES['equipment'],-e['left'],e['right'],0,r)
            report['building'].append(dict(car=i,kind='equipment',radius=r,margin_m=m,z=z))
        if config['normal_ends']:
            for side,index in ((0,0),(1,-1)):
                car=d['cars'][index];offset=(car['a']+car['b'])/2
                start=(-1 if side==0 else 1)*car['length']/2
                end=start+(-1 if side==0 else 1)*d['projections'][side]
                m,z=building_margin([(.18,.75),(.18,1.05)],min(start,end)-offset,max(start,end)-offset,car['spacing'],r)
                report['building'].append(dict(car=index,kind='outer_coupler',radius=r,margin_m=m,z=z))
        for sign in ((1,) if r==0 else (-1,1)):
            arr=formation(d,r,sign)
            for kind in ('body','gauge'):
                rows=pair_rows(d,arr,kind)
                report['pairs'].append(dict(radius=r,direction=sign,kind=kind,minimum_m=min(x['margin_m'] for x in rows),pairs=rows))
                ps=polygons(d,arr,kind)
                for i,pose in enumerate(arr['equipment_poses']):
                    report['adjacent_tangent_gaps'].append(dict(radius=r,direction=sign,kind=kind,pair=[i,i+1],
                        gap_m=tangent_gap(ps[i],ps[i+1],pose[2])))
    if config['normal_ends']:
        lo,hi,step=config['reference_spacing_m']
        spacings=[lo+i*step for i in range(int(round((hi-lo)/step))+1) if lo+i*step<=hi+1e-9]
        for r in radii:
            for sign in ((1,) if not r else (-1,1)):
                for other_name in ('same','20m'):
                    worst={kind:(math.inf,None,None) for kind in ('body','gauge')}
                    for spacing in ([None] if other_name=='same' else spacings):
                        other=d if spacing is None else reference(spacing)
                        if spacing and spacing>=2*r and r:
                            report['errors'].append(f'R{r}: 20m級の台車間が直径以上です。'); continue
                        try:
                            first,second,pivots=coupled(d,other,r,sign)
                        except ValueError as exc:
                            report['errors'].append(f'R{r}/{other_name}/{spacing}: {exc}');continue
                        report['building'].append(dict(car=other_name,kind='joining_coupler',radius=r,direction=sign,
                                                       spacing_m=spacing,margin_m=link_margin(pivots,r,sign)))
                        for kind in worst:
                            p,q=polygons(d,first,kind),polygons(other,second,kind)
                            value,i,j=min((separation(a,b),i,j) for i,a in enumerate(p) for j,b in enumerate(q))
                            if value<worst[kind][0]: worst[kind]=(value,spacing,[i,j])
                    for kind,(value,spacing,pair) in worst.items():
                        report['coupled'].append(dict(radius=r,direction=sign,other=other_name,kind=kind,
                            margin_m=value if math.isfinite(value) else None,spacing_m=spacing,pair=pair))
            # As in the prior 41m test: include all reference bogie spacings in building checks.
            for kind in ('body','gauge','pantograph'):
                length=20 if kind=='body' else 20.5 if kind=='gauge' else 2
                profile=PROFILES[kind] if kind!='pantograph' else [(.65,4.29),(.65,4.515)]
                candidates=[(*building_margin(profile,-length/2,length/2,b,r),b) for b in spacings if not r or b<2*r]
                if candidates:
                    m,z,b=min(candidates)
                    report['building'].append(dict(car='20m',kind=kind,radius=r,margin_m=m,z=z,spacing_m=b))
    report['building_pass']=all(x['margin_m']>=-1e-7 for x in report['building'])
    report['body_pass']=not report['errors'] and all(x['minimum_m']>=-1e-7 for x in report['pairs'] if x['kind']=='body') and all(
        x['margin_m'] is not None and x['margin_m']>=-1e-7 for x in report['coupled'] if x['kind']=='body')
    report['gauge_pass']=not report['errors'] and all(x['minimum_m']>=-1e-7 for x in report['pairs'] if x['kind']=='gauge') and all(
        x['margin_m'] is not None and x['margin_m']>=-1e-7 for x in report['coupled'] if x['kind']=='gauge')
    return report
