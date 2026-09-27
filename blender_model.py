"""Blender専用：部品作成、配置、メッシュ検証、保存。"""
import hashlib
import json
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from configuration import ROOT,validate
from geometry import dimensions, formation, coupled, reference, point
from verification import PROFILES

COLORS={'body':(.10,.42,.80,1),'gauge':(.96,.51,.08,1),'equipment':(.7,.22,.82,1)}

def extrusion(profile,lo,hi):
    ring=profile+[(-y,z) for y,z in reversed(profile)]
    n=len(ring)
    vertices=[(x,y,z) for x in (lo,hi) for y,z in ring]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return vertices,faces

def mesh(name,parts,color):
    vertices,faces=[],[]
    for profile,lo,hi in parts:
        v,f=extrusion(profile,lo,hi); offset=len(vertices)
        vertices.extend(v);faces.extend(tuple(i+offset for i in face) for face in f)
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new(name+'_色');mat.diffuse_color=color;obj.data.materials.append(mat);obj.color=color
    obj['原点']='車体中央または共有台車中心のレール上面。X長手・Y左右・Z高さ、単位m。'
    return obj

def vehicle(name,car,kind):
    length=car.get('gauge_length',car['length']) if kind=='gauge' else car['length']
    parts=[(PROFILES[kind],-length/2,length/2)]
    if kind=='body':parts.append(([(.65,4.29),(.65,4.515)],-1,1))
    obj=mesh(name,parts,COLORS[kind])
    obj['台車中心_X_m']=[car['a'],car['b']]
    if kind=='gauge':obj.display_type='WIRE';obj.show_in_front=True
    return obj

