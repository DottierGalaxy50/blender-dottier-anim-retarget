import bpy
import mathutils
import math
import textwrap

#import os
#bpy.ops.wm.console_toggle()
#os.system('cls')

update_values = True
bone_sel_empty = True
update_bone_list_search = False
correct_location_next = True

b_ang = {}
b_ang_base = {}

def check_scene_vars():
    if not bpy.context.scene.get("dottier_retarget_vars"):
        bpy.context.scene["dottier_retarget_vars"] = {}
        bpy.context.scene["dottier_retarget_vars"]["source"] = ""
        bpy.context.scene["dottier_retarget_vars"]["target"] = ""
        bpy.context.scene["dottier_retarget_vars"]["lst_bones"] = []
        bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"] = []
        bpy.context.scene["dottier_retarget_vars"]["multi_bone_sel_props"] = {
            "difference": False,
            "diff_rot": False,
            "diff_loc": False,
            "diff_rot_x": False,
            "diff_rot_y": False,
            "diff_rot_z": False,
            "diff_loc_x": False,
            "diff_loc_y": False,
            "diff_loc_z": False,
            "diff_loc_frac": False,
        }

def remove_handlers():
    for f in bpy.app.handlers.load_post: 
        if f.__name__ == 'dottier_load':
            bpy.app.handlers.load_post.remove(f)
            
    for f in bpy.app.handlers.depsgraph_update_post: 
        if f.__name__ == 'dottier_update_selection':
            bpy.app.handlers.depsgraph_update_post.remove(f)
            
    for f in bpy.app.handlers.frame_change_post: 
        if f.__name__ == 'dottier_frame_change':
            bpy.app.handlers.frame_change_post.remove(f)
            
remove_handlers()

from bpy.app.handlers import persistent

@persistent
def dottier_load(scene):
    check_scene_vars()

bpy.app.handlers.load_post.append(dottier_load)

@persistent
def dottier_update_selection(scene):
    global bone_sel_empty, update_bone_list_search, b_ang, b_ang_base, correct_location_next

    check_scene_vars()
    source = bpy.context.scene["dottier_retarget_vars"]["source"]
    target = bpy.context.scene["dottier_retarget_vars"]["target"]

    if not bpy.data.objects.get(target) or not bpy.data.objects.get(source):
        bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"] = []
        return

    b_ang = {}
    b_ang_base = {}

    if correct_location_next:
        correct_location_change()
    else:
        correct_location_next = True
    
    lst_bone_selection = bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]
    # Get the selected pose bones
    selected_bones = [bone.name for bone in bpy.data.objects[target].pose.bones if bone.bone.select]
    
    if sorted(lst_bone_selection) != sorted(selected_bones):
        bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"] = selected_bones           
        update_bone_list_search = True
        
        if len(selected_bones) > 0:
            bone_sel_empty = False
            dottier_update_panel()
        else:
            bone_sel_empty = True

bpy.app.handlers.depsgraph_update_post.append(dottier_update_selection)

@persistent
def dottier_frame_change(scene):
    global correct_location_next
    update_all_bones()
    correct_location_next = True
    
bpy.app.handlers.frame_change_post.append(dottier_frame_change)

##############################################################################
        
def apply_to_frame(frame):
    bpy.context.scene.frame_set(frame)
    target = bpy.context.scene["dottier_retarget_vars"]["target"]

    for bone in bpy.data.objects[target].pose.bones:
        #rot_mode = bone.rotation_mode
        bone.rotation_mode = 'QUATERNION'
        
        bone.keyframe_insert("location")
        bone.keyframe_insert("rotation_quaternion")   
        #bone.rotation_mode = rot_mode

#The location we copy from the Source Bone should be relative to his own parent, so we have to correct
#the Target Bone to always be at the correct location independently of his own parent's rotation.
def correct_location_change():
    check_scene_vars()
    source = bpy.context.scene["dottier_retarget_vars"]["source"]
    target = bpy.context.scene["dottier_retarget_vars"]["target"]
    
    if not bpy.data.objects.get(target) or not bpy.data.objects.get(source): return

    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    
    for bone_data in lst_bones:
        trg_bone = bpy.data.objects[target].pose.bones.get(bone_data["bone"])
        src_bone = bpy.data.objects[source].pose.bones.get(bone_data["bcopy"])
        
        if not src_bone or not trg_bone: continue
    
        loc_change_local = trg_bone["dottier_loc_change_local"].to_list() if trg_bone.get("dottier_loc_change_local") else (0,0,0)
        loc_change_world = trg_bone["dottier_loc_change_world"].to_list() if trg_bone.get("dottier_loc_change_world") else (0,0,0)
        loc_change_local = mathutils.Vector((loc_change_local[0], loc_change_local[1], loc_change_local[2]))
        loc_change_world = mathutils.Vector((loc_change_world[0], loc_change_world[1], loc_change_world[2]))
        
        trg_base_rot = trg_bone.matrix.to_quaternion() @ trg_bone.matrix_basis.to_quaternion().inverted()
        trg_bone.location = (trg_bone.location.copy() - loc_change_local) + (trg_base_rot.inverted() @ loc_change_world)
        
        trg_bone["dottier_loc_change_local"] = (trg_base_rot.inverted() @ loc_change_world)

#Differently to the location change, we only correct the rotation in determinated cases, we do it this way
#so you can still rotate bones from the 3d viewport without correcting their rotation.
def correct_rotation():
    check_scene_vars()
    source = bpy.context.scene["dottier_retarget_vars"]["source"]
    target = bpy.context.scene["dottier_retarget_vars"]["target"]

    if not bpy.data.objects.get(target) or not bpy.data.objects.get(source): return

    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    lst_bone_selection = bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]
    
    lst_corrected = []
    
    for bone in lst_bone_selection:
        if not bone in lst_corrected and bone in lst_bone_names:
            bone_data = lst_bones[lst_bone_names.index(bone)]
            trg_bone = bpy.data.objects[target].pose.bones.get(bone_data["bone"])
            lst_corrected.append(bone)
            
            if not trg_bone: continue
            update_bone(bone,correct_r=True)

            for child in trg_bone.children_recursive:   
                if child.name in lst_bone_names:
                    update_bone(child.name,correct_r=True)
                    lst_corrected.append(child.name)
            
