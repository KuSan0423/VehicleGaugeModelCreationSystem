"""共通寸法、一定半径上の剛体配置、接触判定用平面輪郭（単位m）。"""
import math
from configuration import validate

def dimensions(config):
    c = validate(config)
    lengths = [v/1000 for v in c['lengths_mm']]
    gaps = [v/1000 for v in c['gaps_mm']]
    fractions = c['joint_fractions']
    cars, cursor = [], 0.0
    for i, length in enumerate(lengths):
        before = gaps[i-1]*(1-fractions[i-1]) if i else gaps[0]*fractions[0]
        after = gaps[i]*fractions[i] if i < len(gaps) else gaps[-1]*(1-fractions[-1])
        a, b = -length/2-before, length/2+after
        if c['normal_ends'] and i == 0:
            a = -length/2+c['outer_insets_mm'][0]/1000
        if c['normal_ends'] and i == len(lengths)-1:
            b = length/2-c['outer_insets_mm'][1]/1000
        if b <= a or (c['normal_ends'] and ((i == 0 and a > length/2) or
                                          (i == len(lengths)-1 and b < -length/2))):
            raise ValueError(f'{i+1}両目の台車配置が成り立ちません。')
        cars.append(dict(length=length, a=a, b=b, spacing=b-a,
                         start=cursor, center=cursor+length/2, end=cursor+length))
        cursor += length+(gaps[i] if i < len(gaps) else 0)
    radius = min(c['test_radii_m']+([c['radius_m']] if c['radius_m'] else []))
    if max(x['spacing'] for x in cars) >= 2*radius:
        raise ValueError('台車中心間は最小曲線の直径未満である必要があります。')
    reserve = c['equipment_reserve_mm']/1000
    equipment = []
    for i, gap in enumerate(gaps):
        left, right = gap*fractions[i]-reserve, gap*(1-fractions[i])-reserve
        sl, sr = [math.tan(math.asin(cars[j]['spacing']/(2*radius))) for j in (i, i+1)]
        if min(left, right) <= 0 or left+right-1.5*(sl+sr) <= 0:
            raise ValueError(f'連接部{i+1}: 指定間隔では機器限界の幅3mと端面余裕を確保できません。')
        equipment.append(dict(left=left, right=right, sl=sl, sr=sr))
    projections = [v/1000 if c['normal_ends'] else 0 for v in c['coupler_mm']]
    return dict(cars=cars, equipment=equipment, length=cursor+sum(projections),
                body_span=cursor, projections=projections, radius_min=radius)

def point(pose, x, y=0):
    cx, cy, a = pose
    return (cx+math.cos(a)*x-math.sin(a)*y, cy+math.sin(a)*x+math.cos(a)*y)

def formation(d, radius=0, sign=1, phase=0, shift=0):
    cars = d['cars']
    if not radius:
        poses = [(v['center']-d['body_span']/2+shift, 0, 0) for v in cars]
        nodes = [point(poses[0], cars[0]['a'])]+[point(p, v['b']) for p, v in zip(poses, cars)]
        angles = [0]*len(nodes)
    else:
        arcs = [2*math.asin(v['spacing']/(2*radius)) for v in cars]
        angles = [phase-sum(arcs)/2]
        for arc in arcs:
            angles.append(angles[-1]+arc)
        nodes = [(radius*math.sin(t), sign*2*radius*math.sin(t/2)**2) for t in angles]
        poses = []
        for i, car in enumerate(cars):
            a, b = nodes[i:i+2]
            yaw = math.atan2(b[1]-a[1], b[0]-a[0])
            mid = ((a[0]+b[0])/2, (a[1]+b[1])/2, yaw)
            poses.append((*point(mid, -(car['a']+car['b'])/2), yaw))
    eq = [(*nodes[i+1], sign*angles[i+1]) for i in range(len(cars)-1)]
    return dict(poses=poses, equipment_poses=eq, nodes=nodes)

def rect(pose, lo, hi, width):
    return [point(pose,x,y) for x,y in [(lo,-width),(hi,-width),(hi,width),(lo,width)]]

def equipment_outline(e, width=1.5):
    return [(-e['left'],0),(-e['left']+e['sl']*width,-width),
            (e['right']-e['sr']*width,-width),(e['right'],0),
            (e['right']-e['sr']*width,width),(-e['left']+e['sl']*width,width)]

def polygons(d, arrangement, kind='body'):
    width = 1.45 if kind == 'body' else 1.5
    p = [rect(pose,-v.get('gauge_length',v['length'])/2 if kind=='gauge' else -v['length']/2,
              v.get('gauge_length',v['length'])/2 if kind=='gauge' else v['length']/2,width)
         for v,pose in zip(d['cars'],arrangement['poses'])]
    p += [[point(pose,x,y) for x,y in equipment_outline(e)]
          for e,pose in zip(d['equipment'],arrangement['equipment_poses'])]
    return p

def separation(p,q):
    """正値=分離軸上の隙間下限。負値=平面輪郭の重なり（3D最短距離ではない）。"""
    result = -math.inf
    for poly in (p,q):
        for a,b in zip(poly,poly[1:]+poly[:1]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            norm=math.hypot(dx,dy)
            if norm < 1e-12:
                continue
            u=[(-dy*x+dx*y)/norm for x,y in p]
            v=[(-dy*x+dx*y)/norm for x,y in q]
            result=max(result,min(u)-max(v),min(v)-max(u))
    return result

def tangent_gap(p,q,angle):
    """旧15mモデルの評価：共有台車の接線軸へ投影した車体端間の隙間。"""
    axis=(math.cos(angle),math.sin(angle))
    a=[x*axis[0]+y*axis[1] for x,y in p]
    b=[x*axis[0]+y*axis[1] for x,y in q]
    return max(min(b)-max(a),min(a)-max(b))

def reference(spacing=15):
    return dict(cars=[dict(length=20,gauge_length=20.5,a=-spacing/2,b=spacing/2,
                         spacing=spacing,center=10)],equipment=[],body_span=20,
                projections=[.25,.25],length=20.5)

def coupled(d, other, radius=0, sign=1):
    first=formation(d,radius,sign)
    second=formation(other,radius,sign)
    end=point(first['poses'][-1],d['cars'][-1]['length']/2)
    front=point(second['poses'][0],-other['cars'][0]['length']/2)
    distance=d['projections'][1]+other['projections'][0]
    if not radius:
        second=formation(other,shift=end[0]+distance-front[0])
    else:
        # Solve two endpoint orbits around the same track-circle centre.
        q1=math.hypot(end[0],radius-sign*end[1])
        q2=math.hypot(front[0],radius-sign*front[1])
        numerator=distance**2-(q1-q2)**2
        if numerator < -1e-10:
            raise ValueError('連結器長では曲線上の車体端を接続できません。')
        delta=2*math.asin(min(1,math.sqrt(max(0,numerator)/(4*q1*q2))))
        phase=math.atan2(end[0],radius-sign*end[1])+delta-math.atan2(front[0],radius-sign*front[1])
        second=formation(other,radius,sign,phase=phase)
    front=point(second['poses'][0],-other['cars'][0]['length']/2)
    if abs(math.dist(end,front)-distance)>1e-6:
        raise ValueError('連結器の接続距離の計算が不一致です。')
    return first,second,(end,front)
