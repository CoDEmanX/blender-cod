"""
(c) 2011 by CoDEmanX

Version: alpha 3


TODO

- Ensure valid material# / fallback (alpha 3)
- Allow to export selection only (alpha 3)
- Add batch export of posed models, animation to model series (alpha 3)

- Skip bones with influence of 0.010096 and less (too small weight!)
Note: The final weight sum per vertex should be about 1.0.
The script sets too small weights to 0.0 BEFORE calculating weight/total weight.
This should work in most situtions, but it might give weight sums <> 1.0
(e.g. weight is > required minimum, but becomes < after division, sum will be < 1.0)
Would something like LOOP(normalize, drop too small weights) work???

"""

import bpy
import os
from datetime import datetime

# Global var, smallest allowed bone weight
weight_min = 0.010097

def save(self, context, filepath="",
         use_version='6',
         use_selection=False,
         use_vertex_colors=True,
         use_apply_modifiers=True,
         use_armature=True,
         use_armature_pose=False,
         use_frame_start=1,
         use_frame_end=250,
         ):

    num_verts = 0
    num_faces = 0
    meshes = []
    meshes_matrix = []
    meshes_vgroup = []
    objects = []
    armature = None
    bone_mapping = {}
    materials = []

    ob_count = 0
    v_count = 0

    # There's no context object right after object deletion
    try:
        last_mode = context.object.mode
    except (AttributeError):
        last_mode = 'OBJECT'

    # HACK: Force an update, so that bone tree is properly sorted for hierarchy table export
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    # Check input objects, count them and convert mesh objects
    for ob in bpy.data.objects:
        
        # Take the first armature
        if ob.type == 'ARMATURE' and use_armature and armature is None and len(ob.data.bones) > 0:
            armature = ob
            continue
        
        if ob.type != 'MESH':
            continue
        
        # Set up modifiers whether to apply deformation or not
        mod_states = []
        for mod in ob.modifiers:
            mod_states.append(mod.show_viewport)
            if mod.type == 'ARMATURE':
                mod.show_viewport = mod.show_viewport and use_armature_pose
            else:
                mod.show_viewport = mod.show_viewport and use_apply_modifiers
        
        # to_mesh() applies enabled modifiers only
        mesh = ob.to_mesh(scene=context.scene, apply_modifiers=True, settings='PREVIEW')

        # Restore modifier settings
        for i, mod in enumerate(ob.modifiers):
            mod.show_viewport = mod_states[i]

        # Skip invalid meshes
        if len(mesh.vertices) < 3 or len(mesh.faces) < 1 or len(ob.material_slots) < 1 or not mesh.uv_textures:
            continue
            
        meshes.append(mesh)
        meshes_matrix.append(ob.matrix_world)
        
        if ob.vertex_groups:
            meshes_vgroup.append(ob.vertex_groups)
        else:
            meshes_vgroup.append(None)
        
        num_verts += len(mesh.vertices)
        
        # Take quads into account!
        for f in mesh.faces:
            if len(f.vertices) == 3:
                num_faces += 1
            else:
                num_faces += 2
        
        objects.append(ob.name)
        
        # Store all used materials (unique)
        for ms in ob.material_slots:
            if ms.material not in materials:
                materials.append(ms.material)

    if (num_verts or num_faces or len(objects)) == 0:
        return "Nothing to export.\nMeshes must have at least:\n    3 vertices\n    1 face\n    1 material\n    UV mapping"

    # There's valid data for export, create output file
    try:
        file = open(filepath, "w")
    except IOError:
        return "Could not open file for writing:\n%s" % filepath

    # Write header
    file.write("// XMODEL_EXPORT file in CoD model v%i format created with Blender v%s\n" % (int(use_version), bpy.app.version_string))
    file.write("// Source file: %s\n" % bpy.data.filepath)
    file.write("// Export time: %s\n\n" % datetime.now().strftime("%d-%b-%Y %H:%M:%S"))

    file.write("MODEL\n")
    file.write("VERSION %i\n" % int(use_version))


    # Write armature data
    if armature is None:

        # Default rig
        file.write("\nNUMBONES 1\n")
        file.write("BONE 0 -1 \"tag_origin\"\n")
        
        file.write("\nBONE 0\n")
        file.write("OFFSET 0.000000 0.000000 0.000000\n")
        file.write("SCALE 1.000000 1.000000 1.000000\n")
        file.write("X 1.000000 0.000000 0.000000\n")
        file.write("Y 0.000000 1.000000 0.000000\n")
        file.write("Z 0.000000 0.000000 1.000000\n")
        
    else:
        
        # TODO: Test this!
        if use_armature_pose:
            bones = armature.pose.bones
        else:
            bones = armature.data.bones
            
        file.write("\nNUMBONES %i\n" % len(bones))
        
        a_matrix = armature.matrix_world
        
        # Get the root bone
        root = bones[0]
        
        # Check for multiple roots, armature should have exactly one
        roots = 0
        for bone in bones:
            if bone.parent == None:
                roots += 1
        if roots != 1:
            file.write("// Warning: %i root bones found in armature object '%s'\n" % (roots, armature.name))
        
        # Write bone hierarchy table and create bone_mapping array for later use (vertex weights)
        for i, bone in enumerate(bones):
            file.write("BONE %i %i \"%s\"\n" % (i, bone.parent_index(root)-1, bone.name))
            bone_mapping[bone.name] = i
        
        # Write bone orientations
        for i, bone in enumerate(bones):
            file.write("\nBONE %i\n" % i)
            
            b_tail = a_matrix * bone.tail
            file.write("OFFSET %.6f %.6f %.6f\n" % (b_tail[0], b_tail[1], b_tail[2]))
            
            file.write("SCALE 1.000000 1.000000 1.000000\n") # Is this even supported by CoD?
            
            b_matrix = bone.matrix * a_matrix
            file.write("X %.6f %.6f %.6f\n" % (b_matrix[0][0], b_matrix[0][1], b_matrix[0][2]))
            file.write("Y %.6f %.6f %.6f\n" % (b_matrix[1][0], b_matrix[1][1], b_matrix[1][2]))
            file.write("Z %.6f %.6f %.6f\n" % (b_matrix[2][0], b_matrix[2][1], b_matrix[2][2]))


    # Write vertex data
    file.write("\nNUMVERTS %i\n" % num_verts)

    for i, me in enumerate(meshes):

        # Retrieve verts which belong to a face only
        verts = []
        for f in me.faces:
            for v in f.vertices:
                verts.append(v)

        # Uniquify & sort
        keys = {}
        for e in verts:
            keys[e] = 1
        verts = list(keys.keys())

        # Get the right object matrix for mesh
        mesh_matrix = meshes_matrix[i]
        
        # Get bone influences per vertex
        if armature is not None and meshes_vgroup[i] is not None:
            
            groupNames, vWeightList = meshNormalizedWeights(meshes_vgroup[i], me)
            groupIndices = [bone_mapping.get(g, -1) for g in groupNames] # Bind to root if there's no bone with vertex_group name
                
            weight_group_list = []
            for weights in vWeightList:
                weight_group_list.append(sorted(zip(weights, groupIndices), reverse=True))
                
                
        for vert in verts:
            v = me.vertices[vert]
            
            # Calculate global coords
            x=mesh_matrix[0][0]*v.co[0]+mesh_matrix[1][0]*v.co[1]+mesh_matrix[2][0]*v.co[2]+mesh_matrix[3][0]
            y=mesh_matrix[0][1]*v.co[0]+mesh_matrix[1][1]*v.co[1]+mesh_matrix[2][1]*v.co[2]+mesh_matrix[3][1]
            z=mesh_matrix[0][2]*v.co[0]+mesh_matrix[1][2]*v.co[1]+mesh_matrix[2][2]*v.co[2]+mesh_matrix[3][2]
            
            file.write("VERT %i\n" % (v.index+v_count))
            file.write("OFFSET %.6f, %.6f, %.6f\n" % (x, y, z))
            
            # Write bone influences
            if armature is None or meshes_vgroup[i] is None:
                file.write("BONES 1\n")
                file.write("BONE 0 1.000000\n\n")
            else:
                cache = ""
                c_bones = 0
                for weight, bone_index in weight_group_list[v.index]:
                    if round(weight, 6) < weight_min:
                        break
                    cache += "BONE %i %.6f\n" % (bone_index, weight)
                    c_bones += 1
                    
                if c_bones == 0:
                    file.write("// Warning: No bone influence found for vertex %i, binding to root...\n" % v.index)
                    file.write("BONES 1\n")
                    file.write("BONE 0 1.000000\n\n")
                else:
                    file.write("BONES %i\n%s\n" % (c_bones, cache))
            
            
        v_count += len(verts);

    # TODO: Find a proper way to keep track of the vertex index?   
    v_count = 0


    # Write face data
    file.write("\nNUMFACES %i\n" % num_faces)

    for me in meshes:

        for f in me.faces:
            
            # TODO: Remap!
            mat = f.material_index
            
            if me.vertex_colors:
                col = me.vertex_colors.active.data[f.index]
            
            # Experimental triangulation support
            f_v_orig = [v for v in enumerate(f.vertices)]
            
            if len(f_v_orig) == 3:
                f_v_iter = (f_v_orig[2], f_v_orig[1], f_v_orig[0]), # HACK: trailing comma to force a tuple
            else:
                f_v_iter = (f_v_orig[2], f_v_orig[1], f_v_orig[0]), (f_v_orig[3], f_v_orig[2], f_v_orig[0])
                
            for iter in f_v_iter:
                
                if use_version == '5':
                    file.write("TRI %i 0 %i 1\n" % (ob_count, mat))
                else:
                    file.write("TRI %i %i 0 0\n" % (ob_count, mat))
                
                for vi, v in iter:
                
                    no = me.vertices[v].normal # Invert? Orientation seems to have no effect...
                    
                    uv = me.uv_textures.active
                    uv1 = uv.data[f.index].uv[vi][0]
                    uv2 = 1 - uv.data[f.index].uv[vi][1] # Flip!
                    # TODO: Warn if accidentally tiling ( uv <0 or >1 )
                    
                    if use_version == '5':
                        file.write("VERT %i %.6f %.6f %.6f %.6f %.6f\n" % (v+v_count, uv1, uv2, no[0], no[1], no[2]))
                    else:
                        file.write("VERT %i\n" % (v+v_count))
                        file.write("NORMAL %.6f %.6f %.6f\n" % (no[0], no[1], no[2]))
                        
                        if me.vertex_colors and use_vertex_colors:
                            
                            if vi == 0:
                                c = col.color1
                            elif vi == 1:
                                c = col.color2
                            elif vi == 2:
                                c = col.color3
                            else:
                                c = col.color4
                                
                            file.write("COLOR %.6f %.6f %.6f 1.000000\n" % (c[0], c[1], c[2]))
                        else:
                            file.write("COLOR 1.000000 1.000000 1.000000 1.000000\n")
                            
                        file.write("UV 1 %.6f %.6f\n" % (uv1, uv2))
        
        # Note: Face types (tris/quads) have nothing to do with vert indices!
        v_count += len(me.vertices)
        
        ob_count += 1


    # Write object data
    file.write("\nNUMOBJECTS %i\n" % len(objects))

    for i_ob, ob in enumerate(objects):
        file.write("OBJECT %i \"%s\"\n" % (i_ob, ob))
        
        
    # Write material data
    cache = ""
    c_materials = 0
    
    # Static material string
    material_string = ("COLOR 0.000000 0.000000 0.000000 1.000000\n"
                       "TRANSPARENCY 0.000000 0.000000 0.000000 1.000000\n"
                       "AMBIENTCOLOR 0.000000 0.000000 0.000000 1.000000\n"
                       "INCANDESCENCE 0.000000 0.000000 0.000000 1.000000\n"
                       "COEFFS 0.800000 0.000000\n"
                       "GLOW 0.000000 0\n"
                       "REFRACTIVE 6 1.000000\n"
                       "SPECULARCOLOR -1.000000 -1.000000 -1.000000 1.000000\n"
                       "REFLECTIVECOLOR -1.000000 -1.000000 -1.000000 1.000000\n"
                       "REFLECTIVE -1 -1.000000\n"
                       "BLINN -1.000000 -1.000000\n"
                       "PHONG -1.000000\n\n"
                       )

    for mat in materials:
        try:
            for ts in mat.texture_slots:
                # Skip empty slots
                if not ts:
                    continue
                    
                # Pick filename of the first color map
                if ts.use_map_color_diffuse:
                    filepath = ts.texture.image.filepath
                    filename = os.path.split(filepath)[1]
                    if len(filename) == 0:
                        filename = "untitled"
                        #raise(ValueError)
                    break
            else:
                raise(ValueError)
                
        except:
            continue
        
        if use_version == '5':
            cache += "MATERIAL %i \"%s\"" % (c_materials, filename)
            # or is it mat.name@filename?
        else:
            cache += "MATERIAL %i \"%s\" \"%s\" \"%s\"\n" % (
                     c_materials,
                     mat.name,
                     mat.diffuse_shader.capitalize(),
                     filename
                     )
            cache += material_string
        c_materials += 1

    if c_materials > 0:
        file.write("\nNUMMATERIALS %i\n" % c_materials)
        file.write(cache)
    else:
        # Write a default material
        file.write("\nNUMMATERIALS 1\n")
        if use_version == '5':
            file.write("MATERIAL 0 \"default.tga\"\n")
        else:
            file.write("MATERIAL 0 \"$default\" \"Lambert\" \"untitled\"\n")
            file.write(material_string)

    # Close to flush buffers!
    file.close()

    # Set mode back
    bpy.ops.object.mode_set(mode=last_mode, toggle=False)
    
    # Quit with no errors
    return
    
    