def bone_fraction(bone):
    check_scene_vars()
    source = bpy.context.scene["dottier_retarget_vars"]["source"]
    target = bpy.context.scene["dottier_retarget_vars"]["target"]
    
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    lst_bcopy_names = [b_data["bcopy"] for b_data in lst_bones]
    
    bone_data = lst_bones[lst_bone_names.index(bone)] if bone in lst_bone_names else None
    
    if bone_data == None: return

    src_bone = bpy.data.objects[source].pose.bones.get(bone_data["bcopy"])
    trg_bone = bpy.data.objects[target].pose.bones.get(bone)
       
    if src_bone == None or trg_bone == None: return

    src_compare = trg_compare = None   
    
    for parent in src_bone.parent_recursive:
        if parent.name in lst_bcopy_names:
            parent_trg = lst_bones[lst_bcopy_names.index(parent.name)]["bone"]
            
            src_compare = parent
            trg_compare = bpy.data.objects[target].pose.bones.get(parent_trg)
            
            #If parent_trg is not a parent of Target Bone then trg_compare will equal none
            trg_compare = trg_compare if trg_compare in trg_bone.parent_recursive else None
            break

    if not src_compare or not trg_compare:
        if src_bone.parent != None and trg_bone.parent != None:
            src_compare = src_bone.parent
            trg_compare = trg_bone.parent
        else:
            bone_data["l_frac"] = 1.0
            return
        
    src_compare = src_compare.name
    trg_compare = trg_compare.name
    
    cur_src = src_bone
    cur_trg = trg_bone
    
    loc_base = loc_offset = None
    src_length = trg_length = 0    
    
    for parent in src_bone.parent_recursive:    
        if cur_src.name in lst_bcopy_names:
            src_data = lst_bones[lst_bcopy_names.index(cur_src.name)]
            loc_base = mathutils.Vector((src_data["bx"], src_data["by"], src_data["bz"]))
        else:
            loc_base = mathutils.Vector((0.0, 0.0, 0.0))

        src_loc = cur_src.matrix @ cur_src.matrix_basis.to_quaternion().inverted().to_matrix().to_4x4() @ mathutils.Matrix.Translation(-cur_src.matrix_basis.to_translation()) @ loc_base
        src_length += (src_loc-parent.matrix.to_translation()).length
        
        if parent.name == src_compare: break
        cur_src = parent
        
    for parent in trg_bone.parent_recursive:    
        if cur_trg.name in lst_bcopy_names:
            trg_data = lst_bones[lst_bcopy_names.index(cur_trg.name)]
            loc_offset = mathutils.Vector((trg_data["lx"], trg_data["ly"], trg_data["lz"]))
        else:
            loc_offset = mathutils.Vector((0.0, 0.0, 0.0))

        trg_loc = cur_trg.matrix @ cur_trg.matrix_basis.to_quaternion().inverted().to_matrix().to_4x4() @ mathutils.Matrix.Translation(-cur_trg.matrix_basis.to_translation()) @ loc_offset
        trg_length += (trg_loc-parent.matrix.to_translation()).length
        
        if parent.name == trg_compare: break
        cur_trg = parent
    
    frac = 1.0
    
    if src_length != 0.0:
        frac = trg_length/src_length
        
    if frac > 10.0:
        frac = 10.0
    
    bone_data["l_frac"] = frac
    
def set_source_bone_pose_as_base(bone,clear):
    check_scene_vars()
    source = bpy.context.scene["dottier_retarget_vars"]["source"]
    target = bpy.context.scene["dottier_retarget_vars"]["target"]
    
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    
    bone_data = lst_bones[lst_bone_names.index(bone)] if bone in lst_bone_names else None
    
    if bone_data == None: return

    if clear:
        bone_data["bx"] = 0.0
        bone_data["by"] = 0.0
        bone_data["bz"] = 0.0
    else:
        src_bone = bpy.data.objects[source].pose.bones.get(bone_data["bcopy"])
           
        if src_bone == None: return

        bone_data["bx"] = src_bone.location[0]
        bone_data["by"] = src_bone.location[1]
        bone_data["bz"] = src_bone.location[2]
    
def update_all_bones():
    check_scene_vars()
    source = bpy.context.scene["dottier_retarget_vars"]["source"]
    target = bpy.context.scene["dottier_retarget_vars"]["target"]
            
    if not bpy.data.objects.get(target) or not bpy.data.objects.get(source): return

    for bone in bpy.data.objects[target].pose.bones:
        update_bone(bone.name)
    
