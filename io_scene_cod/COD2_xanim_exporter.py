#!BPY

"""
Name: 'COD2_xanim_export_exporter'
Blender: 246
Group: 'Export'
Tooltip: 'Blender to COD2 animation exporter'
"""
# COD2_xanim_exporter.py version 0.8
# Copyright (C) 2009  Nico's Computer Services -- peregrine@mymeteor.ie. 
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

# This script exports meshes created with Blender in Call of Duty 2 .xanim_export file format. The same file format is also suitable for COD1 and UO
# It exports frame data and bone pose data.
# To add notetracks, edit the exported .xanim_export file with Notepad or Notepad++. See the COD2 mod tools documentation for more information. 

import string
import Blender
from Blender import Object, Mesh, Scene, Window, sys, Image, Draw, Mathutils, Armature
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


def write_obj(filepath):
	global out
	out = file(filepath, 'w')
	out.write('//xanim_export file for COD2 created with Blender \nANIMATION \nVERSION 3\n') # write the header
	out.write('\n')
	# ----------------------
	# get armature bone and pose data
	# ----------------------
	check_list = [] # create a list to hold the total number of bones in the armature
	final_list = [] # create a list to hold the bones in their final order.
	child_list = [] # create a list to hold the children of the root bone (TAG_ORIGIN).
	parent_list = [] # create a list to temporarily hold the child bones of the bones in the child_list list.
	obj = Blender.Object.Get('Armature') # get the "Armature" object in the scene
	arm = obj.getData(); # initialise a variable and set it to the data of obj (the armature) 
	pose = obj.getPose() # set pose to the pose of the armature
	arm_mat = obj.matrixWorld # initialise a variable and set it to the matrix of the obj (the armature) 
	for pbone in arm.bones.values(): # for every bone in the armature...
		check_list.append(pbone) # get a list of all the bones in the armature
	for pbone in arm.bones.values(): # for every bone in the armature
			if pbone.parent is None: # check for the root bone 
				final_list.insert(0, pbone) # put the root bone in the first location in the final_list list.
				for tcbone in arm.bones.values(): # go through every bone in the armature to check whether it corresponds to the name of the root bone's child bone
					if tcbone in pbone.children: 
						child_list.append(tcbone)# add the root bone's children to the child_list list
		
	while len(final_list) < len(check_list): # check that the final list of bones in the correct order is not as long as the total number of bones in the armature.
		for cbone in arm.bones.values(): # for every bone in the armature
			if cbone in child_list: # if the bone is in the child_list list
				if cbone not in final_list: # and does not occur in the final_list list...
					final_list.append(cbone) # add the bone to the final_list list.
						# if cbone.hasChildren() == True:
					for ccbone in cbone.children: # put the bone's children, if any, into the parent_list list.
						parent_list.append(ccbone)
		child_list[0:] = [] # clean out the child_list list ready for the next batch of child bones - the next level down in the bone hierarchy.
		child_list.extend(parent_list) # copy the parent_list list into the child_list list
		parent_list[0:] = [] # clean out the parent_list list ready for the next batch of child bones' children - two levels down in the hierarchy.
			
	out.write('NUMPARTS %i\n' % (len(final_list)))
	# out.write('posebones dict %s\n' % (pose_bones))


	# ---------------------
	# output the part number and name of the bones
	# ---------------------
	for pb in final_list:
		out.write('PART %i "%s"\n' % (final_list.index(pb), pb.name))
	out.write('\n')
	out.write('FRAMERATE 30\n')
	startingframe = Blender.Get('staframe') 
	endingframe = Blender.Get('endframe') 
	framenumber = endingframe - startingframe # the number of frames between the starting frame and the ending frame as set in the scene
	out.write('NUMFRAMES %i\n' % (framenumber + 1)) # in order for the ending frame to be compiled by Asset Manager, it is necessary to tell it the total amount of frames, including the ending frame.
	out.write('\n')
	
	# -------------------------
	# output the pose data for each bone in each frame
	# -------------------------
	for frame in range(startingframe, endingframe + 1): # Blender does not seem to want to export the last selected frame (ie. the endframe)
		Blender.Set('curframe', frame)
		out.write('FRAME %i\n' % (frame))
		# pose = obj.getPose() # set pose to the pose of the armature
		for pcbone in final_list:
			for pb in pose.bones.values():
				if pcbone.name == pb.name:
					out.write('PART %i\n' % (final_list.index(pcbone)))
					if pb.parent is None:
						out.write('OFFSET %f %f %f\n' % (pb.tail[0], pb.tail[1], pb.tail[2]))
						out.write('SCALE 1.000000 1.000000 1.000000\n') # Script the scale of the bone
						out.write('X 1.000000, 0.000000, 0.000000\n') # root bone X Y and Z orientation vectors impact on how the model is oriented in Radiant and in Call of Duty 2
						out.write('Y 0.000000, 1.000000, 0.000000\n')
						out.write('Z 0.000000, 0.000000, 1.000000\n')
						out.write('\n')
					else:
						#pb_wm = pb.poseMatrix * arm_mat
						# out.write('pose bone matrix: %s\n' % (pb.poseMatrix))
						# out.write('pose bone by armature matrix: %s\n' % (pb_wm))
						newpb = pb.tail * arm_mat # get the world coordinates of the bone's tail.
						# out.write('newpb: %f %f %f\n' % (newpb[0], newpb[1], newpb[2]))
						# out.write('posebone head: %f %f %f\n' % (pb.head[0], pb.head[1], pb.head[2]))
			# out.write('pose bone all info: %s\n' % (pb)) # just gives the type and the name of the posebone
			# quat = blender_bone.matrix['BONESPACE'].toQuat()
			# tail = blender_bone.tail['BONESPACE'] * parent_mat
			# rot_mat = blender_bone.matrix['BONESPACE'] * parent_mat.rotationPart()
			# out.write('//pose bone quaternion: %s\n' % (pb.quat))
						# out.write('OFFSET %f %f %f\n' % (pb.tail[0], pb.tail[1], pb.tail[2]))
						out.write('OFFSET %f %f %f\n' % (newpb[0], newpb[1], newpb[2])) # location of the pb.tail multiplied by the armature object matrix to get the world co-ordinates, not the co-ordinates relative to the head of the root bone
						# out.write('Location %f %f %f\n' % (pb.loc[0], pb.loc[1], pb.loc[2]))
						out.write('SCALE 1.000000 1.000000 1.000000\n') # Script the scale of the bone
						out.write('X %f %f %f\n' % (pb.poseMatrix[0][0], pb.poseMatrix[0][1], pb.poseMatrix[0][2]))
						out.write('Y %f %f %f\n' % (pb.poseMatrix[1][0], pb.poseMatrix[1][1], pb.poseMatrix[1][2]))
						out.write('Z %f %f %f\n' % (pb.poseMatrix[2][0], pb.poseMatrix[2][1], pb.poseMatrix[2][2]))
						# out.write('wmX %f %f %f\n' % (pb_wm[0][0], pb_wm[0][1], pb_wm[0][2]))
						# out.write('wmY %f %f %f\n' % (pb_wm[1][0], pb_wm[1][1], pb_wm[1][2]))
						# out.write('wmZ %f %f %f\n' % (pb_wm[2][0], pb_wm[2][1], pb_wm[2][2]))
			# mat_3 = Matrix([pb.poseMatrix[0][0], pb.poseMatrix[0][1], pb.poseMatrix[0][2]],[pb.poseMatrix[1][0], pb.poseMatrix[1][1], pb.poseMatrix[1][2]],[pb.poseMatrix[2][0], pb.poseMatrix[2][1], pb.poseMatrix[2][2]])
			# out.write('inverted position matrix: %s\n' % (mat_3.invert()))
						out.write('\n')
		out.write('\n')
	out.write('NOTETRACKS\n')
	out.write('\n')
	for pb in final_list:
	# for pb in pbones:
			out.write('PART %i\n' % (final_list.index(pb)))
			out.write('NUMTRACKS 0\n')
			out.write('\n')
			
	# out.write('\n')		
	out.close()
	
