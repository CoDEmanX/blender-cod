#!BPY

"""
Name: 'COD2_xmodel_export_exporter'
Blender: 246
Group: 'Export'
Tooltip: 'Blender to COD2 model exporter'
"""

# COD2_xmodel_exporter.py version 1.11 (now with actual functions!)
# Copyright (C) 2009  NCS -- peregrine@mymeteor.ie. 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# This script exports meshes created with Blender in Call of Duty 2 .xmodel_export file format.
# It exports bone data, vertex data, face data and texture coordinates.
# This script is heavily commented for the sake of clarity for the author and in the hope that it will help other scripters.

import string
import Blender
from Blender import Types, NMesh, Object, Mesh, Scene, Window, sys, Image, Draw, Mathutils, Armature
from Blender import Draw, BGL
from Blender.BGL import *
from Blender.Armature import Bone
from Blender.Armature import *
import Blender.Mathutils
from Blender.Mathutils import CrossVecs, Matrix, Vector
from Blender.Mathutils import *
import bpy
import BPyMesh
import BPyObject
import BPySys
import BPyMessages
import BPyMathutils
import math

def write_obj(filepath):
	global out
	out = file(filepath, 'w')
	# global childvar = 1 # initialise a variable to check whether there is a bone in the child_list list that has children.
# *******************
# write .xmodel_export file header
# *******************
	out.write('//xmodel_export file for COD2 created with Blender \nMODEL \nVERSION 6 \n') # write the header
	out.write('\n')
	# ********************
	# get armature and bone information
	# ********************
	
	CheckForArmature() # call function that checks whether there is an armature in the scene. Returns "1" if there is, otherwise "0"	
			
	if CheckForArmature() < 1: # if there is no armature object in the Blender file, this is a static model, so the whole TAG_ORIGIN bone (essential in every model) is scripted.
		WriteStaticArmature() # call function to write the armature for a static model
	else: # if there is an armature
		obj = Blender.Object.Get('Armature') # get the "Armature" object in the scene
		arm = obj.getData(); # initialise a variable and set it to the data of obj (the armature) 
		arm_mat = obj.matrixWorld # initialise a variable and set it to the matrix of the obj (the armature) 
	
		GetArmatureData(arm) # call function to get the armature bone data, passing in the 'arm' variable initialised above.
		final_list = [] # create a list to hold the bones in their final order.
		final_list.extend(GetArmatureData(arm)) # put the list returned by the GetArmatureData function into the list of bones.	
		out.write('NUMBONES %i\n' % (len(final_list))) # write out the number of bones in the armature.
		
		for lbone in final_list: # for every bone in the final_list
			if final_list.index(lbone) == 0: # check if it's the root bone 
				out.write('BONE 0 -1 "%s"\n' % (lbone.name)) # Script the root bone because it does not have a parent (set to -1 in the .xmodel_export file).
			else:
				out.write('BONE %i %i "%s"\n' % (final_list.index(lbone), final_list.index(lbone.parent), lbone.name)) # write the bone's number, its parent's number and it's name to the file.
		out.write('\n')

		for abone in final_list: # for every bone in the final ordered list of bones...
			if final_list.index(abone) == 0: # check if it's the root bone
				out.write('BONE 0\n') # Script the root bone because it does not have any further effect on the animation. It's just a locator for the origin of the armature when scripting animations in the .gsc file, and a locator for the model.
				out.write('OFFSET %f, %f, %f\n' % (abone.tail['ARMATURESPACE'][0], abone.tail['ARMATURESPACE'][1], abone.tail['ARMATURESPACE'][2]))
				out.write('SCALE 1.000000, 1.000000, 1.000000\n')
				out.write('X 1.000000, 0.000000, 0.000000\n') # root bone X Y and Z orientation vectors impact on how the model is oriented in Radiant.
				out.write('Y 0.000000, 1.000000, 0.000000\n')
				out.write('Z 0.000000, 0.000000, 1.000000\n')
				out.write('\n')
			else:
				out.write('BONE %i\n' % (final_list.index(abone))) # write out the index of the bone in the final_list list
				ab_wm = abone.matrix['ARMATURESPACE'] * arm_mat # set the bone matrix to world coordinates
				bb_wm = abone.tail['ARMATURESPACE'] * arm_mat
				aq = abone.matrix['ARMATURESPACE'].toQuat()
				ae = abone.matrix['ARMATURESPACE'].toEuler()
				out.write('OFFSET %f, %f, %f\n' % (bb_wm[0], bb_wm[1], bb_wm[2]))
				out.write('SCALE 1.000000, 1.000000, 1.000000\n') # script the scale, as it always seems to be 1.0
				out.write('X %f, %f, %f\n' % (ab_wm[0][0], ab_wm[0][1], ab_wm[0][2]))
				out.write('Y %f, %f, %f\n' % (ab_wm[1][0], ab_wm[1][1], ab_wm[1][2]))
				out.write('Z %f, %f, %f\n' % (ab_wm[2][0], ab_wm[2][1], ab_wm[2][2]))
				out.write('\n')
