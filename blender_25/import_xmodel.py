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

import os
import bpy
from mathutils import *
#from mathutils.geometry import tesselate_polygon
#from io_utils import load_image, unpack_list, unpack_face_list

def round_matrix_3x3(mat, precision=6):
    return Matrix(((round(mat[0][0],precision), round(mat[0][1],precision), round(mat[0][2],precision)),
                (round(mat[1][0],precision), round(mat[1][1],precision), round(mat[1][2],precision)),
                (round(mat[2][0],precision), round(mat[2][1],precision), round(mat[2][2],precision))))

test_0 = []
test_1 = []
test_2 = []
test_3 = []


def load(self, context, filepath=""):
    
    global test_0
    global test_1
    global test_2
    global test_3

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
    numverts = 0
    vert_i = 0
    vert_table = [] # allocate table? [0]*numverts
    bones_influencing_num = 0
    bones_influencing_i = 0
    numfaces = 0
    

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
            state = 3
            
        elif state == 3 and line_split[0] == "BONE":
            if numbones_i != int(line_split[1]):
                error_string = "Unexpected bone number: %s (expected %i)" % (line_split[1], numbones_i)
                print("\n%s" % error_string)
                return error_string
            bone_table.append((line_split[3][1:-1], int(line_split[2]), vec0, mat0))
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
            state = 8
            
        elif state == 8 and line_split[0] == "Y":
            line_split = line.replace(",", "").split()
            bone_table[bone_i][3][1] = Vector((float(line_split[1]), float(line_split[2]), float(line_split[3])))
            state = 9
            
        elif state == 9 and line_split[0] == "Z":
            line_split = line.replace(",", "").split()
            bone_table[bone_i][3][2] = Vector((float(line_split[1]), float(line_split[2]), float(line_split[3])))
            test_3.append(bone_table[bone_i][3][2])
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
            state= 14
            
        elif state == 14 and line_split[0] == "BONE":
            # TODO: add bones to vert_table
            if bones_influencing_i >= bones_influencing_num-1:
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
            
        else: #elif state == 16:
            #UNDONE
            pass
            
        #print("\nCurrent state=" + str(state) + "\nLine:" + line)
    
    #print("\n" + str(list(bone_table)) + "\n\n" + str(list(vert_table)))
    

    createRig(context, "Armature", Vector((0,0,0)), bone_table)
    
    #print("\n\n" + str(len(obj.data.bones)))

    file.close()


def createRig(context, name, origin, boneTable):
    
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
    i = 0
    for bt in test_0:
        bone = amt.edit_bones.new(test_0[i])
        if test_1[i] != -1:
            parent = amt.edit_bones[test_1[i]]
            bone.parent = parent
            bone.head = parent.tail
            bone.use_connect = True
            bone.align_roll(test_3[i])
            #(trans, rot, scale) = parent.matrix.decompose()
        else:
            bone.head = (0,0,0)
            rot = Matrix.Translation((0,0,0))	# identity matrix
            bone.use_connect = False
        #bone.tail = Vector(vector) * rot + bone.head
        bone.tail = test_2[i]
        #bone.tail = boneTable[i][2] #passing boneTable as parameter seems to break it :(
        i += 1
        
    #outfile.write("\n%s" % str(boneTable))

    bpy.ops.object.mode_set(mode='OBJECT')
    return ob