def update_bone(bone, apply_view=None, move_exact=None, correct_r=None):
    global b_ang, b_ang_base, correct_location_next

    check_scene_vars()
    source = bpy.context.scene["dottier_retarget_vars"]["source"]
    target = bpy.context.scene["dottier_retarget_vars"]["target"]
    
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    
    bonename = bone
    bone_data = lst_bones[lst_bone_names.index(bone)] if bone in lst_bone_names else None
    pose_bone = bpy.data.objects[target].pose.bones.get(bonename)
    
    if bone_data == None or pose_bone == None: return

    src_bone = bpy.data.objects[source].pose.bones.get(bone_data["bcopy"])
    correct_location_next = False
    
    b_ang_parent = None
    
    #Blender doesn't update the bone's matrix until the script finishes, so we have to store the new rotation
    #of the parent separately and then use it when needed.
    if pose_bone.parent != None:
        b_ang_parent = b_ang[pose_bone.parent.name].copy() if pose_bone.parent.name in b_ang else pose_bone.parent.matrix.to_quaternion()
    
    new_matrix = pose_bone.matrix.copy() @ pose_bone.matrix_basis.to_quaternion().inverted().to_matrix().to_4x4() @ mathutils.Matrix.Translation(-pose_bone.matrix_basis.to_translation())
    rot = new_matrix.to_quaternion()
    
    new_b_ang_base = rot.copy()
    
    if pose_bone.parent != None:
        rot_diff = rot.rotation_difference(pose_bone.parent.matrix.to_quaternion())     
        rot = b_ang_parent @ rot_diff.inverted()
        
        new_b_ang_base = rot_diff.copy()
        
    #Get base rot this way if the bone has been updated already and there hasn't been a scene update.
    if bonename in b_ang_base:       
        if pose_bone.parent != None:   
            rot = b_ang_parent @ b_ang_base[bonename].copy().inverted()
        else:
            rot = b_ang_base[bonename].copy()
    else:
        b_ang_base[bonename] = new_b_ang_base.copy()
    
    src_rot_world = bpy.data.objects[source].matrix_world.to_quaternion()
    trg_rot_world = bpy.data.objects[target].matrix_world.to_quaternion()
    
    #Copy Location & Rotation
        
    new_loc = mathutils.Vector((0, 0, 0))
        
    if bone_data["l"] and src_bone:
        src_bone_matrix = src_rot_world.to_matrix().to_4x4() @ (src_bone.matrix @ src_bone.matrix_basis.to_quaternion().inverted().to_matrix().to_4x4())
        loc_base = mathutils.Vector((bone_data["bx"], bone_data["by"], bone_data["bz"]))  
        new_loc = trg_rot_world.inverted() @ src_bone_matrix.to_quaternion() @ ((src_bone.location-loc_base) * bone_data["l_frac"]) 
    
    new_rot = None
            
    if bone_data["r"] and src_bone:
        new_rot = trg_rot_world.inverted() @ src_rot_world @ src_bone.matrix.to_quaternion()

    #scale = pose_bone.scale.copy()
    #loc = pose_bone.location
    #rot = new_matrix.to_quaternion().to_matrix().to_4x4()
    
    #Apply Location & Rotation
    
    if bone_data["l"] and src_bone: 
        if not correct_r:
            if apply_view:
                loc_offset = pose_bone.location - (rot.inverted() @ new_loc)
                bone_data["lx"] = loc_offset[0]
                bone_data["ly"] = loc_offset[1]
                bone_data["lz"] = loc_offset[2]
                
            pose_bone["dottier_loc_change_local"] = (rot.inverted() @ new_loc)
            pose_bone["dottier_loc_change_world"] = new_loc
                
            if move_exact:
                loc_offset = (rot.inverted() @ ((trg_rot_world.inverted() @ src_rot_world @ src_bone.matrix.to_translation())-new_matrix.to_translation())) - (rot.inverted() @ new_loc)
                bone_data["lx"] = loc_offset[0]
                bone_data["ly"] = loc_offset[1]
                bone_data["lz"] = loc_offset[2]
            
            loc = (rot.inverted() @ new_loc) + mathutils.Vector((bone_data["lx"], bone_data["ly"], bone_data["lz"]))
    else:
        if apply_view:
            loc_offset = pose_bone.location
            bone_data["lx"] = loc_offset[0]
            bone_data["ly"] = loc_offset[1]
            bone_data["lz"] = loc_offset[2]
            
        pose_bone["dottier_loc_change_local"] = 0.0
        pose_bone["dottier_loc_change_world"] = 0.0
            
        if move_exact and src_bone:
            loc_offset = rot.inverted() @ ((trg_rot_world.inverted() @ src_rot_world @ src_bone.matrix.to_translation())-new_matrix.to_translation())
            bone_data["lx"] = loc_offset[0]
            bone_data["ly"] = loc_offset[1]
            bone_data["lz"] = loc_offset[2]
            
        loc = mathutils.Vector((bone_data["lx"],bone_data["ly"],bone_data["lz"]))

    if bone_data["r"] and src_bone:
        rot_mode = pose_bone.rotation_mode
        pose_bone.rotation_mode = 'QUATERNION'
        
        if apply_view:
            rot_offset = (pose_bone.rotation_quaternion.rotation_difference(rot.inverted() @ new_rot).inverted()).to_euler()
            bone_data["rx"] = math.degrees(rot_offset[0])
            bone_data["ry"] = math.degrees(rot_offset[1])
            bone_data["rz"] = math.degrees(rot_offset[2])

        pose_bone.rotation_quaternion = (rot.inverted() @ new_rot) @ mathutils.Euler((math.radians(bone_data["rx"]), math.radians(bone_data["ry"]), math.radians(bone_data["rz"])), 'XYZ').to_quaternion()
        pose_bone.rotation_mode = rot_mode
        rot = new_rot @ mathutils.Euler((math.radians(bone_data["rx"]), math.radians(bone_data["ry"]), math.radians(bone_data["rz"])), 'XYZ').to_quaternion()
    else:
        rot_mode = pose_bone.rotation_mode
        pose_bone.rotation_mode = 'QUATERNION'
        
        if apply_view:
            rot_offset = pose_bone.rotation_quaternion.to_euler()
            bone_data["rx"] = math.degrees(rot_offset[0])
            bone_data["ry"] = math.degrees(rot_offset[1])
            bone_data["rz"] = math.degrees(rot_offset[2])
        
        pose_bone.rotation_quaternion = mathutils.Euler((math.radians(bone_data["rx"]), math.radians(bone_data["ry"]), math.radians(bone_data["rz"])), 'XYZ').to_quaternion()
        pose_bone.rotation_mode = rot_mode
        rot = rot @ mathutils.Euler((math.radians(bone_data["rx"]), math.radians(bone_data["ry"]), math.radians(bone_data["rz"])), 'XYZ').to_quaternion()
    
    b_ang[bonename] = rot.copy()
    
    if not correct_r:
        pose_bone.location = loc
    #pose_bone.scale = scale

#############################################################################################
######################################################### Blender Panel #####################
#############################################################################################

bl_info = {
    "name": "Dottier's Anim Retarget",
    "author": "DottierGalaxy50",
    "version": (1, 0, 0),
    "blender": (4, 0),
    "location": "3D Viewport > Sidebar > Dottier's Anim Retarget",
    "description": "Retarget and correct animations onto other armatures",
    "category": "Animation",
    "doc_url": "https://github.com/DottierGalaxy50/blender-dottier-anim-retarget",
}

def dottier_update_panel():
    global update_values
    
    check_scene_vars()
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_selection = bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    multi_bone_sel_props = bpy.context.scene["dottier_retarget_vars"]["multi_bone_sel_props"]
    
    bone_data = None
    
    for bone in lst_bone_selection:
        if bone in lst_bone_names:
            bone_data = lst_bones[lst_bone_names.index(bone)]
            break
        
    if bone_data == None: return

    retarget_props = bpy.context.scene.dottier_retarget   
    update_values = False
    multi_bone_sel_equality()
        
    if multi_bone_sel_props["diff_rot"]:
        retarget_props.cp_rot = False
    else:
        retarget_props.cp_rot = bone_data["r"]  
    
    if multi_bone_sel_props["diff_loc"]:
        retarget_props.cp_loc = False
    else:
        retarget_props.cp_loc = bone_data["l"]  
        
    # Rotation
    
    if multi_bone_sel_props["diff_rot_x"]:
        retarget_props.rot_x = 0.0
    else:
        retarget_props.rot_x = bone_data["rx"]        
    if multi_bone_sel_props["diff_rot_y"]:
        retarget_props.rot_y = 0.0
    else:
        retarget_props.rot_y = bone_data["ry"]        
    if multi_bone_sel_props["diff_rot_z"]:
        retarget_props.rot_z = 0.0
    else:
        retarget_props.rot_z = bone_data["rz"]
        
    # Location
        
    if multi_bone_sel_props["diff_loc_x"]:
        retarget_props.loc_x = 0.0
    else:
        retarget_props.loc_x = bone_data["lx"]        
    if multi_bone_sel_props["diff_loc_y"]:
        retarget_props.loc_y = 0.0
    else:
        retarget_props.loc_y = bone_data["ly"]        
    if multi_bone_sel_props["diff_loc_z"]:
        retarget_props.loc_z = 0.0
    else:
        retarget_props.loc_z = bone_data["lz"]

    if multi_bone_sel_props["diff_loc_frac"]:
        retarget_props.loc_frac = 0.0
    else:
        retarget_props.loc_frac = bone_data["l_frac"]
    
    update_values = True

