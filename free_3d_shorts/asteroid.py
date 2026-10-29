#!/usr/bin/env python3
"""Original procedural Blender vertical short; no downloaded visual assets."""
import bpy, math, random, os
from mathutils import Vector
random.seed(473)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='CYCLES' if os.environ.get('USE_CYCLES')=='1' else 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x=540;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.render.fps=24;scene.frame_start=1;scene.frame_end=240
scene.render.image_settings.file_format='PNG'
scene.render.filepath='frames/frame_'
scene.world.color=(0.006,0.009,0.026)

def mat(name,col,metal=0,rough=.5,emission=None,strength=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 if emission:p.inputs['Emission Color'].default_value=(*emission,1);p.inputs['Emission Strength'].default_value=strength
 return m
ocean=mat('deep blue ocean',(0.009,.12,.47),.25,.36)
land=mat('contrasting land',(0.05,.42,.22),.1,.8)
asteroid=mat('asteroid iron',(.28,.22,.21),.1,.9)
glow=mat('orange impact glow',(1,.12,.016),.2,.5,(1,.19,.01),3)
white=mat('white',(.94,.95,1),.05,.4,(.17,.32,.65),.2)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=2,location=(0,0,0))
planet=bpy.context.object;planet.name='Original fictional Earth-like planet';planet.data.materials.append(ocean)
bpy.ops.object.shade_smooth()
# Custom topographic patches as flattened spheres—stylized, not real geodata
for j in range(15):
 angle=random.uniform(0,math.tau); z=random.uniform(-1.4,1.4)
 radius=math.sqrt(max(.1,4-z*z))
 pos=Vector((radius*math.cos(angle),radius*math.sin(angle),z)); n=pos.normalized()
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=1,location=pos*1.008)
 p=bpy.context.object;p.name='Stylized continent %d'%j;p.data.materials.append(land)
 p.scale=(random.uniform(.3,.7),random.uniform(.2,.6),.06);p.rotation_euler=n.to_track_quat('Z','Y').to_euler()
 p.parent=planet
# Camera points down z; visual center raised to allow room for captions
bpy.ops.object.camera_add(location=(0,-11,3.6))
cam=bpy.context.object
direction=Vector((0,0,.1))-cam.location;cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=7.5;scene.camera=cam
bpy.ops.object.light_add(type='AREA',location=(-4,-5,5));bpy.context.object.data.energy=1700;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=7
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=.65,location=(4,-1,2))
rock=bpy.context.object;rock.name='Original asteroid';rock.data.materials.append(asteroid)
for v in rock.data.vertices:v.co*=random.uniform(.68,1.3)
bpy.ops.object.shade_smooth()
rock.location=(4.5,-2,2.2);rock.keyframe_insert('location',frame=1)
rock.location=(1.8,-1.7,.7);rock.keyframe_insert('location',frame=145)
rock.location=(.35,-1.5,-.3);rock.keyframe_insert('location',frame=200)
rock.scale=(1,1,1);rock.keyframe_insert('scale',frame=185)
rock.scale=(.02,.02,.02);rock.keyframe_insert('scale',frame=215)
for obj in [planet,rock]:
 obj.rotation_euler=(0,0,0);obj.keyframe_insert('rotation_euler',frame=1)
 obj.rotation_euler=(.12,.4,1.6);obj.keyframe_insert('rotation_euler',frame=240)
# An original glowing blast appears on impact
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.1,location=(.2,-1.9,-.1))
blast=bpy.context.object;blast.name='Impact animation';blast.data.materials.append(glow)
blast.scale=(0,0,0);blast.keyframe_insert('scale',frame=188)
blast.scale=(.01,.01,.01);blast.keyframe_insert('scale',frame=195)
blast.scale=(19,19,19);blast.keyframe_insert('scale',frame=230)
# Star field
for i in range(80):
 x=random.uniform(-6,6);z=random.uniform(-6,6)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=random.uniform(.008,.029),location=(x,3,z))
 bpy.context.object.data.materials.append(white)
scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath='scene.blend')
# video encoded by ffmpeg from image sequence after Blender exits.
bpy.ops.render.render(animation=True)