# Taken from export_fbx.py by Campbell Barton
# Modified to accept vertex_groups directly instead of mesh object
def BPyMesh_meshWeight2List(vgroup, me):
    
    """ Takes a mesh and return its group names and a list of lists, one list per vertex.
    aligning the each vert list with the group names, each list contains float value for the weight.
    These 2 lists can be modified and then used with list2MeshWeight to apply the changes.
    """

    # Clear the vert group.
    groupNames = [g.name for g in vgroup]
    len_groupNames = len(groupNames)

    if not len_groupNames:
        # no verts? return a vert aligned empty list
        #return [[] for i in range(len(me.vertices))], []
        return [], []
        
    else:
        vWeightList = [[0.0] * len_groupNames for i in range(len(me.vertices))]

    for i, v in enumerate(me.vertices):
        for g in v.groups:
            # possible weights are out of range
            index = g.group
            if index < len_groupNames:
                vWeightList[i][index] = g.weight

    return groupNames, vWeightList


def meshNormalizedWeights(vgroup, me):

    groupNames, vWeightList = BPyMesh_meshWeight2List(vgroup, me)

    if not groupNames:
        return [], []

    for vWeights in vWeightList:
        tot = 0.0
        for w in vWeights:
            if w < weight_min:
                w = 0.0
            tot += w

        if tot:
            for j, w in enumerate(vWeights):
                vWeights[j] = w / tot

    return groupNames, vWeightList