def multi_bone_sel_equality():
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_selection = bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    multi_bone_sel_props = bpy.context.scene["dottier_retarget_vars"]["multi_bone_sel_props"]
    
    multi_bone_sel_props["difference"] = False
    multi_bone_sel_props["diff_rot"] = False
    multi_bone_sel_props["diff_loc"] = False
    multi_bone_sel_props["diff_rot_x"] = False
    multi_bone_sel_props["diff_rot_y"] = False
    multi_bone_sel_props["diff_rot_z"] = False
    multi_bone_sel_props["diff_loc_x"] = False
    multi_bone_sel_props["diff_loc_y"] = False
    multi_bone_sel_props["diff_loc_z"] = False
    multi_bone_sel_props["diff_loc_frac"] = False
    
    first_bone_data = None
    
    for bone in lst_bone_selection:
        if bone in lst_bone_names:
            first_bone_data = lst_bones[lst_bone_names.index(bone)]
            break
        
    if first_bone_data == None: return
    
    for bone in lst_bone_selection:   
        bone_data = lst_bones[lst_bone_names.index(bone)] if bone in lst_bone_names else None
        
        if bone_data == None: continue

        if first_bone_data["r"] != bone_data["r"]: multi_bone_sel_props["diff_rot"] = True
        if first_bone_data["l"] != bone_data["l"]: multi_bone_sel_props["diff_loc"] = True

        if first_bone_data["rx"] != bone_data["rx"]: multi_bone_sel_props["diff_rot_x"] = True
        if first_bone_data["ry"] != bone_data["ry"]: multi_bone_sel_props["diff_rot_y"] = True
        if first_bone_data["rz"] != bone_data["rz"]: multi_bone_sel_props["diff_rot_z"] = True
        
        if first_bone_data["lx"] != bone_data["lx"]: multi_bone_sel_props["diff_loc_x"] = True
        if first_bone_data["ly"] != bone_data["ly"]: multi_bone_sel_props["diff_loc_y"] = True
        if first_bone_data["lz"] != bone_data["lz"]: multi_bone_sel_props["diff_loc_z"] = True
    
        if first_bone_data["l_frac"] != bone_data["l_frac"]: multi_bone_sel_props["diff_loc_frac"] = True
        
    if True in multi_bone_sel_props.values():
        multi_bone_sel_props["difference"] = True
    
def update_transformation(trans_type,axis,val):
    global update_values
    
    check_scene_vars()
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_selection = bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    multi_bone_sel_props = bpy.context.scene["dottier_retarget_vars"]["multi_bone_sel_props"]
    
    if not update_values: return

    retarget_props = bpy.context.scene.dottier_retarget
     
    for bone in lst_bone_selection: 
        lst_bones[lst_bone_names.index(bone)][axis] = val
        update_bone(bone)
        
    if trans_type == "rot":
        correct_rotation()
    
    if multi_bone_sel_props["difference"]:
        if multi_bone_sel_props["diff_"+trans_type+"_"+axis[1]]:
            multi_bone_sel_equality()
        
def rx_update(self, context):
    update_transformation("rot","rx",self.rot_x); return None
def ry_update(self, context):
    update_transformation("rot","ry",self.rot_y); return None
def rz_update(self, context):
    update_transformation("rot","rz",self.rot_z); return None
def lx_update(self, context):
    update_transformation("loc","lx",self.loc_x); return None
def ly_update(self, context):
    update_transformation("loc","ly",self.loc_y); return None
def lz_update(self, context):
    update_transformation("loc","lz",self.loc_z); return None

def prop_cp_loc(self, context):
    global update_values
    if not update_values: return
    
    check_scene_vars()
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    multi_bone_sel_props = bpy.context.scene["dottier_retarget_vars"]["multi_bone_sel_props"]

    for bone in bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]:
        lst_bones[lst_bone_names.index(bone)]["l"] = self.cp_loc
        lst_bones[lst_bone_names.index(bone)]["l_frac"] = self.loc_frac
        update_bone(bone)
        
    if multi_bone_sel_props["difference"]:
        if multi_bone_sel_props["diff_loc_frac"]:
            multi_bone_sel_equality()
                
    return None

def prop_cp_rot(self, context):
    global update_values
    if not update_values: return

    check_scene_vars()
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    
    for bone in bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]: 
        lst_bones[lst_bone_names.index(bone)]["r"] = self.cp_rot
        update_bone(bone)

    correct_rotation()

    return None

armatures_dont_update = False

def armatures_update(self, context):
    global armatures_dont_update, update_bone_list_search
    
    check_scene_vars()
    
    #Avoid infinite recursion
    if armatures_dont_update:
        armatures_dont_update = False
        return
    
    src_name = self.Source.name if self.Source else ""
    trg_name = self.Target.name if self.Target else ""

    if src_name == bpy.context.scene["dottier_retarget_vars"]["target"]:
        armatures_dont_update = True
        self.Source = None
        bpy.context.scene["dottier_retarget_vars"]["source"] = ""
    else:
        bpy.context.scene["dottier_retarget_vars"]["source"] = src_name 
        
    if trg_name == bpy.context.scene["dottier_retarget_vars"]["source"]:
        armatures_dont_update = True
        self.Target = None
        bpy.context.scene["dottier_retarget_vars"]["target"] = ""
    else:
        bpy.context.scene["dottier_retarget_vars"]["target"] = trg_name
    
    update_bone_list_search = True
    update_all_bones()
    dottier_update_panel()

    return None

