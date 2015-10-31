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

"""
Blender-CoD: Blender Add-On for Call of Duty modding
Version: alpha 4

Copyright (c) 2015 SE2Dev, CoDEmanX, Flybynyt -- blender-cod@online.de

https://github.com/CoDEmanX/blender-cod

"""

import bpy
from mathutils import *
import math
import time
import os

#def load(self, context, **keywords):filepath=""

def movebone(bone, matrix): #moves a bone independent of its children
		pmat = bone.matrix.copy()
		dmat = matrix * pmat.inverted()
		cmats = {}
		for child in bone.children:
				cmats[child.name] =  child.matrix.copy()
		bone.matrix = matrix
		for child in bone.children:
				child.matrix =   dmat.inverted() * cmats[child.name] 
		return {'FINISHED'}

def GetActionName(filepath):
		str = os.path.splitext(filepath)[0]
		return os.path.basename(str)

def load(self, context,  filepath=""):
		ob = bpy.context.object
		path = os.path.dirname(filepath) + "\\"

		try:
			ob.animation_data.action
		except:
			ob.animation_data_create()

		for f in self.files:
			load_anim(self, context, path + f.name)
		
		return {'FINISHED'}

def load_anim(self, context, filepath=""):
		time_start = time.time()
		scene = bpy.context.scene #bpy.data.scenes["Scene"].render.fps
		ob = bpy.context.object
		
		amt = ob.data
		
		bpy.ops.object.mode_set(mode='POSE') 
		
		filetype = ""
		version = 0
		numbones = 0
		bone_i = 0
		bone_name_table = []
		framerate = 0
		numframes = 0
		bone_name = ""
		has_neg_tag_origin = 0
		is_view_anim = 1 #set this to 0 later

		state = 0

		print("\nImporting %s" % filepath)

		ob.animation_data.action = bpy.data.actions.new(GetActionName(filepath))
		ob.animation_data.action.use_fake_user = True

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

				elif state == 1 and line_split[0] == "TOM_VERSION":
						version = line_split[1]
						state = 2
				elif state == 1 and line_split[0] == "VERSION":
						load_xanim(self, context, file)
						return {"FINISHED"}

				elif state == 2 and line_split[0] == "NUMPARTS":
						numbones = int(line_split[1])
						state = 3

				elif state == 3 and line_split[0] == "PART":					
						bone_name_table.append(line_split[2][1:-1])
						if( int(line_split[1]) == -1 and line_split[2][1:-1] == "tag_origin"):
								has_neg_tag_origin = 1
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

				elif not(state == 14) and line_split[0] == "FRAME":
						currentframe = int(line_split[1])

						try:
								firstframe
						except:
								firstframe = currentframe #might be able to remove with some tweaking
								scene.frame_start = firstframe
								scene.frame_end = scene.frame_start + numframes - 1

								for bone_name_i in bone_name_table: #This for loop is for adding a keyframe for everybone at its default rotation and location
																		#so that bones that are initially defined on the next frame still start correctly
										try:
												ob.pose.bones.data.bones[bone_name_i]
										except:
												print("Bone Not Found - Ignoring Bone:", bone_name) #at least it only does this one time here
										else:
												cbone = ob.pose.bones.data.bones[bone_name_i]
												cbone.keyframe_insert(data_path = "location",index = -1,frame = currentframe)
												cbone.keyframe_insert("rotation_quaternion",index = -1,frame = currentframe)
						state = 7
				
				elif line_split[0] == "PART":#state == 7 and line_split[0] == "PART":
						bone_i = int(line_split[1])
						if bone_i == -1:
								bone_name = "tag_origin"
						else:
								bone_name = bone_name_table[bone_i+has_neg_tag_origin].lower()

						state = 8
		
				elif state == 8 and line_split[0] == "OFFSET":
						offset = Vector((float(line_split[1]),float(line_split[2]),float(line_split[3])))

						try:
								ob.pose.bones.data.bones[bone_name]
						except:
								do="nothing"
								#print("Bone Not Found - ", bone_name)  more annoying than anything
								#print("Bone Not Found - Ignoring Bone:", bone_name)
								#do nothing
						else:
								cbone = ob.pose.bones.data.bones[bone_name]

								if (is_view_anim == True and any("tag_torso" in bone.name for bone in cbone.parent_recursive)): #used for Viewmodels
										
										#offset /= 2.54#removing this makes the bones seem relatively normal
									   
										try:
												cbone.parent.matrix.translation
										except:
												cbone.matrix_basis.translation = offset
										else:
												cbone.matrix.translation = (cbone.parent.matrix*offset)


								else:
										cbone.matrix_basis.translation = offset

								cbone.keyframe_insert(data_path = "location",index = -1,frame = currentframe)
								
						state = 9
		
				elif state == 9 and line_split[0] == "SCALE": #can probably be ignored - supposedly always == 1
						scale = [float(line_split[1]),float(line_split[2]),float(line_split[3])]
						state = 10
		
				elif (state == 9 or state == 10 or state == 8) and line_split[0] == "X": #scale doesnt always come after offset
						m_col = []
						m_col.append(Vector((float(line_split[1]), float(line_split[2]), float(line_split[3]))))
						state = 11
		
				elif state == 11 and line_split[0] == "Y":
						m_col.append(Vector((float(line_split[1]), float(line_split[2]), float(line_split[3]))))
						state = 12
		
				elif state == 12 and line_split[0] == "Z":
						m_col.append(Vector((float(line_split[1]), float(line_split[2]), float(line_split[3]))))
						
						rotMat = Matrix(m_col).to_4x4()

						try:
								ob.pose.bones.data.bones[bone_name]
						except:
								do="nothing"
								#print("Bone Not Found - ", bone_name) # more annoying than anything
								#print("Bone Not Found - Ignoring Bone:", bone_name)
								#do nothing
						else:
								cbone = ob.pose.bones.data.bones[bone_name]

								cbone.matrix_basis.identity() #reset bone to its base position
								try:
										cbone.parent.matrix
								except:
										cbone.matrix_basis.identity()
										tmp_mat = ( rotMat.to_3x3()).to_4x4()
								else:
										tmp_mat = ( cbone.parent.matrix.to_3x3() * rotMat.to_3x3()).to_4x4()#cbone.matrix.to_3x3() *
						
								cbone.scale = Vector((1,1,1))
								cbone.matrix = tmp_mat
								
								cbone.keyframe_insert("rotation_quaternion",index = -1,frame = currentframe)
						
						if bone_i+has_neg_tag_origin >= numbones-1:
								bone_i = 0
								state = 6
						else:
								state = 7
				elif line_split[0] == "NUMTRACKS":
						#ignore the number after NUMTRACKS as it isnt really needed
						bpy.ops.object.mode_set(mode='OBJECT')
						state = 13
				elif state == 13 and line_split[0] == "NAME":
						nt_name = line_split[1]
						#print(nt_name)
						state = 14
				elif state == 14 and line_split[0] == "FRAME":
						notetrack = bpy.context.scene.timeline_markers.new(nt_name)
						notetrack.frame = int(line_split[1])
		
						state = 13

		bpy.context.scene.update()
		file.close()

		bpy.ops.object.mode_set(mode='POSE')

		bpy.context.scene.frame_current = firstframe

		print("imported in: " + str(time.time()-time_start) + " seconds")
		return {'FINISHED'}


