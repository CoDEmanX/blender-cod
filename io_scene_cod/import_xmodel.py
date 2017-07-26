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

NOTES
- Code is in early state of development and work in progress!
- Importing rigs from XMODEL_EXPORT v6 works, but the code is really messy.

TODO
- Implement full xmodel import

"""

import os
import bpy
from mathutils import *
import math
#from mathutils.geometry import tesselate_polygon
#from io_utils import load_image, unpack_list, unpack_face_list

def load(self, context, filepath=""):
	#DEBUG (WILL BE IN THE GUI LATER
	use_parents = True
	split_mode = False #Split Into Separate Objects
	

	state = 0

	version = 0

	numverts = 0
	numbones = 0
	
	vertTable = []
	boneTable = []

	#objTable = []
	#meshTable = []
	
	#name = "name"
	#face = ((1,2,3)(1,2,3)(1,2,3))
	#uvdata = ((1,2)(1,2)(1,2))
	#objtable[obj] == (name, face, uvdata)
	objTable = [[[],[],""]] #objTable[object][0 = FaceTable, 1 = UVTable]
	#[(name,facedata,
	uvTable = []
	

	idvec3 = Vector ((0,0,0))
	idmat3 = Matrix(((0,0,0),(0,0,0),(0,0,0)))

	#print("\nImporting %s" % filepath)
	
	try:
		file = open(filepath, "r")
	except IOError:
		return "Could Not Open File:\n%s" % filepath
	
	for line in file:
		line = line.strip()
		line_split = line.split()

		if not line or line[0] == "/":
			continue

		elif state == 0 and line_split[0] == "MODEL":
			state = 1

		elif state == 1 and line_split[0] == "VERSION":
			version = line_split[1]
			if version != "5" and version != "6":
				print("\nUnsupported File Version: %s" % version)#Fix Later
				return "Unsupported File Version: %s" % version
			state = 2
		
		elif state == 2 and line_split[0] == "NUMBONES":
			numbones = int(line_split[1])
			cbone = 0;
			state = 3
		
		elif state == 3 and line_split[0] == "BONE":
			if cbone != int(line_split[1]):
				print("Error - Wong Bone") #Fix Later
	
			if(use_parents == True):
				boneTable.append( (line_split[3][1:-1], idmat3, idvec3) )
			else:
				boneTable.append( (line_split[3][1:-1], idmat3, idvec3, line_split[2]) )
			
			if(cbone >= numbones-1):
				cbone = 0
				state = 4
			else:
				cbone += 1
			
		elif state == 4 and line_split[0] == "BONE":
			#if cbone == 0:
			#	tstart = time.clock()
			if cbone != int(line_split[1]):
				return "unexpected bone number" #Fix Later
			state = 5

		elif state == 5 and line_split[0] == "OFFSET":
			line_split = line.replace(",", "").split()
			boneOff = Vector((float(line_split[1]), float(line_split[2]), float(line_split[3])))

			state = 6

		elif state == 6 and line_split[0] == "SCALE":
			#Usually 1.000000 - May not be at some point) #Fix Later
			state = 7
		
		elif state == 7 and line_split[0] == "X":
			line_split = line.replace(",", "").split()

			boneMat = []
			boneMat.append((float(line_split[1]), float(line_split[2]), float(line_split[3])))
			
			state = 8
		
		elif state == 8 and line_split[0] == "Y":
			line_split = line.replace(",", "").split()

			boneMat.append((float(line_split[1]), float(line_split[2]), float(line_split[3])))
			
			state = 9
		
		elif state == 9 and line_split[0] == "Z":
			line_split = line.replace(",", "").split()

			boneMat.append((float(line_split[1]), float(line_split[2]), float(line_split[3])))

			if(cbone == 0):
				bpy.ops.object.mode_set(mode='OBJECT')

				bpy.ops.object.add(type='ARMATURE', enter_editmode=True,location=Vector((0,0,0)))
				ob = bpy.context.object
				ob.show_x_ray = True
				ob.name = "Armature"
				amt = ob.data
				amt.name = ob.name + "Amt"
				#amt.show_axes = True

				bpy.ops.object.mode_set(mode='EDIT')
			bone = amt.edit_bones.new(boneTable[cbone][0])
			bone.use_local_location = False
			bone.head = (0,0,0)
			bone.tail = (0,1,0)
			bone.transform(Matrix(boneMat).transposed())
			bone.translate(boneOff)
			#print(boneTable[cbone][0], boneMat, boneOff)

			if(cbone >= numbones-1):
				cbone = 0
				#tend = time.clock()
				state = 10
			else:
				cbone += 1
				state = 4
				
		elif state == 10 and line_split[0] == "NUMVERTS":
			numverts = int(line_split[1])-1
			state = 11

		elif state == 11 and line_split[0] == "VERT":
			cvert = int(line_split[1]) #may not be needed
			state = 12

		elif state == 12 and line_split[0] == "OFFSET":
			vertTable.append((float(line.replace(",", "").split()[1]),float(line.replace(",", "").split()[2]),float(line.replace(",", "").split()[3])))
			state = 13

		elif state == 13 and line_split[0] == "BONES":
			vnumbones = int(line_split[1])
			vbone = 0
			state = 14

		elif state == 14 and line_split[0] == "BONE":
			#vertbonetable[vertid].append((line_split[1], linesplit[2])) #bone number, bone weight
			vbone += 1
			if (vbone >= vnumbones):
				if(cvert >= numverts):
					state = 15
				else:
					state = 11
		elif state == 15 and line_split[0] == "NUMFACES":
			numfaces = int(line_split[1])
			cface = 0
			state = 16
		elif (state == 16 or state == 29) and line_split[0] == "TRI":
			cfacedata = []
			cuvdata = []
			cob = int(line_split[1])
			cface += 1
			state = 17
		elif (state == 17 or state == 21 or state == 25) and line_split[0] == "VERT":
			cfacedata.append(int(line_split[1]))
			state+=1
		elif (state == 18 or state == 22 or state == 26) and line_split[0] == "NORMAL":
			state+=1
		elif (state == 19 or state == 23 or state == 27) and line_split[0] == "COLOR":
			state+=1
		elif (state == 20 or state == 24 or state == 28) and line_split[0] == "UV":
			cuvdata.append((float(line_split[2]),1.0-float(line_split[3])))#Y value is inverted
			if(state == 28):
				#Create Face
				#if(split_mode == True):
				tmp = (cob + 1) - len(objTable)
				if(tmp > 0):
					i = 0
					for i in range(tmp):
						objTable.append([[],[],""])
				print(tuple(Vector(cfacedata).xzy))
				objTable[0][0].append((cfacedata[0],cfacedata[2],cfacedata[1])) #had to convert cfacedata into cfacedata.xzy fixes normals somehow #objTable[cob][0].append(cfacedata)
				objTable[0][1].append((cuvdata[0],cuvdata[2],cuvdata[1]))#converting the cuvdata into cuvdata.xzy #objTable[cob][1].append(cuvdata)
				if(cface >= numfaces):
					state = 30
			state+=1
		elif state == 30 and line_split[0] == "NUMOBJECTS":
			state = 31
		elif state == 31 and line_split[0] == "OBJECT":
			#print(int(line_split[1]))
			#print(line_split[2][1:-1])
			objTable[int(line_split[1])][2] = (line_split[2][1:-1])#removed for debug
	file.close()

	#print(objTable[0][0])
	if(split_mode == False):
		bpy.ops.object.mode_set(mode='OBJECT')
		bpy.context.object.select = False
		me = bpy.data.meshes.new("OBJECTNAME")
		me.from_pydata(vertTable, [], objTable[0][0])
		me.update()
		mesh_ob = bpy.data.objects.new(objTable[0][2], me)
		bpy.context.scene.objects.link(mesh_ob)
		bpy.context.scene.objects.active = bpy.data.objects[objTable[0][2]]
		#bpy.ops.object.mode_set(mode='EDIT')
		#if(i == 0):
		uvtex = bpy.ops.mesh.uv_texture_add()
		uv = me.uv_layers.active.data
		a = 0
		for b in range(len(objTable[0][1])):
			uv[a].uv = objTable[0][1][b][0]
			a+=1
			uv[a].uv = objTable[0][1][b][1]
			a+=1
			uv[a].uv = objTable[0][1][b][2]
			a+=1
				#print(len(objTable[0][1]))
				#print(b)
	"""for i in range(len(objTable)):
		bpy.ops.object.mode_set(mode='OBJECT')
		bpy.context.object.select = False
		me = bpy.data.meshes.new(objTable[i][2])
		me.from_pydata(vertTable, [], objTable[i][0])
		me.update()
		mesh_ob = bpy.data.objects.new(objTable[i][2], me)
		bpy.context.scene.objects.link(mesh_ob)
		bpy.context.scene.objects.active = bpy.data.objects[objTable[i][2]]
		#bpy.ops.object.mode_set(mode='EDIT')
		#if(i == 0):
		uvtex = bpy.ops.mesh.uv_texture_add()
		uv = me.uv_layers.active.data
		if(i == 0):
			a = 0
			for b in range(len(objTable[0][1])):
				uv[a].uv = objTable[0][1][b][0]
				a+=1
				uv[a].uv = objTable[0][1][b][1]
				a+=1
				uv[a].uv = objTable[0][1][b][2]
				a+=1
				#print(len(objTable[0][1]))
				#print(b)
			"""
	
	#print(objTable)
