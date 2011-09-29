"""
(c) 2011 by CoDEmanX

Version: alpha 2


TODO

- Add *.NT_EXPORT support (CoD5 / CoD7)
- Test pose matrix exports, global or local?

"""

import bpy
from datetime import datetime

def save(self, context, filepath="",
         use_frame_start=1,
         use_frame_end=250,
         use_framerate=24,
         use_notetracks=1
         ):
    
    armature = None
    last_frame_current = context.scene.frame_current
    
    # There's no context object right after object deletion
    try:
        last_mode = context.object.mode
    except (AttributeError):
        last_mode = 'OBJECT'

    # HACK: Force an update, so that bone tree is properly sorted for hierarchy table export
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    # Check input objects
    for ob in bpy.data.objects:
        
        # Take the first armature
        if ob.type == 'ARMATURE' and len(ob.data.bones) > 0:
            armature = ob
            break
    else:
        return "No armature to export.";
        
    # armature.pose.bones?
    bones = armature.data.bones
    
    # Get armature matrix once for later global coords/matrices calculation per frame
    a_matrix = armature.matrix_world
    
    # There's valid data for export, create output file
    try:
        file = open(filepath, "w")
    except IOError:
        return "Could not open file for writing:\n%s" % filepath
    
     # write the header
    file.write("// XANIM_EXPORT file in CoD animation v3 format created with Blender v%s\n" % bpy.app.version_string)
    file.write("// Source file: %s\n" % filepath)
    file.write("// Export time: %s\n\n" % datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    file.write("ANIMATION\n")
    file.write("VERSION 3\n\n")
    
    file.write("NUMPARTS %i\n" % len(bones))
        
    # Write bone table
    for i_bone, bone in enumerate(bones):
        file.write("PART %i \"%s\"\n" % (i_bone, bone.name))
    
    # Exporter should use Blender's framerate (render settings, used as playback speed)
    # Note: Time remapping not taken into account
    file.write("\nFRAMERATE %i\n" % use_framerate)

    file.write("NUMFRAMES %i\n\n" % (abs(use_frame_start - use_frame_end) + 1))
    

    # If start frame > end frame, export animation reversed
    if use_frame_start > use_frame_end:
        frame_order = -1
        frame_min = use_frame_end
        frame_max = use_frame_start
    else:
        frame_order = 1
        frame_min = use_frame_start
        frame_max = use_frame_end

    for i_frame, frame in enumerate(range(use_frame_start, use_frame_end + frame_order, frame_order), use_frame_start):

        file.write("FRAME %i\n" % i_frame)
        
        # Set frame directly
        context.scene.frame_current = frame
        
        # Get PoseBones for that frame
        bones = armature.pose.bones
        
        # Write bone orientations
        for i_bone, bone in enumerate(bones):
            file.write("PART %i\n" % i_bone)
            
            """ Doesn't seem to be right...
            if bone.parent is None:
                file.write("OFFSET 0.000000 0.000000 0.000000\n")
                file.write("SCALE 1.000000 1.000000 1.000000\n")
                file.write("X 1.000000, 0.000000, 0.000000\n")
                file.write("Y 0.000000, 1.000000, 0.000000\n")
                file.write("Z 0.000000, 0.000000, 1.000000\n\n")
            else:
            """
            
            b_tail = a_matrix * bone.tail
            file.write("OFFSET %.6f %.6f %.6f\n" % (b_tail[0], b_tail[1], b_tail[2]))
            file.write("SCALE 1.000000 1.000000 1.000000\n") # Is this even supported by CoD?
            file.write("X %.6f %.6f %.6f\n" % (bone.matrix[0][0], bone.matrix[0][1], bone.matrix[0][2]))
            file.write("Y %.6f %.6f %.6f\n" % (bone.matrix[1][0], bone.matrix[1][1], bone.matrix[1][2]))
            file.write("Z %.6f %.6f %.6f\n\n" % (bone.matrix[2][0], bone.matrix[2][1], bone.matrix[2][2]))
            
            """ Is a local matrix used (above) or a global?
            b_matrix = bone.matrix * a_matrix
            file.write("X %.6f %.6f %.6f\n" % (b_matrix[0][0], b_matrix[0][1], b_matrix[0][2]))
            file.write("Y %.6f %.6f %.6f\n" % (b_matrix[1][0], b_matrix[1][1], b_matrix[1][2]))
            file.write("Z %.6f %.6f %.6f\n" % (b_matrix[2][0], b_matrix[2][1], b_matrix[2][2]))
            """
            
    # Write notetrack data
    file.write("NOTETRACKS\n\n")
    
    # Blender timeline markers to notetrack nodes
    markers = []
    for m in context.scene.timeline_markers:
        if frame_max >= m.frame >= frame_min:
            markers.append(m)
    
    for i_bone, bone in enumerate(bones):
        
        file.write("PART %i\n" % (i_bone))
        
        # TODO: Add *.NT_EXPORT support
        if i_bone == 0 and use_notetracks and len(markers) > 0:
            
            file.write("NUMTRACKS 1\n\n")
            file.write("NOTETRACK 0\n")
            
            # Sort markers by frame number
            markers2 = []
            for m in markers:
                markers2.append([m.frame, m.name])
            markers2 = sorted(markers2)
            
            file.write("NUMKEYS %i\n" % len(markers2))
    
            for m in markers2:
                file.write("FRAME %i \"%s\"\n" % (m[0], m[1]))
            file.write("\n")
            
        else:
            file.write("NUMTRACKS 0\n\n")
                
    # Close to flush buffers!
    file.close()

    # Set frame_current and mode back
    context.scene.frame_current = last_frame_current
    bpy.ops.object.mode_set(mode=last_mode, toggle=False)
    
    # Quit with no errors
    return
    