def load_xanim(self, context, file):
		time_start = time.time()
		scene = bpy.context.scene #bpy.data.scenes["Scene"].render.fps
		ob = bpy.context.object
		amt = ob.data
		
		bpy.ops.object.mode_set(mode='POSE') 
		

		filetype = ""
		version = 0
		numbones = 0
		bone_i = 0
		bone_name_table = []
		framerate = 0
		numframes = 0
   
		state = 2 #the first two parts were parsed by the previous function

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
						bpy.context.scene.frame_current = currentframe
						bpy.context.scene.update()
						
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
						
						rotMat = Matrix(m_col).transposed().to_4x4()
										 
						try:
								ob.pose.bones[bone_name_table[bone_i].lower()]
						except:
								#print("Bone Not Found - ", bone_name_table[bone_i].lower())
								#print("Bone Not Found - Ignoring Bone:", bone_name_table[bone_i].lower())
								do="nothing"
						else:
								cbone = ob.pose.bones[bone_name_table[bone_i].lower()] #Saves alot of space typing

								rotMat.translation = offset								
								movebone(cbone,rotMat)
								bpy.context.scene.update()
								cbone.keyframe_insert("rotation_quaternion",index = -1,frame = currentframe)#was rotation_quaternion - COD most likely uses euler
								cbone.keyframe_insert(data_path = "location",index = -1,frame = currentframe)
								

						if bone_i >= numbones-1:
								bone_i = 0
								state = 6
						else:
								state = 7
				elif line_split[0] == "NUMKEYS":
						#ignore the number after NUMKEYS as it isnt really needed
						bpy.ops.object.mode_set(mode='OBJECT')
						state = 13
				elif state == 13 and line_split[0] == "FRAME":
						nt_name = line_split[2]
						notetrack = bpy.context.scene.timeline_markers.new(nt_name)
						notetrack.frame = int(line_split[1])#bpy.context.scene.timeline_markers[nt_name].frame = int(line_split[1])
		
						state = 13
		
		file.close()
		
		bpy.context.scene.frame_current = firstframe
		bpy.context.scene.update() #probably updates teh scene

		bpy.ops.object.mode_set(mode='POSE')
		
		print("imported in: " + str(time.time()-time_start) + " seconds")
		return {'FINISHED'}