# ***********************
# get mesh information
# ***********************
	totalobverts = [] # create an array to hold the total amount of vertices in the scene. Will increase with every new name in the objectnamelist list.
	totalobfaces = [] # create an array to hold the total amount of faces in the scene. Will increase with every new name in the objectnamelist list.
	# materialname = face.image.name # get the name of the texture file for use in the last part of the .xmodel_export file.
	materialnamelist = [] # create a list to hold the names of the materials
	objectnamelist = [] # create an array to hold the names of the objects in the scene
	for obj in Blender.Scene.GetCurrent().objects: # check each object in the current scene
		if obj.type in ('Mesh'): # only the mesh objects are required by the .xmodel_export format
		 objectnamelist.append(obj) # add the name of the object to the array
	
	for ob in objectnamelist: # for every mesh object in the scene
		mesh = ob.getData() # get the object's mesh information
		vcount = 0 # initialize a variable to keep track of how many vertices are in the meshes
		fcount = 0 # initialize a variable to keep track of how many vertices are in the meshes
		for vert in mesh.verts: # for every vertex in the mesh...
			vcount=vcount+1 # increase the vertex counter
		if objectnamelist.index(ob) == 0: # if this is the first object whose vertices are being counted
			totalobverts.append(vcount) # append the total as the first index in the totalobverts list
		else: # if it is not the first object...
			vtot = vcount+totalobverts[-1] # add this object's vertex total to the total number of vertices up to and including the last object
			totalobverts.append(vtot) # append the new total to the totalobverts list
		# out.write('ob: %i, vcount: %i, totalobverts: %i\n' % (objectnamelist.index(ob), vcount, totalobverts[-1]))
		for face in mesh.faces: # for every face in the mesh...
			fcount=fcount+1 # increase the count
		if objectnamelist.index(ob) == 0: # if this is the first object whose faces are being counted
			totalobfaces.append(fcount) # append the total as the first index in the totalobverts list
		else: # if it is not the first object...
			ftot = fcount+totalobfaces[-1] # add this object's vertex total to the total number of vertices up to and including the last object
			totalobfaces.append(ftot) # append the new total to the totalobverts list
	out.write('NUMVERTS %i\n' % (totalobverts[-1])) # NUMVERTS and the number of vertices in the mesh print out


# **********************************
# get the material data
# **********************************
	texturelist = [] # create a list to hold the names of the texture image files.
	specshaderlist = ["Cook-Torrance", "Phong", "Blinn", "Toon", "WardIso"] # Create a list that holds all of Blender's specular shaders.
	matshaders = [] # create a list to hold the index numbers of the materials' specular shaders.
	RGBlist = [] # create a list to hold the diffuse colours of the materials.
	refractlist = [] # create a list to hold the refractive indices of the materials.
	specrgblist = [] # create a list to hold the specular colours of the materials.
	matmirlist = []  # create a list to hold the mirror colours of the materials. 
	matrefleclist = [] # create a list to hold the reflectivity of the materials. 
	matspeclist = [] # create a list to hold the specularity value of the materials.
	materials = Blender.Material.Get() # make a list of materials in the scene.	
	for mater in materials: # for each material
		textr = mater.getTextures() # initialise a textr tuple (returns "MTex" and "Material")to hold the material's textures.
		ttex = textr[0].tex # get the MTex's texture.
		texturelist.append(ttex.image.name) # add the name of the texture's image to the texturelist.
		matshad = mater.specShader # find the number of the specular shader for this material. 0 = CookTorrance, 1 = Phong, 2 = Blinn, 3 = Toon, 4 = WardIso.
		matshaders.append(matshad)# add the material's shader number to the matshaders list.
		matcol = mater.getRGBCol()# get the diffuse colours of the material - returns 3 floats.
		RGBlist.append(matcol) # add the material's diffuse colour to the RGB list.
		matrefrac = mater.getRefracIndex() # get the refractive index of the material - returns 1 float.
		refractlist.append(matrefrac) # add the material's refractive index to the refractlist.
		specol = mater.getSpecCol() # get the material's specular colour.
		specrgblist.append(specol) # add the material's specular colour to the specrgblist.
		matmir = mater.getMirCol() # get the material's mirror colour.
		matmirlist.append(matmir) # add the material's mirror colour to the matmirlist.
		matreflec = mater.getRef() # get the material's reflectivity value.
		matrefleclist.append(matreflec) # add the material's reflectivity value to the matrefleclist.
		matspec = mater.getSpec() # get the material's specularity value.
		matspeclist.append(matspec) # add the material's specularity value to the matspeclist.

	