def equipment(name,e):
    obj=mesh(name,[(PROFILES['equipment'],-e['left'],e['right'])],COLORS['equipment'])
    bm=bmesh.new();bm.from_mesh(obj.data)
    for sign,extent,slope in [(-1,e['left'],e['sl']),(1,e['right'],e['sr'])]:
        for sy in (-1,1):
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,
                                  plane_co=(sign*extent,0,0),plane_no=(sign,sy*slope,0),clear_outer=True)
            bmesh.ops.holes_fill(bm,edges=[ed for ed in bm.edges if ed.is_boundary],sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    return obj

def transform(obj,pose):
    obj.matrix_world=Matrix.Translation((pose[0],pose[1],0)) @ Matrix.Rotation(pose[2],4,'Z')

def audit(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    result=dict(closed=all(e.is_manifold for e in bm.edges),min_area=min(f.calc_area() for f in bm.faces),
                volume=bm.calc_volume(signed=True))
    bm.free()
    if not result['closed'] or result['min_area']<=1e-10 or result['volume']<=0:
        raise ValueError(f'不正なメッシュ: {obj.name}: {result}')
    return result

def bvh(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                                [list(f.vertices) for f in obj.data.polygons])

def overlaps(objects):
    trees=[bvh(o) for o in objects]
    return [dict(pair=[objects[i].name,objects[j].name],surface_pairs=len(trees[i].overlap(trees[j])))
            for i in range(len(objects)) for j in range(i+1,len(objects))]

def signature(obj):
    return dict(vertices=[list(v.co) for v in obj.data.vertices],faces=[list(f.vertices) for f in obj.data.polygons],
                keys=[] if not obj.data.shape_keys else [dict(name=k.name,value=k.value,vertices=[list(v.co) for v in k.data]) for k in obj.data.shape_keys.key_blocks])

class Model:
    def __init__(self,config):
        config=validate(config)
        self.config=config;self.d=dimensions(config)
        self.source=ROOT/'data/基準_Ver2.blend'
        self.source_hash=hashlib.sha256(self.source.read_bytes()).hexdigest()
        bpy.ops.wm.open_mainfile(filepath=str(self.source))
        bpy.context.preferences.filepaths.save_version=0
        if hasattr(bpy.context.preferences.filepaths,'use_save_preview_images'):
            bpy.context.preferences.filepaths.use_save_preview_images=False
        self.building=bpy.data.objects['建築限界'];self.building_signature=signature(self.building)
        for obj in list(bpy.data.objects):
            if obj!=self.building:bpy.data.objects.remove(obj,do_unlink=True)
        self.groups={kind:[vehicle(f'{i+1}号車_{kind}',car,kind) for i,car in enumerate(self.d['cars'])] for kind in ('body','gauge')}
        self.eq=[equipment(f'連接部{i+1}_機器配置限界',e) for i,e in enumerate(self.d['equipment'])]
        self.couplers=[]
        if config['normal_ends']:
            for i,length in enumerate(self.d['projections']):
                if length>0:self.couplers.append((i,mesh(f'外端{i+1}_参考連結器',[([(.18,.75),(.18,1.05)],0,length)],(.35,.40,.45,1))))
        self.objects=self.groups['body']+self.groups['gauge']+self.eq+[o for _,o in self.couplers]
        self.audit={o.name:audit(o) for o in self.objects+[self.building]}
        self.extras=[]
        sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
        sc['設定JSON']=json.dumps(config,ensure_ascii=False)
        self.place(config['radius_m'],config['direction'])

    def clear_extras(self):
        for obj in self.extras:bpy.data.objects.remove(obj,do_unlink=True)
        self.extras=[]

    def place(self,radius,sign=1):
        arr=formation(self.d,radius,sign)
        for group in self.groups.values():
            for obj,pose in zip(group,arr['poses']):transform(obj,pose)
        for obj,pose in zip(self.eq,arr['equipment_poses']):transform(obj,pose)
        for side,obj in self.couplers:
            index=0 if side==0 else -1;sgn=-1 if side==0 else 1
            pose=arr['poses'][index];position=point(pose,sgn*self.d['cars'][index]['length']/2)
            transform(obj,(*position,pose[2]+(math.pi if side==0 else 0)))
        self.building.hide_set(True);self.building.hide_render=True
        return arr

    def add_other(self,other,arr):
        groups={kind:[] for kind in ('body','gauge')}
        for kind in groups:
            for i,(car,pose) in enumerate(zip(other['cars'],arr['poses'])):
                obj=vehicle(f'相手_{i+1}号車_{kind}',car,kind);transform(obj,pose)
                groups[kind].append(obj);self.extras.append(obj)
        eq=[]
        for i,(e,pose) in enumerate(zip(other['equipment'],arr['equipment_poses'])):
            obj=equipment(f'相手_機器{i+1}',e);transform(obj,pose);eq.append(obj);self.extras.append(obj)
        return groups,eq

    def add_links(self,pivots,other):
        a,b=pivots;angle=math.atan2(b[1]-a[1],b[0]-a[0])
        # The first train's outward coupler is replaced by the exact joining link.
        for side,obj in self.couplers:
            if side==1:transform(obj,(*a,angle))
        length=other['projections'][0]
        if length:
            obj=mesh('相手_接続連結器',[([(.18,.75),(.18,1.05)],0,length)],(.35,.40,.45,1))
            transform(obj,(*b,angle+math.pi));self.extras.append(obj)

    def verify_meshes(self,report):
        rows=[]
        for case in report['pairs']:
            self.place(case['radius'],case['direction'])
            rows.append(dict(radius=case['radius'],direction=case['direction'],kind=case['kind'],
                             overlaps=overlaps(self.groups[case['kind']]+self.eq)))
        # Worst reference spacing for every tested radius/sign/kind, plus identical formations.
        for case in report['coupled']:
            if case['margin_m'] is None:continue
            self.clear_extras();other=self.d if case['other']=='same' else reference(case['spacing_m'])
            self.place(case['radius'],case['direction'])
            _,arr,_=coupled(self.d,other,case['radius'],case['direction'])
            groups,eq=self.add_other(other,arr)
            rows.append(dict(radius=case['radius'],direction=case['direction'],kind=case['kind'],other=case['other'],
                overlaps=overlaps(self.groups[case['kind']]+self.eq+groups[case['kind']]+eq)))
        self.clear_extras()
        report['mesh_surface_checks']=rows;report['mesh_audit']=self.audit
        report['building_mesh_unchanged']=signature(self.building)==self.building_signature
        report['source_sha256']=self.source_hash
        if not report['building_mesh_unchanged']:raise ValueError('建築限界形状が変更されました。')

    def save(self,path):
        bpy.context.view_layer.update()
        for obj in bpy.context.scene.objects:obj.select_set(False)
        for obj in self.groups['body']:obj.select_set(True)
        bpy.context.view_layer.objects.active=self.groups['body'][0]
        # A useful saved viewport without requiring any existing user screen layout.
        from mathutils import Quaternion
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type=='VIEW_3D':
                    space=area.spaces.active;space.clip_end=10000
                    space.region_3d.view_distance=max(25,self.d['length']*1.1)
                    space.region_3d.view_location=Vector((0,0,2))
                    space.region_3d.view_rotation=Quaternion((.86,.35,.15,.34)).normalized()
        bpy.ops.wm.save_as_mainfile(filepath=str(path))

    def export(self,out):
        self.clear_extras()
        for obj in self.objects:obj.matrix_world=Matrix.Identity(4)
        for obj in self.objects:obj.hide_set(obj not in [self.groups['body'][0],self.groups['gauge'][0]])
        self.building.hide_set(False);self.building.hide_render=False
        self.save(out/'部品モデル.blend')
        for obj in self.objects:obj.hide_set(False)
        self.place(0);self.save(out/'編成_直線.blend')
        self.place(self.config['radius_m'],self.config['direction']);self.save(out/'編成_指定条件.blend')
        if self.config['normal_ends']:
            for r in sorted(set([0,self.config['radius_m']])):
                for name,other in [('編成2組',self.d),('編成と20m級',reference(self.config['reference_spacing_m'][1]))]:
                    self.clear_extras();self.place(r,self.config['direction'])
                    try:
                        _,arr,pivots=coupled(self.d,other,r,self.config['direction'])
                    except ValueError:
                        continue  # The verification report records unconnectable conditions.
                    self.add_other(other,arr);self.add_links(pivots,other)
                    self.save(out/f'{name}_{"直線" if not r else "指定曲線"}.blend')
        self.clear_extras();self.place(self.config['radius_m'],self.config['direction'])
        if hashlib.sha256(self.source.read_bytes()).hexdigest()!=self.source_hash:raise ValueError('基準ファイルが変更されました。')
