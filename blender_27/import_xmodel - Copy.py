# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

"""
Blender-CoD: Blender Add-On for Call of Duty modding
Version: alpha 3

Copyright (c) 2011 CoDEmanX, Flybynyt -- blender-cod@online.de

http://code.google.com/p/blender-cod/

NOTES
- Code is in early state of development and work in progress!
- Importing rigs from XMODEL_EXPORT v6 works, but the code is really messy.

TODO
- Implement full xmodel import

"""
#scale = 0.0253999862840074 for 1 bu = 1in
import os
import bpy
import mathutils
from mathutils import *
import math
from math import * 
#from mathutils.geometry import tesselate_polygon
#from io_utils import load_image, unpack_list, unpack_face_list

def parent_set(object, armature, bone):
    object.parent = armature
    object.parent_bone = bone
    object.parent_type = 'BONE'

def round_matrix_3x3(mat, precision=6):
    return Matrix(((round(mat[0][0],precision), round(mat[0][1],precision), round(mat[0][2],precision)),
                (round(mat[1][0],precision), round(mat[1][1],precision), round(mat[1][2],precision)),
                (round(mat[2][0],precision), round(mat[2][1],precision), round(mat[2][2],precision))))

#def getRoll(bone):
#    mat = bone.matrix_local.to_3x3()
#    quat = mat.to_quaternion()
#    if abs(quat.w) < 1e-4:
#        roll = pi
#    else:
#        roll = 2*atan(quat.y/quat.w)
#    return roll

#http://gamedev.stackexchange.com/questions/32529/calculating-the-correct-roll-from-a-bone-transform-matrix
def vec_roll_to_mat3(vec, roll):
    target = mathutils.Vector((0,1,0))
    nor = vec.normalized()
    axis = target.cross(nor)
    if axis.dot(axis) > 0.0000000001: # this seems to be the problem for some bones, no idea how to fix
        axis.normalize()
        theta = target.angle(nor)
        bMatrix = mathutils.Matrix.Rotation(theta, 3, axis)
    else:
        updown = 1 if target.dot(nor) > 0 else -1
        bMatrix = mathutils.Matrix.Scale(updown, 3)
    rMatrix = mathutils.Matrix.Rotation(roll, 3, nor)
    mat = rMatrix * bMatrix
    return mat

def mat3_to_vec_roll(mat):
    vec = mat.col[1]
    vecmat = vec_roll_to_mat3(mat.col[1], 0)
    vecmatinv = vecmat.inverted()
    rollmat = vecmatinv * mat
    roll = math.atan2(rollmat[0][2], rollmat[2][2])
    return vec, roll


def getRoll(matrix):
    mat = matrix.to_3x3()
    quat = mat.to_quaternion()
    if abs(quat.w) < 1e-4:
        roll = pi
    else:
        roll = 2*atan(quat.y/quat.w)
    return roll

def dist(pt1, pt2): 

   locx = pt2[0] - pt1[0] 
   locy = pt2[1] - pt1[1] 
   locz = pt2[2] - pt1[2] 

   distance = sqrt((locx)**2 + (locy)**2 + (locz)**2) 
   return distance

def openImage(path, filename): #without extension
    try:
        img = bpy.data.images[filename]
    except:
        try:
            img = bpy.data.images.load(filepath=(path+filename+".dds"))#bpy.ops.image.open(filepath=(path+filename+".dds"))
        except:
            try:
                img = bpy.data.images.load(filepath=(path+filename+".tga"))#bpy.ops.image.open(filepath=(path+filename+".tga"))
            except:
                return False
            else:
                img.name = filename
                return img
        else:
            img.name = filename
            return img
    else:
        return img
    
    
                
    

