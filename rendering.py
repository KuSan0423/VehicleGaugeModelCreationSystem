"""既存PNGに合わせたWorkbench斜視・上面プレビュー。"""
import math
import bpy
from mathutils import Vector,Matrix

def render(objects,path,top=False):
    scene=bpy.context.scene
    saved={obj:(obj.hide_render,obj.hide_get(),obj.display_type) for obj in scene.objects}
    for obj in scene.objects:obj.hide_render=obj not in objects
    for obj in objects:obj.hide_render=False;obj.hide_set(False);obj.display_type='SOLID'
    coords=[obj.matrix_world@v.co for obj in objects if obj.type=='MESH' for v in obj.data.vertices]
    center=Vector(tuple((min(v[i] for v in coords)+max(v[i] for v in coords))/2 for i in range(3)))
    camera_data=bpy.data.cameras.new('PreviewCamera');camera=bpy.data.objects.new('PreviewCamera',camera_data);scene.collection.objects.link(camera)
    direction=Vector((0,0,1)) if top else Vector((1.3,-1.8,1.3)).normalized()
    camera.location=center+direction*100
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.clip_end=10000;scene.camera=camera
    inverse=camera.rotation_euler.to_matrix().transposed();projected=[inverse@(v-center) for v in coords]
    width=max(v.x for v in projected)-min(v.x for v in projected)
    height=max(v.y for v in projected)-min(v.y for v in projected)
    camera.data.ortho_scale=max(height,width/1.5)*1.8
    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
    scene.display.shading.background_type='WORLD'
    if scene.world is None:scene.world=bpy.data.worlds.new('PreviewWorld')
    scene.world.color=(.65,.65,.65)
    scene.render.resolution_x=1500;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera,do_unlink=True)
    for obj,(hidden,viewport,display) in saved.items():obj.hide_render=hidden;obj.hide_set(viewport);obj.display_type=display

def previews(model,out):
    model.clear_extras()
    # Separated components, same colours and gray-background perspective as the source.
    objects=[]
    seen=set()
    for obj,car in zip(model.groups['body'],model.d['cars']):
        if car['length'] in seen:continue
        obj.matrix_world=Matrix.Translation((0,-7-len(seen)*7,0));objects.append(obj)
        seen.add(car['length'])
    gauge=model.groups['gauge'][0];gauge.matrix_world=Matrix.Identity(4);objects.append(gauge)
    model.building.matrix_world=Matrix.Translation((0,6,0));objects.append(model.building)
    for i,obj in enumerate(model.eq):obj.matrix_world=Matrix.Translation((15+i*3,0,0));objects.append(obj)
    render(objects,out/'モデルプレビュー.png')
    render(model.eq,out/'機器配置限界.png')
    model.building.matrix_world=Matrix.Identity(4)
    model.place(model.config['radius_m'],model.config['direction'])
    visible=model.groups['body']+model.eq+[o for _,o in model.couplers]
    render(visible,out/'連接部_斜視.png')
    render(visible,out/'連接部_上面.png',top=True)