# ************************
# write vertex information
# ************************	
	if CheckForArmature() < 1: # if there is no armature object in the Blender file, this is a static model, so the TAG_ORIGIN bone influence on each vertex is scripted.
		for vertob in objectnamelist: # for every mesh object in the scene
			mesh = vertob.getData() # get the object's data
			matrix = vertob.getMatrix() # get the object's matrix
			vnumber = 0 # initialize a variable to keep track of which vertex is current
			for vert in mesh.verts:
				if objectnamelist.index(vertob) == 0: # if the current object is the first in the objectnamelist list
					vertnumber = vnumber # set the total number of vertices in the scene to the first object's vertex count
				else: # if it is not the first object in the scene
					vertnumber = vnumber + totalobverts[objectnamelist.index(vertob) - 1] # set the total number of vertices to the sum of the vertices in each object up to, but not including, the current object plus the current vertex's number.
				out.write('VERT %i\n' % (vertnumber)) # print out the vertex number.
				matrixIndentWorkaround1 = 0
				matrixIndentWorkaround2 = 0
				if matrixIndentWorkaround1 == matrixIndentWorkaround2: # Without this workaround, Blender Python returns an indentation error for the line after the matrix multiplication. No idea why. It does not happen after NewX, only after NewY and NewZ.
					newX = (matrix[0][0] * vert.co[0]) + (matrix[1][0] * vert.co[1]) + (matrix[2][0] * vert.co[2]) + (matrix[3][0])# calculate the global x coordinate of the vertex
					# newX = (matrix[0][1] * vert.co[0]) + (matrix[1][1] * vert.co[1]) + (matrix[2][1] * vert.co[2]) + (matrix[3][1])# Blender models imported into Radiant are rotated 90 degrees CCW about the Z axis, so this script forces the X axis to point in the Y direction.
					newY = (matrix[0][1] * vert.co[0]) + (matrix[1][1] * vert.co[1]) + (matrix[2][1] * vert.co[2]) + (matrix[3][1])# global y coord
					# newY = (matrix[0][0] * vert.co[0] * -1) + (matrix[1][0] * vert.co[1]) + (matrix[2][0] * vert.co[2]) + (matrix[3][0]) # Blender models imported into Radiant are rotated 90 degrees CCW about the Z axis, so this script forces the Y axis to point in the -X direction.
					newZ = (matrix[0][2] * vert.co[0]) + (matrix[1][2] * vert.co[1]) + (matrix[2][2] * vert.co[2]) + (matrix[3][2])# global z coord
				out.write('OFFSET %f, %f, %f\n' % (newX, newY, newZ)) # print out the global co-ordinates
				out.write('BONES 1\n')
				out.write('BONE 0 1.000000\n')
				vnumber=vnumber+1 # set the next vertex as current
				out.write('\n')
	
	else: #if there is an armature in the scene
		vertinf = 0 # initialise a variable to hold the length of the list containing the data about bones that influence the vertex.
		vertinfnew = 0 # initialise a variable to hold the length of the list containing the data about the main five bones that influence the vertex.
		for vertob in objectnamelist: # for every mesh object in the scene
			mesh = vertob.getData() # get the object's data
			matrix = vertob.getMatrix() # get the object's matrix
			vnumber = 0 # initialize a variable to keep track of which vertex is current
			lastvertfirstinf = [[final_list[1].name, 1.000000]] # create a list to hold the information for a default bone if the current vertex has no influences.
			for vert in mesh.verts:
				longinflist = mesh.getVertexInfluences(vnumber) # get the bone influences for this vertex. Returns a list of lists. Each sublist contains [bone.name (in string format)][influence (in float format)]
				nullinf = 0 # initialise a variable to check which bones are in the list but have no influence on the vertex.
				for inf in longinflist:
					if longinflist[nullinf][1] < 0.000001: # if the second parameter (the amount of influence) of this sublist is greater than 0.00000...
						del longinflist[nullinf] # remove the bone from the vertex's influence list
						nullinf = nullinf-1 # set the counter back to the previous number so that the next influence is not skipped (due to the deletion of this influence).
					nullinf = nullinf+1 # go to the next item in the list	
				nullinfl = 0 # initialise a variable to check which bones are in the list but have no influence on the vertex.
				for infl in longinflist:
					if longinflist[nullinfl][1] == 0.0: # if the second parameter (the amount of influence) of this sublist is greater than 0.00000...
						del longinflist[nullinfl] # remove the bone from the vertex's influence list
						nullinfl = nullinfl-1
					nullinfl = nullinfl+1 # go to the next item in the list
				shortinflist = longinflist
				if len(longinflist) == 0:
					shortinflist[0:] = [] # clean out the default bone value list
					shortinflist = lastvertfirstinf # set the shortlist of influences to the last in vertex's first influence
				infltot = 0 # initialise a variable to keep track of which influence is being added.
				infllist = [] # initialise a list to hold influence information, as Blender's total influences don't usually add up to 1.000000, which is what the .xmodel_export format requires
				for x in shortinflist: # iterate over the list of influences.
					infllist.append(shortinflist[infltot][1]) # put the influence value of each bone into infllist.
					infltot = infltot+1 # go to the next influence value.
				totalinf = 1.000000 # create a variable to hold the total influence of all the bones affecting this vertex. Should end up at 1.000000
				totalinf = sum(infllist) # set totalinf to the sum of all the items in infllist
				if totalinf == 0: # if the sum of the influences is 0 - this is a bug in the script - it should weed out the 0 influences in line 216
					totalinf = 1.000000 # give a nominal influence
				newval = 0 # initialise a variable to hold the factor by which each influence needs to be multiplied
				newval = 1.000000 / totalinf # find the factor by which each influence needs to be multiplied in order for the total influence to be 1.000000
				newinf = 0 # initialise a variable to keep track of the application of new influences.
				for y in infllist: # iterate over the list of influences.
					shortinflist[newinf][1] = infllist[newinf]*newval # set the new influence value in the influence list to the product of the original influence multiplied by the newval factor.
					newinf = newinf+1 # go to the next influence value.
				
				if objectnamelist.index(vertob) == 0: # if the current object is the first in the objectnamelist list
					vertnumber = vnumber # set the total number of vertices in the scene to the first object's vertex count
				else: # if it is not the first object in the scene
					vertnumber = vnumber + totalobverts[objectnamelist.index(vertob) - 1] # set the total number of vertices to the sum of the vertices in each object up to, but not including, the current object plus the current vertex's number.
				out.write('VERT %i\n' % (vertnumber)) # print out the vertex number.
				matrixIndentWorkaround1 = 0
				matrixIndentWorkaround2 = 0
				if matrixIndentWorkaround1 == matrixIndentWorkaround2: # Without this workaround, Blender Python returns an indentation error for the line after the matrix multiplication. No idea why. It does not happen after NewX, only after NewY and NewZ.
					newX = (matrix[0][0] * vert.co[0]) + (matrix[1][0] * vert.co[1]) + (matrix[2][0] * vert.co[2]) + (matrix[3][0])# calculate the global x coordinate of the vertex
					newY = (matrix[0][1] * vert.co[0]) + (matrix[1][1] * vert.co[1]) + (matrix[2][1] * vert.co[2]) + (matrix[3][1])# global y coord
					newZ = (matrix[0][2] * vert.co[0]) + (matrix[1][2] * vert.co[1]) + (matrix[2][2] * vert.co[2]) + (matrix[3][2])# global z coord
				out.write('OFFSET %f, %f, %f\n' % (newX, newY, newZ)) # print out the global co-ordinates
				out.write('BONES %i\n' % (len(shortinflist)))
				infvar = 0 # initialise a variable to keep track of which bone influence is current
				for q in shortinflist: # iterate over the bones in shortinflist to write out the bones and their amount of influence on the vertex.
					for vbone in arm.bones.values(): # for every bone in the armature
						if vbone.name == shortinflist[infvar][0]: # if the bone name is the same as the influencing bone
							out.write('BONE %i %f\n' % (final_list.index(vbone), shortinflist[infvar][1])) # write out the bone's number (its final_list index) and the recalulated influence.
					infvar = infvar+1
				lastvertfirstinf = shortinflist # set the list holding the previous vertex's influences to that of the present vertex, ready to be used for the next vertex, if necessary.
				vnumber=vnumber+1 # set the next vertex as current
				out.write('\n')
					