def dottier_src_bone_search(self, context, edit_text):
    check_scene_vars()
    source = bpy.context.scene["dottier_retarget_vars"]["source"]
    
    show_all = False
        
    if edit_text == self.bcopy:
        show_all = True
        
    lst_options = None

    if show_all:
        lst_options = [bone.name for bone in bpy.data.objects[source].pose.bones]
    else:
        lst_options = [bone.name for bone in bpy.data.objects[source].pose.bones if bone.name.lower().find(edit_text.lower()) != -1]
    
    if bpy.data.objects[source].pose.bones.get(self.bcopy) != None:
        if self.bcopy in lst_options: 
            lst_options.remove(self.bcopy)
    
        lst_options.insert(0,self.bcopy)
    
    return lst_options

def dottier_trg_bone_search(self, context, edit_text):
    check_scene_vars()
    target = bpy.context.scene["dottier_retarget_vars"]["target"]

    show_all = False
        
    if edit_text == self.bone:
        show_all = True
        
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
        
    lst_options = None
    
    if show_all:      
        lst_options = [bone.name for bone in bpy.data.objects[target].pose.bones if not (bone.name in lst_bone_names)]
    else:
        lst_options = [bone.name for bone in bpy.data.objects[target].pose.bones if (bone.name.lower().find(edit_text.lower()) != -1)
               and not (bone.name in lst_bone_names)]
    
    if bpy.data.objects[target].pose.bones.get(self.bone) != None:
        if self.bone in lst_options: 
            lst_options.remove(self.bone)
    
        lst_options.insert(0,self.bone)
    
    return lst_options

lst_item_dont_update = False

def lst_item_update(self, context):
    global lst_item_dont_update, update_values
    if not update_values: return

    check_scene_vars()
    target = bpy.context.scene["dottier_retarget_vars"]["target"]

    #Avoid infinite recursion
    if lst_item_dont_update:
        lst_item_dont_update = False
        return
    
    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    lst_bone_names = [b_data["bone"] for b_data in lst_bones]
    already_on_list = False

    #Check if bone is already on the list
    for bone in bpy.data.objects[target].pose.bones:
        if self.bone == bone.name:
            if self.bone in lst_bone_names:
                already_on_list = True
            
    new_bonename = self.bone
    
    #If bone is already on list, use previous name
    if already_on_list:
        lst_item_dont_update = True
        bone = lst_bones[self.index]["bone"]
        new_bonename = bone
        self.bone = bone
        
    #update_bone(lst_bones[self.index]["bone"])
        
    lst_bones[self.index]["bone"] = new_bonename   
    lst_bones[self.index]["bcopy"] = self.bcopy
    
    update_bone(new_bonename)
    correct_rotation()

    return None

class dottier_retarget_lst_item(bpy.types.PropertyGroup):
    bone :  bpy.props.StringProperty(name= "", search=dottier_trg_bone_search, update=lst_item_update)
    bcopy : bpy.props.StringProperty(name= "", search=dottier_src_bone_search, update=lst_item_update)
    index : bpy.props.IntProperty(name= "")

class dottier_retarget_props(bpy.types.PropertyGroup):  
    cp_loc : bpy.props.BoolProperty(name= "Copy Location", update=prop_cp_loc, description="Copy Source Bone's exact location change")
    cp_rot : bpy.props.BoolProperty(name= "Copy Rotation", update=prop_cp_rot, description="Copy Source Bone's exact rotation")
    
    rot_x : bpy.props.FloatProperty(name= "X", soft_min=-360, soft_max=360, update=rx_update)
    rot_y : bpy.props.FloatProperty(name= "Y", soft_min=-360, soft_max=360, update=ry_update)
    rot_z : bpy.props.FloatProperty(name= "Z", soft_min=-360, soft_max=360, update=rz_update)
    
    loc_x : bpy.props.FloatProperty(name= "X", update=lx_update)
    loc_y : bpy.props.FloatProperty(name= "Y", update=ly_update)
    loc_z : bpy.props.FloatProperty(name= "Z", update=lz_update)
    
    loc_frac : bpy.props.FloatProperty(name= "Influence", soft_min=0, soft_max=2, step=1, update=prop_cp_loc, description="How much of the location change to apply.") #(Default value is an estimate obtained by the length difference between both bones and a shared parent from both armatures)
    
    Source : bpy.props.PointerProperty(type=bpy.types.Armature, update=armatures_update, description="The armature you want to copy the animations from")
    Target : bpy.props.PointerProperty(type=bpy.types.Armature, update=armatures_update, description="The armature you want to pass the animations to")

    lst_bones : bpy.props.CollectionProperty(type=dottier_retarget_lst_item)