Blender.Window.FileSelector(write_obj, "Export")

"""
	# ipobj = Blender.Object.Get('Armature') # get the "Armature" object in the scene
	# iparm = ipobj.getData() # get the data for the armature
	# act_list = ipobj.getAction() # get the action list for the armature
	# ip = act_list.getAllChannelIpos() # get the channel ipos for the action list
	# for bon in bonenamelist: # for each bone in the armature#
		# out.write('bone number %s\n' % (bonenamelist.index(bon)))
		# point_list = [] # initialise a list to hold the points
		# name = bon.name # set the name variable to the bone name.
		# ip_bon_channel = ip[bon.name] # get the bone's ip channel
		# ip_bon_name = ip_bon_channel.getName() # get the name of the bone's ip channel
		# ip_bon = Blender.Ipo.Get(ip_bon_name) # get the ipos of the bone's ip channel
		# poi = ip_bon.getCurves() # set poi to the bone's ipo curves
		# out.write('bone name %s\n' % (ip_bon_name))
		# for povar in poi[0].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[0] LocX %f %f\n' % (a[0], a[1]))
		# for povar in poi[1].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[1] LocY %f %f\n' % (a[0], a[1]))
		# for povar in poi[2].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[2] LocZ %f %f\n' % (a[0], a[1]))
		# for povar in poi[3].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[3] QuatW %f %f\n' % (a[0], a[1]))
		# for povar in poi[4].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[4] QuatX %f %f\n' % (a[0], a[1]))
		# for povar in poi[5].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[5] QuatY %f %f\n' % (a[0], a[1]))
		# for povar in poi[6].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[6] QuatZ %f %f\n' % (a[0], a[1]))
		# for povar in poi[7].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[7] ScaleX %f %f\n' % (a[0], a[1]))
		# for povar in poi[8].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[8] ScaleY %f %f\n' % (a[0], a[1]))
		# for povar in poi[9].getPoints():
			# a = povar.getPoints() # get the point data
			# out.write('a in poi[9] ScaleZ %f %f\n' % (a[0], a[1]))
		# for po in poi[3].getPoints(): # for every point in the fourth of the bone's ipo curves
			# a = po.getPoints() # get the point data
			# point_list.append(int(a[0])) # append the data to the point_list list
		# for po in poi:
			# out.write('ipo points %s\n' % (po))
	
	
	# *************************************
	# from the api
	# **************************************
	# ipo = Blender.Ipo.Get('ObIpo')                          # retrieves an Ipo object of which the name is already known
       # ipo.name = 'ipo1'                                       # change the Ipo's name
       # icu = ipo[Ipo.OB_LOCX]                          # request X Location Ipo curve
       # if icu != None and len(icu.bezierPoints) > 0: # if curve exists and has BezTriple points
               # val = icu[2.5]                                  # get the curve's value at time 2.5
               # ipo[Ipo.OB_LOCX] = None                 # delete the Ipo curve
			   
	
	

	# valid object ipo constraint names
		# Object Ipo: OB_LOCX, OB_LOCY, OB_LOCZ, OB_DLOCX, OB_DLOCY, OB_DLOCZ, OB_ROTX, OB_ROTY, OB_ROTZ, OB_DROTX, OB_DROTY, OB_DROTZ
	
	# valid pose / action ipo constraint names
	# PO_LOCX, PO_LOCY, PO_LOCZ, PO_SCALEX, PO_SCALEY, PO_SCALEZ, PO_QUATW, PO_QUATX, PO_QUATY, PO_QUATZ 
	
	
	# ipolist = Blender.Ipo.Get()
	

	ipolist = []
	for ipinfo in Blender.Ipo.Get():
		ipolist.append(ipinfo)
		out.write('the current ipoinfo name is: %s\n' % (ipinfo.name))
		# icu = ipinfo[Blender.Ipo.OB_LOCX]                          # request X Location Ipo curve
		icu = ipinfo[Blender.Ipo.PO_QUATX]
		if icu != None and len(icu.bezierPoints) > 0: # if curve exists and has BezTriple points
			val0 = icu[0]
			val05 = icu[140]
			val1 = icu[280]
			out.write('ob_locx at 0 %f, 140 %f and 280 %f frames\n' % (val0, val05, val1)) 
		possiblecurves = ipinfo.curveConsts
		out.write('possible curves: %s\n' % (possiblecurves))
"""

	# arm_obj = Blender.Object.Get('Armature') # set arm_obj to the armature
	# arm_mat = arm_obj.matrixWorld # set arm_mat to the world matrix of the armature
	# pose = arm_obj.getPose() # set pose to the pose of the armature
	# pose_bones = pose.bones # set pose_bones to the pose bones dict (name of bone, posebone name of bone) of the armature
	# pbones = pose.bones.values()
	
	# out.write('armature world matrix: %s\n' % (arm_obj.matrixWorld)) # turns out to be the identity matrix in 4x4 format.
	# out.write('NUMPARTS %i\n' % (len(pbones)))
	
	# for pb in pbones:
		# pose_bone = pose_bones[boneName] # set pose_bone to the name of the current pose bone
		# pose_bone_wm = pose_bone.poseMatrix * arm_mat # set pose_bone_wm to the result of the multiplication of the bone's matrix by the armature world matrix
		# out.write('posebone matrix: %s\n' % (pb.poseMatrix)) writes out the local matrix of the bone's pose
		# pb_wm = pb.poseMatrix * arm_mat
		# out.write('posebone world matrix: %s\n' % (pb_wm))
		
		
	# for part in bonenamelist:
		# out.write('PART %i "%s"\n' % (bonenamelist.index(part), part.name)) # the names of the parts correspond to the names of the bones
	
	# Loop all frames 
	# frnbr = 0 # initialise a variable to keep track of the current frame number.
	# for frame in range(startingframe, endingframe + 1):