# ********************************
# write face information
# ********************************	
	out.write('NUMFACES %i\n' % (totalobfaces[-1]))
	fnumber=0 # initialise a variable to keep track of the number of faces
	for faceob in objectnamelist:
		mesh = faceob.getData()
		for face in mesh.faces: # for every face in the mesh
			fvnumlist = [] # create an array to hold the face's vertex number data
			fvuvlist = [] # create an array to hold the face's vertex UV coordinate data
			for uv in face.uv: # for each vertex in the face
				# fvuvlist.extend([uv[0], uv[1]]) # add the vertices' UVs to the array flist[6], [7], [8], [9], [10], [11]
				fvuvlist.extend([uv[0], uv[1] * -1]) # textures appear flipped vertically in Radiant, so this script inverts the uv Y value.
			out.write('TRI %i %i 0 0\n' % (objectnamelist.index(faceob), texturelist.index(face.image.name))) # write the nuber of the mesh that the face belongs to and the number of the texture image assigned to this face
			vertuv = 0 # initialise a variable to keep track of which vertex's UV coordinates are needed
			for vert in face.v: # for each vertex in the face 
				if objectnamelist.index(faceob) == 0: # if the current object is the first in the objectnamelist list
					fvertnumber = mesh.verts.index(vert) # set the total number of vertices in the scene to the first object's vertex count
				else: # if it is not the first object in the scene
					fvertnumber = mesh.verts.index(vert) + totalobverts[objectnamelist.index(faceob) - 1] # set the total number of vertices to the sum of the vertices in each object up to, but not including, the current object plus the current vertex's number.
				out.write('VERT %i\n' % (fvertnumber)) # print out the vertex number.
				out.write('NORMAL %f %f %f\n' % (vert.no[0], vert.no[1], vert.no[2])) # write out the vertex's normals
				out.write('COLOR 1.000000 1.000000 1.000000 1.000000\n') # script the colour data
				out.write('UV 1 %f %f\n' % (fvuvlist[vertuv * 2], fvuvlist[(vertuv * 2) + 1])) # write UV 1 and the third vertex's UVs
				vertuv = vertuv + 1
	out.write('\n')