class VIEW3D_PT_dottier_retarget_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dottier's Anim Retarget"
    bl_label = "Dottier's Anim Retarget"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        retarget_props = scene.dottier_retarget
        
        check_scene_vars()
        source = bpy.context.scene["dottier_retarget_vars"]["source"]
        target = bpy.context.scene["dottier_retarget_vars"]["target"]
        
        missing_armature = False
                
        if not bpy.data.objects.get(target) or not bpy.data.objects.get(source): missing_armature = True 
        if not bpy.context.scene["dottier_retarget_vars"]: return
        
        multi_bone_sel_props = bpy.context.scene["dottier_retarget_vars"]["multi_bone_sel_props"]
        lst_bone_selection = bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]
        lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
        lst_bone_names = [b_data["bone"] for b_data in lst_bones]
        
        layout.prop_search(retarget_props, "Source", bpy.data, "armatures", text="Source", icon="ARMATURE_DATA")
        layout.prop_search(retarget_props, "Target", bpy.data, "armatures", text="Target", icon="ARMATURE_DATA")
        
        if not missing_armature:
            row = layout.row()
            row.operator("dottier_retarget.gen_list", text="Generate Bone Link list")
            
            column = layout.row().column(align=True)
            box = column.box()
            
            row = box.row()
            row.scale_x = 1.35
            row.scale_y = 0.5
            row.alignment = 'CENTER'
            row.label(text="Target")
            row.label(icon="THREE_DOTS")
            row.label(text="Source")
            
            row = column.row()
            row.template_list("VIEW3D_UL_dottier_bone_ui_list", "", retarget_props, "lst_bones", context.object, "active_material_index")
        
        bone_sel_missing = False
        
        for bone in lst_bone_selection:
            if not bone in lst_bone_names:
                bone_sel_missing = True
        
        if len(lst_bone_selection) < 1 or bone_sel_missing:                       
            box = layout.box()
            box.scale_y = 0.6 #0.8
            
            new_icon = "INFO"
            
            if not bone_sel_missing:
                if missing_armature:
                    text = "Select the armatures you want to work with."
                    box.scale_y = 1
                else:
                    text = "While on Pose Mode, select one or multiple bones of Target from the 3D View to modify their properties."
            else:
                text = "One or multiple bones of Target are missing from the Bone Link list. Fill the list with all the Target bones." #⚠
                new_icon = "ERROR"
            
            #Text Wrap: https://blender.stackexchange.com/questions/74052/wrap-text-within-a-panel
            
            # Get the 3D View area
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    break
            # Calculate the width of the panel
            for region in area.regions:
                if region.type == 'UI':
                    panel_width = region.width
                    break

            # Calculate the maximum width of the label
            uifontscale = 9 * context.preferences.view.ui_scale

            max_label_width = int(panel_width // uifontscale)
            max_label_width += int(0.00008*(panel_width*panel_width)) #0.0001
            
            first_line = True

            # Split the text into lines and format each line
            for line in text.splitlines():
                # Remove leading and trailing whitespace
                line = line.strip()
                
                for chunk in textwrap.wrap(line, width=max_label_width):
                    if first_line:
                        box.label(text=chunk, icon=new_icon); first_line = False
                    else:
                        box.label(text=chunk)

        else:

            bonename = lst_bone_selection[0]
            sourcename = lst_bones[lst_bone_names.index(bonename)]["bcopy"]
            
            if not bpy.data.objects[source].pose.bones.get(sourcename):
                sourcename = "(⚠ Missing Bone)"
            
            if len(lst_bone_selection) > 1:
                bonename = "* (Multiple)"
                
                for bone in lst_bone_selection:
                    if lst_bones[lst_bone_names.index(bone)]["bcopy"] != sourcename:
                        sourcename = "* (Multiple)"
                        break
            
            box = layout.box()
            column = box.row().column(align=True)

            row = column.row(align=True)
            row.label(text="Target: "+bonename, icon='BONE_DATA')
            row = column.row()
            row.label(text="Source: "+sourcename, icon='BONE_DATA')
            
            row = layout.row().column(align=True).row(align=True)
            row.operator("dottier_retarget.apply_view", text="Apply view as Offset", icon="GRID")
            row.operator("dottier_retarget.refresh", text="", icon="FILE_REFRESH")
                
            row = layout.row()
            row.label(text="Location Offset:")
            column = layout.row().column(align=True)
            
            row = column.row(align=True)
            if multi_bone_sel_props["diff_loc_x"]:
                row.prop(retarget_props, "loc_x", text="X: (Different)")
                row.label(icon='ERROR')
            else:
                row.prop(retarget_props, "loc_x", text="X:")
            
            row = column.row(align=True)
            if multi_bone_sel_props["diff_loc_y"]:
                row.prop(retarget_props, "loc_y", text="Y: (Different)")
                row.label(icon='ERROR')
            else:
                row.prop(retarget_props, "loc_y", text="Y:")
            
            row = column.row(align=True)
            if multi_bone_sel_props["diff_loc_z"]:
                row.prop(retarget_props, "loc_z", text="Z: (Different)")
                row.label(icon='ERROR')
            else:
                row.prop(retarget_props, "loc_z", text="Z:")
            
            row = layout.row()
            row.label(text="Rotation Offset:")
            column = layout.row().column(align=True)
            
            row = column.row(align=True)
            if multi_bone_sel_props["diff_rot_x"]:
                row.prop(retarget_props, "rot_x", text="X: (Different)")
                row.label(icon='ERROR')
            else:
                row.prop(retarget_props, "rot_x", text="X:")
            
            row = column.row(align=True)
            if multi_bone_sel_props["diff_rot_y"]:
                row.prop(retarget_props, "rot_y", text="Y: (Different)")
                row.label(icon='ERROR')
            else:
                row.prop(retarget_props, "rot_y", text="Y:")
            
            row = column.row(align=True)
            if multi_bone_sel_props["diff_rot_z"]:
                row.prop(retarget_props, "rot_z", text="Z: (Different)")
                row.label(icon='ERROR')
            else:
                row.prop(retarget_props, "rot_z", text="Z:")
                
            box = layout.box()
            row = box.row()
            row.prop(retarget_props, "cp_rot")
            
            column = layout.row().column(align=True)
            box = column.box()
            row = box.row(align=False)
            row.prop(retarget_props, "cp_loc")
            row.operator("dottier_retarget.move_exact", text="Move to Exact", icon="CON_LOCLIKE")
            
            row = box.row().column(align=True).row(align=True)
            if multi_bone_sel_props["diff_loc_frac"]:
                row.prop(retarget_props, "loc_frac", text="Influence: (Different)")
                row.label(icon='ERROR')
            else:
                row.prop(retarget_props, "loc_frac", text="Influence:")
            row.operator("dottier_retarget.estimate_fraction", text="", icon="DRIVER_DISTANCE")
                
            row = box.row().column(align=True).row(align=True)
            row.operator("dottier_retarget.set_base", text="Set current location as Base", icon="OBJECT_ORIGIN")
            row.operator("dottier_retarget.clear_base", text="", icon="X")
            
        row = layout.row()
        row.operator("dottier_retarget.save_config", text="Save Config")
        
        if not missing_armature:
            row.operator("dottier_retarget.load_config", text="Load Config")
        
            row = layout.row()
            row.operator("dottier_retarget.clear_list", text="Clear Bone Link list")
        
            row = layout.row()
            row.scale_y = 1.5
            row.operator("dottier_retarget.apply_keyframes", text="Update All Keyfames", icon="KEYFRAME")
        
class VIEW3D_OT_dottier_retarget_apply_view(bpy.types.Operator):
    """Apply the current Target Bone's transformation from the 3D Viewport as an Offset"""
    bl_label = "Operator"
    bl_idname = "dottier_retarget.apply_view"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for bone in bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]:
            bpy.context.view_layer.update()
            update_bone(bone, apply_view=True)

        correct_rotation()
        dottier_update_panel()
        
        return {'FINISHED'}
    
class VIEW3D_OT_dottier_retarget_refresh(bpy.types.Operator):
    """Refreshes the Target Bone. (Removes unapplied transformations)"""
    bl_label = "Refresh Target Bone"
    bl_idname = "dottier_retarget.refresh"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for bone in bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]:
            update_bone(bone)
            
        correct_rotation()
        
        return {'FINISHED'}
    
class VIEW3D_OT_dottier_retarget_move_exact(bpy.types.Operator):
    """Moves Target Bone to his Source Bone's current exact location relative to the armature's space and applies it as a Location Offset"""#. (Doesn't take into account the Location Change Influence)"""
    bl_label = "Operator"
    bl_idname = "dottier_retarget.move_exact"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for bone in bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]:
            bpy.context.view_layer.update()
            update_bone(bone, move_exact=True)
            
        dottier_update_panel()
        
        return {'FINISHED'}

