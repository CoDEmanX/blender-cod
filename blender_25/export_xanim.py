#!BPY

# export_xanim.py version 0.9
# Copyright (C) 2009  Nico's Computer Services -- peregrine@mymeteor.ie.
#               2011  CoDEmanX 
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

# This script exports meshes created with Blender in Call of Duty .xanim_export version 3 file format.
# The file format is suitable for COD1, UO, CoD2, CoD4, CoD5 and possibly above
# It exports frame data, bone pose data (does it?) and notetracks.

import string
import bpy
#TODO: remove unneeded imports!
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper, path_reference_mode, axis_conversion
from datetime import datetime

#UNDONE: This block isn't final, i tried to get the file ext stuff to work with this (without luck)
bl_info = {
    "name": "CoD animation v3 format",
    "author": "Flybynyt, CoDEmanX",
    "blender": (2, 58, 1),
    "api": 38019,
    "location": "File > Import-Export",
    "description": "...",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"}
    
''' Will be needed later...
# To support reload properly, try to access a package var, if it's there, reload everything
if "bpy" in locals():
    import imp
    if "import_3ds" in locals():
        imp.reload(import_3ds)
    if "export_3ds" in locals():
        imp.reload(export_3ds)
'''

def write_xanim(filepath):
    global out
    out = open(filepath, 'w')
     # write the header
    out.write('// XANIM_EXPORT file in CoD animation v3 format created with Blender v%s\n' % bpy.app.version_string)
    out.write('// Source file: %s\n' % bpy.data.filepath)
    out.write('// Export time: %s\n\n' % datetime.now().strftime('%d-%b-%Y %H:%M:%S'))
    out.write('ANIMATION \n')
    out.write('VERSION 3\n')
    out.write('\n')
    # ----------------------
    # get armature bone and pose data
    # ----------------------
    check_list = [] # create a list to hold the total number of bones in the armature
    final_list = [] # create a list to hold the bones in their final order.
    child_list = [] # create a list to hold the children of the root bone (TAG_ORIGIN).
    parent_list = [] # create a list to temporarily hold the child bones of the bones in the child_list list.
    
    try:
        obj = bpy.data.objects['Armature'] # get the "Armature" object in the scene
    except(KeyError):
        # no object 'Armature'
        # TODO: error handling through out this script
        out.write('\n\n*** No "Armature" object found! ***')
        out.close()
        return
    # alternatively, we could get the first armature: bpy.data.armatures[0]
    # but .data will not work then (do we need it?)

    #TODO: replace the bone order code by a simple for-iteration
    #      Blender puts them into desired tree automatically,
    #      just make sure to toogle to the desired mode (e.g. object mode)
    #      to update the scene. Attention: bpy.context.scene.update() doesn't work!

    arm = obj.data # initialise a variable and set it to the data of obj (the armature) 
    pose = obj.pose # set pose to the pose of the armature
    arm_mat = obj.matrix_world # initialise a variable and set it to the matrix of the obj (the armature) 
    for pbone in arm.bones.values(): # for every bone in the armature...
        check_list.append(pbone) # get a list of all the bones in the armature
    for pbone in arm.bones.values(): # for every bone in the armature
            if pbone.parent is None: # check for the root bone 
                final_list.insert(0, pbone) # put the root bone in the first location in the final_list list.
                for tcbone in arm.bones.values(): # go through every bone in the armature to check whether it corresponds to the name of the root bone's child bone
                    if tcbone in pbone.children.values(): # children.values() ??
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
    
    # CoDEmanX: Exporter should use Blender's framerate (render settings, used as playback speed)
    # Time remapping not taken into account
    out.write('FRAMERATE %i\n' % round(bpy.context.scene.render.fps/bpy.context.scene.render.fps_base))
    #out.write('FRAMERATE 30\n')
    
    # Getting start and end frame of first scene is okay, isn't it?
    #startingframe = Blender.Get('staframe') 
    #endingframe = Blender.Get('endframe')
    try:
        startingframe = bpy.data.scenes[0].frame_start
    except(IndexError):
        out.write('\n\n*** NO STARTING FRAME! ***')
        out.close()
        return
    
    try:
        endingframe = bpy.data.scenes[0].frame_end
    except(IndexError):
        out.write('\n\n*** NO ENDING FRAME! ***')
        out.close()
        return
    
    framenumber = endingframe - startingframe # the number of frames between the starting frame and the ending frame as set in the scene
    out.write('NUMFRAMES %i\n' % (framenumber + 1)) # in order for the ending frame to be compiled by Asset Manager, it is necessary to tell it the total amount of frames, including the ending frame.
    out.write('\n')
    
    #UNDONE? Does it really export pose data? If yes, out-commented code should get removed!
    # -------------------------
    # output the pose data for each bone in each frame
    # -------------------------
    for frame in range(startingframe, endingframe + 1): # Blender does not seem to want to export the last selected frame (ie. the endframe)
        try:
            bpy.data.scenes[0].frame_current = frame
        except(IndexError):
            out.write('\n\n*** Couldn\'t set frame_current, scene does not exist?! ***')
            out.close()
            return
        
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
                        out.write('X %f %f %f\n' % (pb.matrix[0][0], pb.matrix[0][1], pb.matrix[0][2]))
                        out.write('Y %f %f %f\n' % (pb.matrix[1][0], pb.matrix[1][1], pb.matrix[1][2]))
                        out.write('Z %f %f %f\n' % (pb.matrix[2][0], pb.matrix[2][1], pb.matrix[2][2]))
                        # out.write('wmX %f %f %f\n' % (pb_wm[0][0], pb_wm[0][1], pb_wm[0][2]))
                        # out.write('wmY %f %f %f\n' % (pb_wm[1][0], pb_wm[1][1], pb_wm[1][2]))
                        # out.write('wmZ %f %f %f\n' % (pb_wm[2][0], pb_wm[2][1], pb_wm[2][2]))
            # mat_3 = Matrix([pb.poseMatrix[0][0], pb.poseMatrix[0][1], pb.poseMatrix[0][2]],[pb.poseMatrix[1][0], pb.poseMatrix[1][1], pb.poseMatrix[1][2]],[pb.poseMatrix[2][0], pb.poseMatrix[2][1], pb.poseMatrix[2][2]])
            # out.write('inverted position matrix: %s\n' % (mat_3.invert()))
                        out.write('\n')
        out.write('\n')
        
    out.write('NOTETRACKS\n')
    out.write('\n')
    
    markers = bpy.context.scene.timeline_markers
    
    for pb in final_list:
    # for pb in pbones:
        out.write('PART %i\n' % (final_list.index(pb)))
        if final_list.index(pb) == 0 and len(markers) > 0: #TODO: add "and export_notetracks == True", but how to get the state from the button in export dialog?
            
            out.write('NUMTRACKS 1\n')
            out.write('\n')
            out.write('NOTETRACK 0\n')
            
            # Sort markers by frame number
            markers2 = []
            for m in markers:
                markers2.append([m.frame, m.name])
            markers2 = sorted(markers2)

            out.write('NUMKEYS %i\n' % len(markers2))
    
            for m in markers2:
                out.write('FRAME %i "%s"\n' % (m[0], m[1]))
            out.write('\n')
        else:
            out.write('NUMTRACKS 0\n')
            out.write('\n')
            	
    out.close()
    
    
class ExportXanim(bpy.types.Operator): #, ExportHelper
    bl_idname = "export.cod_xanim"
    bl_label = "Export to XANIM_EXPORT"
    #bl_options = {'PRESET'}
    
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    
    #TODO: make the file extension stuff work!
    
    #filename_ext = ".XANIM_EXPORT"
    #filter_glob = StringProperty(default="*.XANIM_EXPORT", options={'HIDDEN'})
    #filter_glob = StringProperty(default="*.XANIM_EXPORT")
    
    num_markers = len(bpy.context.scene.timeline_markers)
    export_notetracks = BoolProperty(name="Export Notetracks (" + str(num_markers) + ")", description="Write Notetracks to output file", default=bool(num_markers))

    
    @classmethod
    def poll(cls, context):
        # correct?
        return context.object is not None
        
    def execute(self, context):
        write_xanim(self.filepath)
        return {'FINISHED'}
        
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
# Only needed if you want to add into a dynamic menu
def menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(ExportXanim.bl_idname, text="CoD Xanim v3 (.XANIM_EXPORT)")
    
# Register and add to the file selector
bpy.utils.register_class(ExportXanim)
bpy.types.INFO_MT_file_export.append(menu_func)

# test call, keep this until release to make "Run Script" work
bpy.ops.export.cod_xanim('INVOKE_DEFAULT')