# **********************************
# write the names of the mesh objects
# **********************************
	out.write('NUMOBJECTS %i\n' % (len(objectnamelist)))# writes the number of objects in the scene. Remember to remove camera and light before exporting
	for nameob in objectnamelist:
		out.write('OBJECT %i "%s"\n' % (objectnamelist.index(nameob), nameob.name))
	out.write('\n')
	
# **********************************
# write the materials
# **********************************	
	out.write('NUMMATERIALS %i\n' % (len(materials))) # writes the number of materials in the scene.
	matcount = 0 # initialise a variable to keep track of which material is being dealt with.
	for materout in materials:
		mshader = matshaders[matcount]
		out.write('MATERIAL %i "%s" "%s" "%s"\n' % (materials.index(materout), materout.name, specshaderlist[mshader], texturelist[matcount])) # print out the index number, name shader and texture image of the material.
		out.write('COLOR %f %f %f 1.000000\n' % (RGBlist[matcount][0], RGBlist[matcount][1], RGBlist[matcount][2]))
		out.write('TRANSPARENCY 0.000000 0.000000 0.000000 1.000000\n') # RGBA values - scripted for now 
		out.write('AMBIENTCOLOR 0.000000 0.000000 0.000000 1.000000\n')  # RGBA values - scripted for now
		out.write('INCANDESCENCE 0.000000 0.000000 0.000000 1.000000\n') # unknown RGBA values - scripted for now
		out.write('COEFFS 0.800000 0.000000\n') # unknown - scripted for now.
		out.write('GLOW 0.000000 0\n') # unknown - scripted for now.
		out.write('REFRACTIVE %i 1.000000\n' % (refractlist[matcount])) # second value unknown.
		out.write('SPECULARCOLOR %f %f %f 1.000000\n' % (specrgblist[matcount][0], specrgblist[matcount][1], specrgblist[matcount][2]))
		out.write('REFLECTIVECOLOR %f %f %f 1.000000\n' % (matmirlist[matcount][0], matmirlist[matcount][1], matmirlist[matcount][2]))
		out.write('REFLECTIVE 1 %f\n' % (matrefleclist[matcount])) # first value unknown.
		out.write('BLINN %f 0.700000\n' % (matspeclist[matcount]))# second value unknown.
		out.write('PHONG -1.000000\n') # "phong" is also a specular shader and a material can only have one specular shader in Blender, so this is scripted.
		matcount = matcount + 1	
	
	out.close()
	