class VIEW3D_OT_dottier_retarget_estimate_fraction(bpy.types.Operator):
    """Estimates the influence by comparing two lengths obtained from the Source Bone and Target bone up to a parent shared by both on their respective armatures. (Takes into account the Location Offset and Location Base)"""
    bl_label = "Estimate influence"
    bl_idname = "dottier_retarget.estimate_fraction"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for bone in bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]: 
            bone_fraction(bone)
            update_bone(bone)
               
        dottier_update_panel()
        
        return {'FINISHED'}

class VIEW3D_OT_dottier_retarget_set_pose_as_base(bpy.types.Operator):
    """Set the current Source Bone's relative location as the location base from which to apply location changes"""
    bl_label = "Operator"
    bl_idname = "dottier_retarget.set_base"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for bone in bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]: 
            set_source_bone_pose_as_base(bone,False)
            update_bone(bone)
        
        return {'FINISHED'}
    
class VIEW3D_OT_dottier_retarget_clear_location_base(bpy.types.Operator):
    """Clears Location Base to use default instead"""
    bl_label = "Clear Location Base"
    bl_idname = "dottier_retarget.clear_base"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for bone in bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]: 
            set_source_bone_pose_as_base(bone,True)
            update_bone(bone)
        
        return {'FINISHED'}
    
class VIEW3D_OT_dottier_retarget_apply_keyframes(bpy.types.Operator):
    """Updates all frames with the current configuration"""
    bl_label = "Operator"
    bl_idname = "dottier_retarget.apply_keyframes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):  
        scene = bpy.context.scene
        update_all_bones()
        for frame in range(scene.frame_start, scene.frame_end+1):
            apply_to_frame(frame)
        
        return {'FINISHED'}
    
clear_bone_list_search = False
    
class VIEW3D_OT_dottier_retarget_clear_list(bpy.types.Operator):
    """Clears the entire Bone Link list"""
    bl_label = "Operator"
    bl_idname = "dottier_retarget.clear_list"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global clear_bone_list_search
        
        layout = self.layout
        scene = context.scene    
        clear_bone_list_search = True
        
        bpy.context.scene["dottier_retarget_vars"]["lst_bones"] = []
        bpy.context.scene.dottier_retarget.lst_bones.clear()
        
        return {'FINISHED'}
    
class VIEW3D_OT_dottier_retarget_gen_list(bpy.types.Operator):
    """Generate Bone Link list. (Target Bones already on the list won't be overwritten)"""
    bl_label = "Operator"
    bl_idname = "dottier_retarget.gen_list"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context): 
        global update_values, update_bone_list_search
        
        source = bpy.context.scene["dottier_retarget_vars"]["source"]
        target = bpy.context.scene["dottier_retarget_vars"]["target"]
        
        #bpy.context.scene["dottier_retarget_vars"]["lst_bones"] = []
        #bpy.context.scene.dottier_retarget.lst_bones.clear()
        
        lst_bones_new = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]

        if str(type(lst_bones_new)).find("list") == -1:
            lst_bones_new = lst_bones_new.to_list()
        
        lst_bone_names = [b_data["bone"] for b_data in lst_bones_new]
        
        update_values = False
        update_bone_list_search = True

        for bone in bpy.data.objects[target].pose.bones:
            if bone.name in lst_bone_names: continue
        
            src_name = bone.name if bpy.data.objects[source].pose.bones.get(bone.name) else ""

            lst_bone = bpy.context.scene.dottier_retarget.lst_bones.add()
            index = len(bpy.context.scene.dottier_retarget.lst_bones)-1
            
            lst_bone.bone = bone.name
            lst_bone.bcopy = src_name
            lst_bone.index = index
            
            lst_bones_new.append({
                "bone": bone.name,
                "bcopy": src_name,
                "l": True,
                "l_frac": 1.0,
                "r": True,
                "lx": 0,
                "ly": 0,
                "lz": 0,
                "rx": 0,
                "ry": 0,
                "rz": 0,
                "bx": 0,
                "by": 0,
                "bz": 0,
            })
            
        bpy.context.scene["dottier_retarget_vars"]["lst_bones"] = lst_bones_new.copy()
        
        #for bone in bpy.data.objects[target].pose.bones:
        #    bone_fraction(bone)

        update_values = True
        update_all_bones()
        dottier_update_panel()
        
        return {'FINISHED'}

#https://blender.stackexchange.com/questions/245005/how-to-create-and-export-a-custom-file-using-python
def dottier_write_data(context, filepath):
    f = open(filepath, 'w', encoding='utf-8')

    lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
    for bone in lst_bones:
        if bone["bone"].strip() == "": continue

        f.write(str(bone["bone"]))
        f.write(','+str(bone["bcopy"]))
        f.write(','+str(bone["l"]))
        f.write(','+str(bone["l_frac"]))
        f.write(','+str(bone["r"]))
        f.write(','+str(bone["lx"]))
        f.write(','+str(bone["ly"]))
        f.write(','+str(bone["lz"]))
        f.write(','+str(bone["rx"]))
        f.write(','+str(bone["ry"]))
        f.write(','+str(bone["rz"]))
        f.write(','+str(bone["bx"]))
        f.write(','+str(bone["by"]))
        f.write(','+str(bone["bz"]))
        f.write('\n')

    f.close()
    return {'FINISHED'}

def dottier_load_data(context, filepath):
    global update_values, update_bone_list_search
    
    target = bpy.context.scene["dottier_retarget_vars"]["target"]
    new_lst_bones = []
    
    try:
        f = open(filepath, 'r')
        
        for line in f:
            val = line.split(",")
            
            new_lst_bones.append({
                "bone": val[0],
                "bcopy": val[1],
                "l": eval(val[2]),
                "l_frac": float(val[3]),
                "r": eval(val[4]),
                "lx": float(val[5]),
                "ly": float(val[6]),
                "lz": float(val[7]),
                "rx": float(val[8]),
                "ry": float(val[9]),
                "rz": float(val[10]),
                "bx": float(val[11]),
                "by": float(val[12]),
                "bz": float(val[13]),
            })

        f.close()
        
    except Exception: return {'FINISHED'}
    
    if len(new_lst_bones) < len(bpy.data.objects[target].pose.bones):
        for i in range(len(bpy.data.objects[target].pose.bones) - len(new_lst_bones)):
            new_lst_bones.append({
                "bone": "",
                "bcopy": "",
                "l": True,
                "l_frac": 1.0,
                "r": True,
                "lx": 0.0,
                "ly": 0.0,
                "lz": 0.0,
                "rx": 0.0,
                "ry": 0.0,
                "rz": 0.0,
                "bx": 0.0,
                "by": 0.0,
                "bz": 0.0,
            })

    bpy.context.scene["dottier_retarget_vars"]["lst_bones"] = new_lst_bones.copy()
    bpy.context.scene.dottier_retarget.lst_bones.clear()
    update_values = False
    update_bone_list_search = True
    
    for k in new_lst_bones:
        lst_bone = bpy.context.scene.dottier_retarget.lst_bones.add()
        index = len(bpy.context.scene.dottier_retarget.lst_bones)-1
        
        lst_bone.index = index         
        lst_bone.bone = new_lst_bones[index]["bone"]
        lst_bone.bcopy = new_lst_bones[index]["bcopy"]
        
    update_values = True
    update_all_bones()
    dottier_update_panel()
    
    return {'FINISHED'}

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy_extras.io_utils import ExportHelper
    