def load(self, context, filepath="", use_parents=True, use_connected_bones=False, use_local_location=False):
    #raise NameError("HAAALP")
    #bpy.types.Bone.pmat_x = bpy.props.FloatVectorProperty(name = "pMat.x", size = 4, default = (0.0, 0.0, 0.0, 0.0) )
    #bpy.types.Bone.pmat_y = bpy.props.FloatVectorProperty(name = "pMat.y", size = 4, default = (0.0, 0.0, 0.0, 0.0) )
    #bpy.types.Bone.pmat_z = bpy.props.FloatVectorProperty(name = "pMat.z", size = 4, default = (0.0, 0.0, 0.0, 0.0) )

    test_0 = []
    test_1 = []
    test_2 = []
    test_3 = []

    state = 0

    # placeholders
    vec0 = Vector((0.0, 0.0, 0.0))
    mat0 = Matrix(((0.0, 0.0, 0.0),(0.0, 0.0, 0.0),(0.0, 0.0, 0.0)))

    numbones = 0
    numbones_i = 0
    bone_i = 0
    bone_table = []
    bone_name_table = []
    numverts = 0
    vert_i = 0
    vert_table = [] # allocate table? [0]*numverts
    #vert_group_table = [] # see http://wiki.blender.org/index.php/Dev:2.5/Py/Scripts/Cookbook/Code_snippets/Armatures#Rigged_mesh for details
    face_i = 0
    face_tmp = []
    face_table = []
    bones_influencing_num = 0
    bones_influencing_i = 0
    numfaces = 0
    uv_table = []#2014
    uv_img_id_table = []
    mat_img_table = []
    mat_table = []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    try:
        bpy.context.scene.objects.active.pose.bones["tag_weapon"]
    except:
        arm_is_active = 0
    else:
        arm_is_active = 1
        arm_ob = bpy.context.scene.objects.active
        bpy.ops.object.mode_set(mode='EDIT')
        tag_weapon_mat = arm_ob.pose.bones["tag_weapon"].matrix.copy()
        #tag_weapon_mat = arm_ob.data.edit_bones["tag_weapon"].matrix.copy()
        bpy.ops.object.mode_set(mode='OBJECT')
        #tag_weapon = arm_ob.["tag_weapon"]

    bpy.ops.object.select_all(False)#possibly unneeded

    print("\nImporting %s" % filepath)

    try:
        file = open(filepath, "r")
    except IOError:
        return "Could not open file for reading:\n%s" % filepath

    for line in file:
        line = line.strip()
        line_split = line.split()

        # Skip empty and comment lines
        if not line or line[0] == "/":
            continue

        elif state == 0 and line_split[0] == "MODEL":
            state = 1

        elif state == 1 and line_split[0] == "VERSION":
            if line_split[1] != "6":
                error_string = "Unsupported version: %s" % line_split[1]
                print("\n%s" % error_string)
                return error_string
            state = 2

        elif state == 2 and line_split[0] == "NUMBONES":
            numbones = int(line_split[1])
            vert_group_table = {} #SED
            for i in range(numbones):
                vert_group_table[i] = []
            state = 3

        elif state == 3 and line_split[0] == "BONE":
            if numbones_i != int(line_split[1]):
                error_string = "Unexpected bone number: %s (expected %i)" % (line_split[1], numbones_i)
                print("\n%s" % error_string)
                return error_string
            bone_table.append((line_split[3][1:-1], int(line_split[2]), vec0, mat0))

            bone_name_table.append(line_split[3][1:-1])#SED
            #vert_group_table = {} #SED
            #for i in range(numbones):
            #    vert_group_table[i] = []
            test_0.append(line_split[3][1:-1])
            test_1.append(int(line_split[2]))
            if numbones_i >= numbones-1:
                state = 4
            else:
                numbones_i += 1

        elif state == 4 and line_split[0] == "BONE":
            bone_num = int(line_split[1])
            if bone_i != bone_num:
                error_string = "Unexpected bone number: %s (expected %i)" % (line_split[1], bone_i)
                print("\n%s" % error_string)
                return error_string
            state = 5

        elif state == 5 and line_split[0] == "OFFSET":
            # remove commas - line_split[#][:-1] would also work, but isn't as save
            line_split = line.replace(",", "").split()

            # should we check for len(line_split) to ensure we got enough elements?
            # Note: we can't assign a new vector to tuple object, we need to change each value

            bone_table[bone_i][2].xyz = Vector((float(line_split[1]), float(line_split[2]), float(line_split[3])))
            #print("\nPROBLEMATIC: %s" % bone_table[bone_i][2])
            #NO ERROR HERE, but for some reason the whole table will contain the same vectors
            #bone_table[bone_i][2][0] = float(line_split[1])
            #bone_table[bone_i][2][1] = float(line_split[2])
            #bone_table[bone_i][2][2] = float(line_split[3])
            test_2.append(Vector((float(line_split[1]),float(line_split[2]),float(line_split[3]))))

            state = 6

        elif state == 6 and line_split[0] == "SCALE":
            # always 1.000000?! no processing so far...
            state = 7

        elif state == 7 and line_split[0] == "X":
            line_split = line.replace(",", "").split()
            bone_table[bone_i][3][0] = Vector((float(line_split[1]), float(line_split[2]), float(line_split[3])))

            """ Use something like this:
            bone.align_roll(targetmatrix[2])
            roll = roll%360 #nicer to have it 0-359.99...
            """
            m_col = []
            m_col.append((float(line_split[1]), float(line_split[2]), float(line_split[3])))
            
            state = 8

        elif state == 8 and line_split[0] == "Y":
            line_split = line.replace(",", "").split()
            bone_table[bone_i][3][1] = Vector((float(line_split[1]), float(line_split[2]), float(line_split[3])))
            
            m_col.append((float(line_split[1]), float(line_split[2]), float(line_split[3])))

            state = 9

        elif state == 9 and line_split[0] == "Z":
            line_split = line.replace(",", "").split()
            vec_roll = Vector((float(line_split[1]), float(line_split[2]), float(line_split[3])))
            ##bone_table[bone_i][3][2] = vec_roll
            #print("bone_table: %s" % bone_table[bone_i][3][2])
            
            m_col.append((float(line_split[1]), float(line_split[2]), float(line_split[3])))

            #test_3.append(Vector(vec_roll))
            
            test_3.append(m_col)
            #print("test_3: %s\n\n" % test_3[:])

            if bone_i >= numbones-1:
                state = 10
            else:
                #print("\n---> Increasing bone: %3i" % bone_i)
                #print("\t" + str(bone_table[bone_i][3]))
                #print("\t" + str(bone_table[bone_i][0]))
                bone_i += 1
                state = 4

        elif state == 10 and line_split[0] == "NUMVERTS":
            numverts = int(line_split[1])
            state = 11

        elif state == 11 and line_split[0] == "VERT":
            vert_num = int(line_split[1])
            if vert_i != vert_num:
                error_string = "Unexpected vertex number: %s (expected %i)" % (line_split[1], vert_i)
                print("\n%s" % error_string)
                return error_string
            vert_i += 1
            state = 12

        elif state == 12 and line_split[0] == "OFFSET":
            line_split = line.replace(",", "").split()
            vert_table.append(Vector((float(line_split[1]), float(line_split[2]), float(line_split[3]))))
            state = 13

        elif state == 13 and line_split[0] == "BONES":
            # TODO: process
            bones_influencing_num = int(line_split[1])
            bones_influencing_i = 0
            state= 14

        elif state == 14 and line_split[0] == "BONE":
            # TODO: add bones to vert_table
            #vgroups = {}
            #vgroups['Base'] = [
            #(0, 1.0), (1, 1.0), (2, 1.0), (3, 1.0),
            #(4, 0.5), (5, 0.5), (6, 0.5), (7, 0.5)]
            #vert_group_table[bone_name_table[line_split[1]]].append((vert_i, line_split[2]))#SED ADDED THIS
            vert_group_table[int(line_split[1])].append((vert_i-1, float(line_split[2]))) #SED ADDED THIS
            
            if bones_influencing_i >= (bones_influencing_num - 1):
                if vert_i >= numverts:
                    state = 15
                else:
                    state = 11
            else:
                bones_influencing_i += 1
                #state = 14

        elif state == 15 and line_split[0] == "NUMFACES":
            numfaces = int(line_split[1])
            state = 16
            
        elif state == 16: #and line_split[0] == "TRI":
            mat_id = int(line_split[2])#starts at 0
            for i in range((mat_id+1) - (len(mat_table))):
                mat_table.append([])
            uv_img_id_table.append(mat_id)
            uv_tmp = []
            face_tmp = []
            state = 17
            
        elif (state == 17 or state == 21 or state == 25) and line_split[0] == "VERT":
            #print("face_tmp length: %i" % len(face_tmp))
            mat_table[mat_id].append(int(line_split[1]))
            face_tmp.append(int(line_split[1]))
            state += 1
        
        elif (state == 18 or state == 22 or state == 26) and line_split[0] == "NORMAL":
            state += 1
            
        elif (state == 19 or state == 23 or state == 27) and line_split[0] == "COLOR":
            state += 1
            
        elif (state == 20 or state == 24 or state == 28) and line_split[0] == "UV":
            uv_tmp.append((float(line_split[2]),1.0-float(line_split[3])))
            if(state == 28): #swap the first and third entries
                tmp = uv_tmp[0]
                uv_tmp[0] = uv_tmp[2]
                uv_tmp[2] = tmp
            state += 1
        
        elif state == 29:#Most TRI

            #print("Adding face: %s\n%i faces so far (of %i)\n" % (str(face_tmp), face_i, numfaces))
            v0 = face_tmp[0]#2014
            face_tmp[0] = face_tmp[2]#2014
            face_tmp[2] = v0#2014
            face_table.append(face_tmp)
            #uv_table[uv_map_id].append(uv_tmp)
            uv_table.append(uv_tmp)

            #prepare for next tri
            if(line_split[0] == "TRI"):
                uv_map_id = int(line_split[2])

                mat_id = int(line_split[2])#starts at 0
                for i in range((mat_id+1) - (len(mat_table))):
                    mat_table.append([])
                uv_img_id_table.append(mat_id)
                #for i in range((uv_map_id+1) - (len(uv_table))):
                #    uv_table.append([])

                uv_tmp = []
            
            if (face_i >= numfaces - 1):
                state = 30
            else:
                face_i += 1
                face_tmp = []
                state = 17

        elif state > 15 and state < 30 and line_split[0] == "NUMOBJECTS":
            print("Bad numfaces, terminated loop\n")
            state = 30
            
        elif state == 30:
            print("Adding mesh!")
            
            me = bpy.data.meshes.new("pymesh")
            me.from_pydata(vert_table, [], face_table)
            me.update()
            mesh_ob = bpy.data.objects.new("Py-Mesh", me)            
            bpy.context.scene.objects.link(mesh_ob)

            bpy.context.scene.objects.active = mesh_ob
            #If smoothing is set to true
            mesh_ob.select = True
            bpy.ops.object.shade_smooth()

            mesh = mesh_ob.data
            #if UV is true

            uvtex = bpy.ops.mesh.uv_texture_add()
            uv = mesh.uv_layers[0].data

            tmp = 0

            #for i in range(len(uv_table)-1): #this -1 was causing the last tri to be imported as default
            for i in range(len(uv_table)):
                uv[tmp].uv = uv_table[i][0]
                tmp+=1
                uv[tmp].uv = uv_table[i][1]
                tmp+=1
                uv[tmp].uv = uv_table[i][2]
                tmp+=1

                #print(uv[tmp].uv)



            state = 31

        elif state == 31 and line_split[0] == "MATERIAL":
            mat_vgroup = mesh_ob.vertex_groups.new("Material")
            mat_vgroup.add(mat_table[int(line_split[1])],1.0, 'ADD')
            bpy.ops.object.vertex_group_set_active(group='Material')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.vertex_group_select()
            bpy.ops.object.material_slot_add()
            mesh_ob.material_slots[int(line_split[1])].material = bpy.data.materials.new(line_split[2][1:-1])
            bpy.ops.object.material_slot_assign()

            #opens normal map first so that the color map overrides it
            failed = 0

            model_path = os.path.dirname(filepath)

            try:
                cmap = line_split[4][7:-4]
            except:
                do="nothing" #no color map found
            else:
                if not openImage((model_path + "\\..\\_images\\"), cmap):
                    if not openImage((model_path + "\\_images\\"), cmap):
                        if not openImage((model_path + "\\images\\"), cmap):
                            print("Could not open: ", cmap)
                            failed = 1

            if not failed:
                mat_img_table.append(cmap)
                tex = mesh_ob.material_slots[int(line_split[1])].material.texture_slots.add()
                tex.texture = bpy.data.textures.new(cmap+"_tex",'IMAGE')
                tex.texture_coords = 'UV'
                tex.uv_layer = 'UVMap'
                tex.texture.image = bpy.data.images[cmap]

            try:
                nmap = line_split[5][7:-5]
            except:
                do="nothing" #no color map found
            else:
                if not openImage((model_path + "\\..\\_images\\"), nmap):
                    if not openImage((model_path + "\\_images\\"), nmap):
                        if not openImage((model_path + "\\images\\"), nmap):
                            print("Could not open: ", cmap)

            tex = mesh_ob.material_slots[int(line_split[1])].material.texture_slots.add()
            tex.texture_coords = 'UV'
            tex.uv_layer = 'UVMap'    
            
                            
            
            bpy.ops.object.mode_set(mode='OBJECT')
            mesh_ob.vertex_groups.remove(mesh_ob.vertex_groups["Material"])
            #Get material names - should probably use try
            
            #print(line_split[4][7:]) #color
            #print(line_split[5][7:-1]) #normal
            #state = 32 - temp fix in order to get all of the materials

        else: #elif state == 16:
            #UNDONE
            #print("eh? state is %i line: %s" % (state, line))
            foo = "bar"
            pass


    #Apply The UV Images for Textured Viewmode
    i = 0
    for img_id in uv_img_id_table:
        try:
            bpy.context.scene.objects.active.data.uv_textures[0].data[i].image = bpy.data.images[mat_img_table[img_id]]
        except:
            do="nothing"
        else:
            i += 1

    name = "Armature"
    origin = Vector((0,0,0))
    boneTable = bone_table

    # If no context object, an object was deleted and mode is 'OBJECT' for sure
    if context.object: #and context.mode is not 'OBJECT':

        # Change mode, 'cause modes like POSE will lead to incorrect context poll
        bpy.ops.object.mode_set(mode='OBJECT')

    # Create armature and object
    bpy.ops.object.add(
        type='ARMATURE', 
        enter_editmode=True,
        location=origin)
    ob = bpy.context.object
    ob.show_x_ray = True
    ob.name = name
    amt = ob.data
    amt.name = name + "Amt"
    #amt.show_axes = True

    # Create bones
    bpy.ops.object.mode_set(mode='EDIT')
    #for (bname, pname, vector, matrix) in boneTable:
    #i = 0

    bones_i = -1#
    #print(test_0)
    for (t0, t1, t2, t3) in zip(test_0, test_1, test_2, test_3):

        t0 = t0.lower()#SED
        t3 = Matrix(t3).transposed()

        bone = amt.edit_bones.new(t0)
        #print(t0)
        bone.use_local_location = False #SED
        
        """bone.head = (0,0,0)
        bone.tail = (0,1,0)#t3[1]
        bone.transform(t3)
        bone.translate(t2)"""
        #just in case
        axis, roll = mat3_to_vec_roll(t3)
        bone.head = t2
        bone.tail = t2 + axis
        #print(t2)
        #print(t2+axis)
        bone.roll = roll
        
        #bone.roll = 0#getRoll(t3)#TEMPORARY (2014) SED
        #bone.tail = (0,1,0)
        if t1 != -1:
            parent = amt.edit_bones[t1]
            if(use_parents == True):
                bone.parent = parent

        bones_i += 1 #probably not needed
        
        object_world_mat = Matrix(t3).to_4x4()
        object_world_mat[0][3] = t2[0]
        object_world_mat[1][3] = t2[1]
        object_world_mat[2][3] = t2[2]

    #Create Vertex Groups
    for name, vgroup in vert_group_table.items():
        grp = mesh_ob.vertex_groups.new(bone_name_table[name].lower())
        for (v, w) in vgroup:
            grp.add([v], w, 'REPLACE')
    #Add Armature Modifier
    mod = mesh_ob.modifiers.new('Armature Rig', 'ARMATURE')
    mod.object = ob
    mod.use_bone_envelopes = False
    mod.use_vertex_groups = True

    amt.draw_type = "STICK" #draw bones as sticks
    bpy.ops.object.mode_set(mode='POSE') #enter pose mode

    ob = bpy.context.object  
    
    bpy.types.PoseBone.base_mat = bpy.props.FloatVectorProperty(name="Base Rotation Matrix (from File)", subtype="MATRIX", size=16)#SED
    bpy.types.PoseBone.rest_mat = bpy.props.FloatVectorProperty(name="Rest Rotation Matrix (from Blender)", subtype="MATRIX", size=16)#SED    
    
    for (t0, t1, t2, t3) in zip(test_0, test_1, test_2, test_3): #SED
        ob.pose.bones.data.bones[t0.lower()].base_mat[0] = Matrix(t3).to_4x4()[0]
        ob.pose.bones.data.bones[t0.lower()].base_mat[1] = Matrix(t3).to_4x4()[1]
        ob.pose.bones.data.bones[t0.lower()].base_mat[2] = Matrix(t3).to_4x4()[2]

        ob.pose.bones.data.bones[t0.lower()].rest_mat[0] = ob.pose.bones.data.bones[t0.lower()].matrix[0]
        ob.pose.bones.data.bones[t0.lower()].rest_mat[1] = ob.pose.bones.data.bones[t0.lower()].matrix[1]
        ob.pose.bones.data.bones[t0.lower()].rest_mat[2] = ob.pose.bones.data.bones[t0.lower()].matrix[2]
        ob.pose.bones.data.bones[t0.lower()].rest_mat[3] = ob.pose.bones.data.bones[t0.lower()].matrix[3]


    #DEVSTUFF
    try:
        ob.pose.bones['j_gun'].matrix
    except:
        do="nothing"
    else:
        if arm_is_active:
            tvec =  -ob.pose.bones['j_gun'].matrix.translation
            #bpy.ops.object.mode_set(mode='EDIT')
        
            ob.matrix_local = tag_weapon_mat
            mesh_ob.matrix_local = tag_weapon_mat
            parent_set(ob, arm_ob, 'tag_weapon')
            parent_set(mesh_ob, arm_ob, 'tag_weapon')
            ob.matrix_local.translation = tvec#Vector((0,-1,0))
            mesh_ob.matrix_local.translation = tvec#Vector((0,-1,0))
            
           # print(tag_weapon_mat)
            #print(ob.pose.bones['j_gun'].matrix)
        #ob.parent = arm_ob.pose.bones["tag_weapon"]
        #mesh_ob.parent - arm_ob.pose.bones["tag_weapon"]

    
    file.close()