Blender.Window.FileSelector(write_obj, "Export")

def CheckForArmature(): #function to check whether or not there is an armature
	anim_model = 0 # initialise a variable to check whether the model is static (no armature) or animated
	for obj in Blender.Scene.GetCurrent().objects: # check each object in the current scene
		if obj.type in ('Armature'): # if there is an oject of type armature
			anim_model = 1 # set the variable to 1
	return anim_model
	
def WriteStaticArmature(): # function to write armature of static models
	out.write('NUMBONES 1\n')
	out.write('BONE 0 -1 "TAG_ORIGIN"\n') # Script the root bone because it does not have a parent (set to -1 in the .xmodel_export file).
	out.write('\n')
	out.write('BONE 0\n')
	out.write('OFFSET 0.000000,0.000000, 0.000000\n')
	out.write('SCALE 1.000000, 1.000000, 1.000000\n')
	out.write('X 1.000000, 0.000000, 0.000000\n') # root bone X Y and Z orientation vectors impact on how the model is oriented in Radiant
	out.write('Y 0.000000, 1.000000, 0.000000\n')
	out.write('Z 0.000000, 0.000000, 1.000000\n')
	out.write('\n')
	return 
	
def GetArmatureData(arm):
	check_list = [] # create a list to hold the total number of bones in the armature
	final_list = [] # create a list to hold the bones in their final order.
	child_list = [] # create a list to hold the children of the root bone (TAG_ORIGIN).
	parent_list = [] # create a list to temporarily hold the child bones of the bones in the child_list list.
	for bone in arm.bones.values(): # for every bone in the armature...
		check_list.append(bone) # get a list of all the bones in the armature
		
	for abone in arm.bones.values(): # for every bone in the armature
		if abone.hasParent() == 0:
			final_list.insert(0, abone) # put the root bone in the first location in the final_list list.
			for tcbone in arm.bones.values(): # go through every bone in the armature to check whether it corresponds to the name of the root bone's child bone
				if tcbone in abone.children: 
					child_list.append(tcbone)# add the root bone's children to the child_list list
	while len(final_list) < len(check_list): # check that the final list of bones in the correct order is not as long as the total number of bones in the armature.
		for cbone in arm.bones.values(): # for every bone in the armature
			if cbone in child_list: # if the bone is in the child_list list
				if cbone not in final_list: # and does not occur in the final_list list...
					final_list.append(cbone) # add the bone to the final_list list.
					for ccbone in cbone.children: # put the bone's children, if any, into the parent_list list.
						parent_list.append(ccbone)
		child_list[0:] = [] # clean out the child_list list ready for the next batch of child bones - the next level down in the bone hierarchy.
		child_list.extend(parent_list) # copy the parent_list list into the child_list list
		parent_list[0:] = [] # clean out the parent_list list ready for the next batch of child bones' children - two levels down in the hierarchy.
	return final_list	