class dottier_save_config(bpy.types.Operator, ExportHelper):
    """Save the current configuration"""
    bl_idname = "dottier_retarget.save_config"
    bl_label = "Save Config"

    filename_ext = ".txt"
    filter_glob: bpy.props.StringProperty(default="*.txt", options={'HIDDEN'}, maxlen=255)

    def execute(self, context):
        return dottier_write_data(context, self.filepath)
    
class dottier_load_config(bpy.types.Operator, ImportHelper):
    """Load a previously saved configuration"""
    bl_idname = "dottier_retarget.load_config"
    bl_label = "Load Config"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".txt"
    filter_glob: bpy.props.StringProperty(default="*.txt", options={'HIDDEN'})

    def execute(self, context):
        return dottier_load_data(context, self.filepath)

class VIEW3D_UL_dottier_bone_ui_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            source = bpy.context.scene["dottier_retarget_vars"]["source"]
            target = bpy.context.scene["dottier_retarget_vars"]["target"]
            
            if not bpy.data.objects.get(target) or not bpy.data.objects.get(source): return
            
            trg_bones = [bone.name for bone in bpy.data.objects[target].pose.bones]
            src_bones = [bone.name for bone in bpy.data.objects[source].pose.bones]
            
            self.use_filter_show = True
            
            column = layout.row().column(align=True)
            row = column.row(align=True)
            
            if item.bone in trg_bones:
                row.prop(item, "bone")
            else:
                row.prop(item, "bone", icon ="ERROR")
            
            if item.bcopy in src_bones:
                row.prop(item, "bcopy")
            else:
                row.prop(item, "bcopy", icon ="ERROR")
            
    use_filter_error: bpy.props.BoolProperty(
        name="Missing Bone",
        default=False,
        options=set(),
        description="Filter by missing bones",
    )
    
    showing_count: bpy.props.IntProperty(
        name="Items being shown",
        default=0,
        options=set(),
    )
    
    def draw_filter(self, context, layout):
        column = layout.row().column(align=True)
        row = column.row(align=True)
        row.prop(self, "filter_name", text="Search", icon="BONE_DATA")
        row.prop(self, "use_filter_invert", icon="ARROW_LEFTRIGHT", icon_only=True)
        row.prop(self, "use_filter_error", icon="ERROR", icon_only=True)
    
    def filter_items(self, context, data, propname):
        global update_bone_list_search, clear_bone_list_search
        
        #Update filters on selection change  
        if clear_bone_list_search: clear_bone_list_search = False
        
        lst_bone_selection = bpy.context.scene["dottier_retarget_vars"]["lst_bone_selection"]
        
        if self.showing_count == 1 and len(lst_bone_selection) == 1 and lst_bone_selection[0] == self.filter_name:
            update_bone_list_search = True
          
        if update_bone_list_search: 
            update_bone_list_search = False      
            lst_bones = bpy.context.scene["dottier_retarget_vars"]["lst_bones"]
            lst_bone_names = [b_data["bone"] for b_data in lst_bones]
            
            bone_sel_missing = False
            
            for bone in lst_bone_selection:
                if not bone in lst_bone_names:
                    bone_sel_missing = True
                    self.use_filter_error = True
                    self.filter_name = ""
                    
            if not bone_sel_missing:
                if len(lst_bone_selection) == 1:
                    self.use_filter_error = False
                    self.filter_name = lst_bone_selection[0]
                else:
                    self.use_filter_error = False
                    self.filter_name = ""
        
        #Actual filterning code       
        source = bpy.context.scene["dottier_retarget_vars"]["source"]
        target = bpy.context.scene["dottier_retarget_vars"]["target"]
        
        filter_flags = [0] * len(data.lst_bones)
        visible = 1 << 30
        self.showing_count = 0
        
        if not bpy.data.objects.get(target) or not bpy.data.objects.get(source): return filter_flags, ()
        
        trg_bones = [bone.name for bone in bpy.data.objects[target].pose.bones]
        src_bones = [bone.name for bone in bpy.data.objects[source].pose.bones]
        
        for k, v in enumerate(data.lst_bones):
            if v.bone.lower().find(self.filter_name.lower()) != -1:
                if self.use_filter_error:                  
                    if not (v.bone in trg_bones) or not (v.bcopy in src_bones):
                        filter_flags[k] = visible
                        self.showing_count += 1
                else:
                    filter_flags[k] = visible
                    self.showing_count += 1
        
        return filter_flags, ()
    
classes = [
    dottier_save_config, 
    dottier_load_config, 
    dottier_retarget_lst_item, 
    dottier_retarget_props, 
    VIEW3D_PT_dottier_retarget_panel, 
    VIEW3D_OT_dottier_retarget_apply_view,
    VIEW3D_OT_dottier_retarget_refresh,
    VIEW3D_OT_dottier_retarget_move_exact,
    VIEW3D_OT_dottier_retarget_estimate_fraction,
    VIEW3D_OT_dottier_retarget_set_pose_as_base,
    VIEW3D_OT_dottier_retarget_clear_location_base,
    VIEW3D_OT_dottier_retarget_apply_keyframes,
    VIEW3D_OT_dottier_retarget_gen_list,
    VIEW3D_OT_dottier_retarget_clear_list,
    VIEW3D_UL_dottier_bone_ui_list
]
        
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dottier_retarget = bpy.props.PointerProperty(type= dottier_retarget_props)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.dottier_retarget  
    remove_handlers()

if __name__ == "__main__":
    register()
    