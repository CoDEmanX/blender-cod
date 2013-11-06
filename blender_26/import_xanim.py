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
Version: alpha 4

Copyright (c) 2013 CoDEmanX, SE2Dev, Flybynyt -- blender-cod@online.de

http://code.google.com/p/blender-cod/


Note:

- xmodel and rest_anim have same offset values, but different rotation matricies
- imported xmodel bones have a different rotation matrix than the file
- xanim rest files have this broken matrix, imported xanims also have the same broken matrix

"""


import bpy
from mathutils import *
import math

#def load(self, context, **keywords):filepath=""

def load(self, context, filepath=""):
	scene = bpy.context.scene #bpy.data.scenes["Scene"].render.fps
	ob = bpy.context.object
	amt = ob.data
	
	bpy.ops.object.mode_set(mode='POSE') 
	
	#print(bones.keys())
	#for i, v in enumerate(bones.keys()):
	#	print( i, v)

	#print(bones[1])

	filetype = ""
	version = 0
	numbones = 0
	bone_i = 0
	#bone_data_table = [] #bone[bone#][frame][(offset, scale, [x,x,x],[y,y,y],[z,z,z])] # now inited after the framenumber is found
	bone_name_table = []
	framerate = 0
	numframes = 0
	#frame_i = 0
	#currentframe = 0
	#currentbone = 0
	#firstframe = -1 #might work  - might not

	#print(bpy.context.object.pose.bones[0])

	#return {'FINISHED'}

	state = 0

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

		elif state == 0 and line_split[0] == "ANIMATION":
			filetype = line_split[0]
			state = 1

		elif state == 1 and line_split[0] == "VERSION":
			version = line_split[1]
			state = 2

		elif state == 2 and line_split[0] == "NUMPARTS":
			numbones = int(line_split[1])
			state = 3

		elif state == 3 and line_split[0] == "PART":			
			bone_name_table.append(line_split[2][1:-1])
			if bone_i >= numbones-1:
				bone_i = 0
				state = 4 # was 4
			else:
				#amt.bones[bone_i].use_local_location = False
				bone_i += 1

		elif state == 4 and line_split[0] == "FRAMERATE":
			#framerate = int(line_split[1])
			scene.render.fps = int(line_split[1])
			state = 5

		elif state == 5 and line_split[0] == "NUMFRAMES":
			numframes = int(line_split[1])
			#init bone table ex. bone[0] = bone 0   : bone[0].offset etc
			state = 6

		elif state == 6 and line_split[0] == "FRAME":
			currentframe = int(line_split[1])
			#print(currentframe)
			try:
				firstframe
			except:
				firstframe = currentframe #might be able to remove with some tweaking
				scene.frame_start = firstframe
				scene.frame_end = scene.frame_start + numframes - 1	
			state = 7
		
		elif state == 7 and line_split[0] == "PART":
			bone_i = int(line_split[1])
			state = 8
	
		elif state == 8 and line_split[0] == "OFFSET":
			offset = Vector((float(line_split[1]),float(line_split[2]),float(line_split[3])))
			state = 9
	
		elif state == 9 and line_split[0] == "SCALE": #can probably be ignored - supposedly always == 1
			scale = [float(line_split[1]),float(line_split[2]),float(line_split[3])]
			state = 10
	
		elif (state == 9 or state == 10) and line_split[0] == "X": #scale doesnt always come after offset
			m_col = []
			m_col.append(Vector((float(line_split[1]), float(line_split[2]), float(line_split[3]))))
			state = 11
	
		elif state == 11 and line_split[0] == "Y":
			m_col.append(Vector((float(line_split[1]), float(line_split[2]), float(line_split[3]))))
			state = 12
	
		elif state == 12 and line_split[0] == "Z":
			m_col.append(Vector((float(line_split[1]), float(line_split[2]), float(line_split[3]))))
			
			rotMat = Matrix(m_col) #BoneMatrix.to_3x3
			#bone_name_table[bone_i]
			try:
				ob.pose.bones.data.bones[bone_name_table[bone_i].lower()]
			except:
				print("Bone Not Found - ", bone_name_table[bone_i].lower())
				#print("Bone Not Found - Ignoring Bone:", bone_name_table[bone_i].lower())
				#do nothing
			else:
				mw = ob.pose.bones.data.bones[bone_name_table[bone_i].lower()].bone.matrix.copy() 
				matrix_world = ob.pose.bones.data.bones[bone_name_table[bone_i].lower()].bone.matrix.copy()
				ob.pose.bones.data.bones[bone_name_table[bone_i].lower()].matrix = ob.matrix_world.inverted()*(Matrix.Translation(offset)+mw.to_3x3().to_4x4())
			
				ob.pose.bones.data.bones[bone_name_table[bone_i].lower()].keyframe_insert(data_path = "location",index = -1,frame = currentframe)
	
				ob.pose.bones.data.bones[bone_name_table[bone_i].lower()].matrix = rotMat.to_4x4() #was .matrix = (rotMat.to_4x4())
				#print(rotMat, " ", bone_name_table[bone_i])
				ob.pose.bones.data.bones[bone_name_table[bone_i].lower()].keyframe_insert("rotation_euler",index = -1,frame = currentframe)#was rotation_quaternion - COD most likely uses euler

			
			
				
			
	
			if bone_i >= numbones-1:
				bone_i = 0
				state = 6
			else:
				state = 7
		
	#for i in range(10):
	#	ob.pose.bones.data.bones['tag_origin'].location += Vector((1,1,1))
	#	ob.pose.bones.data.bones['tag_origin'].keyframe_insert(data_path = "location",index = -1,frame = i, group="bone_a")
	
	file.close()
	
	#print(framerate)
	#print(numframes)
	#print(firstframe)

	return {'FINISHED'}