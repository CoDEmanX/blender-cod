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

import os
import bpy
import bmesh
import array
from mathutils import *
from math import *
from bpy_extras.image_utils import load_image

from . import shared as shared
from .PyCoD import xmodel as XModel


def get_armature_for_object(ob):
    '''
    Get the armature for a given object.
    If the object *is* an armature, the object itself is returned.
    '''
    if ob is None:
        return None

    if ob.type == 'ARMATURE':
        return ob

    return ob.find_armature()


def get_armature_modifier_for_object(ob):
    for mod in ob.modifiers:
        if mod.type == 'ARMATURE':
            return mod
    return None


def reassign_children(ebs, bone1, bone2):
    for child in bone2.children:
        kid = ebs[child.name]
        kid.parent = bone1

    ebs.remove(bone2)


def join_objects(obs):
    scene = bpy.context.scene
    context = bpy.context.copy()
    context['active_object'] = obs[0]
    context['selected_objects'] = obs

    editable_bases = [scene.object_bases[ob.name] for ob in obs]
    context['selected_editable_bases'] = editable_bases
    bpy.ops.object.join(context)


def join_armatures(skel1_ob, skel2_ob, skel2_mesh_obs):
    skel2_mesh_matrices = [mesh.matrix_world.copy() for mesh in skel2_mesh_obs]

    join_objects([skel1_ob, skel2_ob])

    # Ensure that the context is correct
    bpy.context.scene.objects.active = skel1_ob
    skel1_ob.select_set(state=True)

    bpy.ops.object.mode_set(mode='EDIT')
    ebs = skel1_ob.data.edit_bones

    # Reassign all children for any bones that were present in both skeletons
    for bone in ebs:
        try:
            t = ebs[bone.name + ".001"]
            reassign_children(ebs, bone, t)
        except:
            pass

    # Remove the move the duplicates
    for bone in ebs:
        if(bone.name.endswith(".001")):
            ebs.remove(bone)

    if 'j_gun' in ebs and 'tag_weapon' in ebs:
        ebs['j_gun'].parent = ebs['tag_weapon']
    elif 'tag_weapon' in ebs and 'tag_weapon_right' in ebs:
        ebs['tag_weapon'].parent = ebs['tag_weapon_right']

    bpy.ops.object.mode_set(mode='OBJECT')

    # Update the matrices and armature modifier for the mesh objects
    for mesh_ob, matrix in zip(skel2_mesh_obs, skel2_mesh_matrices):
        mesh_ob.matrix_world = matrix
        mod = get_armature_modifier_for_object(mesh_ob)
        if mod is not None:
            # Update the existing armature modifier
            mod.object = skel1_ob
        else:
            # Add a new armature modifier
            mod = mesh_ob.modifiers.new('Armature Rig', 'ARMATURE')
            mod.object = skel1_ob
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True


def load(self, context,
         filepath,
         global_scale=1.0,
         apply_unit_scale=False,
         use_single_mesh=True,
         use_dup_tris=True,
         use_custom_normals=True,
         use_vertex_colors=True,
         use_armature=True,
         use_parents=True,
         attach_model=False,
         merge_skeleton=False,
         use_image_search=True):

    # Apply unit conversion factor to the scale
    if apply_unit_scale:
        global_scale *= shared.calculate_unit_scale_factor(context.scene)

    target_scale = global_scale

    if use_armature is False:
        attach_model = False

    skel_old = get_armature_for_object(context.active_object)
    if skel_old is None:
        attach_model = False

    if not attach_model:
        merge_skeleton = False

    split_meshes = not use_single_mesh
    load_images = True

    scene = bpy.context.scene
    view_layer = bpy.context.view_layer

    # Load the model
    model_name = os.path.basename(filepath)
    model = XModel.Model(('.').join(model_name.split('.')[:-1]))

    ext = os.path.splitext(filepath)[-1].upper()
    if ext == '.XMODEL_BIN':
        LoadModelFile = model.LoadFile_Bin
    else:
        LoadModelFile = model.LoadFile_Raw

    LoadModelFile(filepath, split_meshes=split_meshes)

    # Materials
    # List of the materials that Blender has loaded
    materials = []
    # Map of images to their instances in Blender
    #  (or None if they failed to load)
    material_images = {}

    for material in model.materials:
        mat = bpy.data.materials.get(material.name)
        if mat is None:
            print("Adding material '%s'" % material.name)
            mat = bpy.data.materials.new(name=material.name)

            # mat.diffuse_shader = 'LAMBERT'
            # mat.specular_shader = 'PHONG'

            # Load the textures for this material - TODO: Cycles Support
            if load_images:
                # Load the actual image files
                # Color maps get deferred to after the other textures
                deferred_textures = []
                for image_type, image_name in material.images.items():
                    if image_name not in material_images:
                        search_dir = os.path.dirname(filepath)
                        image = load_image(image_name,
                                           dirname=search_dir,
                                           recursive=use_image_search,
                                           check_existing=True)
                        if image is None:
                            print("Failed to load image: '%s'" % image_name)
                            # Create a placeholder image for the one that
                            # failed to load
                            image = load_image(image_name,
                                               dirname=None,
                                               recursive=False,
                                               check_existing=True,
                                               place_holder=True)
                        material_images[image_name] = image
                    elif image_name in bpy.data.images:
                        image = bpy.data.images[image_name]
                    else:
                        image = material_images[image_name]

                    # DEPRECATED
                    '''
                    # Create the texture - We exclude the extension in the
                    #  texture name
                    texture_name = os.path.splitext(image_name)[0]
                    if texture_name in bpy.data.textures:
                        tex = bpy.data.textures[texture_name]
                    else:
                        tex = bpy.data.textures.new(texture_name, 'IMAGE')
                        tex.image = image

                    if image_type == 'color':
                        deferred_textures.append(tex)
                        continue
                    else:
                        slot = mat.texture_slots.add()
                        slot.texture = tex
                        slot.use_map_color_diffuse = False
                        slot.use_map_alpha = False
                        if image_type == 'normal':
                            slot.normal_factor = True
                    '''

                # DEPRECATED
                '''
                # Add the deferred_textures
                for tex in deferred_textures:
                    slot = mat.texture_slots.add()
                    slot.texture = tex
                    slot.use_map_color_diffuse = True
                    if tex.image is not None and tex.image.channels > 3:
                        # Enable Transparency
                        slot.use_map_alpha = True
                        slot.alpha_factor = 1.0
                        # NOTE: Decide when use_transparency is needed
                        #       I haven't been able to figure out a way
                        #        to deterime this
                        mat.use_transparency = True
                        mat.transparency_method = 'Z_TRANSPARENCY'
                        # Prevent specular from showing on transparent parts
                        # NOTE: 'RAYTRACE' transparency_method has specular
                        #        highlights show up regardless
                        mat.specular_alpha = 0.0
                    mat.alpha = 0
                '''

        else:
            if mat not in materials:
                print("Material '%s' already exists!" % material.name)
        materials.append(mat)

    # Meshes
    mesh_objs = []  # Mesh objects that we're going to link the skeleton to
    for sub_mesh in model.meshes:
        if split_meshes is False:
            sub_mesh.name = "%s_mesh" % model.name
        print("Creating mesh: '%s'" % sub_mesh.name)
        mesh = bpy.data.meshes.new(sub_mesh.name)
        bm = bmesh.new()

        # Add UV Layers
        uv_layer = bm.loops.layers.uv.new("UVMap")

        # Add Vertex Color Layer
        if use_vertex_colors:
            vert_color_layer = bm.loops.layers.color.new("Color")

        # Add Verts
        for vert in sub_mesh.verts:
            bm.verts.new(Vector(vert.offset) * target_scale)
        bm.verts.ensure_lookup_table()

        # Contains data for faces that use the same 3 verts as an existing face
        #  (usually caused by `double sided` tris)
        dup_faces = []
        dup_verts = []

        # Contains vertex mapping data for all verts that the dup faces use
        dup_verts_mapping = [None] * len(sub_mesh.verts)

        used_faces = []  # List of all faces that were used in the model

        loop_normals = []  # List of normals for every added loop (face vertex)

        # Tracks how many faces in the current mesh use a given material
        material_usage_counts = [0] * len(materials)

        # Inner function used set up a bmesh tri's normals (into loop_normals),
        #  uv, materials, etc.
        def setup_tri(f):
            # Assign the face's material & increment the material usage counter
            material_index = face.material_id
            f.material_index = material_index

            material_usage_counts[material_index] += 1

            # Assign the face's UV layer
            for loop_index, loop in enumerate(f.loops):
                face_index_loop = face.indices[loop_index]
                # Normal
                loop_normals.append(face_index_loop.normal)
                # UV Coordinate Correction
                uv = Vector(face_index_loop.uv)
                uv.y = 1.0 - uv.y
                loop[uv_layer].uv = uv
                # Vertex Colors
                if use_vertex_colors:
                    loop[vert_color_layer] = face_index_loop.color

            used_faces.append(face)

        unused_faces = []

        vert_count = len(sub_mesh.verts)
        for face_index, face in enumerate(sub_mesh.faces):
            # Fix the winding order
            tmp = face.indices[2]
            face.indices[2] = face.indices[1]
            face.indices[1] = tmp

            indices = [bm.verts[index.vertex] for index in face.indices]

            try:
                f = bm.faces.new(indices)
            except ValueError:
                # Mark the face as unused
                unused_faces.append(face)

                if not face.isValid():
                    print("TRI %d is invalid! %s" %
                          (face_index, [index.vertex for index in face.indices]))
                    continue

                for index in face.indices:
                    vert = index.vertex
                    if dup_verts_mapping[vert] is None:
                        dup_verts_mapping[vert] = len(dup_verts) + vert_count
                        dup_verts.append(sub_mesh.verts[vert])
                    index.vertex = dup_verts_mapping[vert]
                dup_faces.append(face)
            else:
                setup_tri(f)

        # Remove the unused tris so they aren't accidentally used later
        for face in unused_faces:
            sub_mesh.faces.remove(face)

        if use_dup_tris:
            for vert in dup_verts:
                bm.verts.new(Vector(vert.offset) * target_scale)
            bm.verts.ensure_lookup_table()

            for face in dup_faces:
                indices = [bm.verts[index.vertex] for index in face.indices]
                try:
                    f = bm.faces.new(indices)
                except ValueError:
                    pass  # Skip dups of dups
                else:
                    setup_tri(f)

        # Vertex Weights
        deform_layer = bm.verts.layers.deform.new()
        for vert_index, vert in enumerate(sub_mesh.verts):
            for bone, weight in vert.weights:
                bm.verts[vert_index][deform_layer][bone] = weight

        if use_dup_tris:
            offset = len(sub_mesh.verts)
            for vert_index, vert in enumerate(dup_verts):
                for bone, weight in vert.weights:
                    bm.verts[vert_index + offset][deform_layer][bone] = weight

        # Assign Materials
        for mat in materials:
            mesh.materials.append(mat)

        bm.to_mesh(mesh)

        # For this mesh remove all materials that aren't used by its faces
        # material_index, material_usage_index must be tracked manually because
        # enumerate() doesn't compensate for the removed materials properly
        material_index = 0
        material_usage_index = 0
        for material in mesh.materials:
            if material_usage_counts[material_usage_index] == 0:
                # Note: update_data must be True, otherwise - after the first
                #  material is removed, the indices are invalidated
                mesh.materials.pop(index=material_index, update_data=True)
            else:
                material_index += 1
            material_usage_index += 1

        # Custom Normals
        if use_custom_normals:
            # Store 'temp' normals in loops, since validate() may alter the
            #  final mesh.
            # We can only set custom loop normals *after* calling it.
            mesh.create_normals_split()

            # Iterate over every single loop (every vert for every face)
            for loop_index, loop in enumerate(mesh.loops):
                mesh.loops[loop_index].normal = loop_normals[loop_index]

            # *Very* important to not remove loop normals here!
            mesh.validate(clean_customdata=False)

            # mesh.free_normals_split() # Is this necessary?

            clnors = array.array('f', [0.0] * (len(mesh.loops) * 3))
            mesh.loops.foreach_get("normal", clnors)

            # Enable Smoothing - must be BEFORE normals_split_custom_set, etc.
            polygon_count = len(mesh.polygons)
            mesh.polygons.foreach_set("use_smooth", [True] * polygon_count)

            mesh.normals_split_custom_set(tuple(zip(*(iter(clnors),) * 3)))
            mesh.use_auto_smooth = True

            # This was used to highlight sharp edges in legacy versions
            # In Blender 2.8x, it uses the View3D Overlay API - but since
            # it's enabled by default in those versions, we don't need any
            # special code
            # mesh.show_edge_sharp = True

        else:
            mesh.validate()

            # Enable Smoothing
            polygon_count = len(mesh.polygons)
            mesh.polygons.foreach_set("use_smooth", [True] * polygon_count)

            # Use Auto-generated Normals
            mesh.calc_normals()

        if split_meshes:
            obj_name = "%s_%s" % (model.name, mesh.name)
        else:
            obj_name = model.name

        # Create the model object and link it to the scene
        obj = bpy.data.objects.new(obj_name, mesh)
        mesh_objs.append(obj)

        scene.collection.objects.link(obj)
        view_layer.objects.active = obj

        # Create Vertex Groups
        # These automatically weight the verts based on the deform groups
        for bone in model.bones:
            obj.vertex_groups.new(name=bone.name.lower())

        # Assign the texture images to the current mesh (for Texture view)
        if load_images:
            # Build a material_id to Blender image map
            material_image_map = [None] * len(model.materials)
            for index, material in enumerate(model.materials):
                if 'color' in material.images:
                    color_map = material.images['color']
                    if color_map in bpy.data.images:
                        material_image_map[index] = bpy.data.images[color_map]

            # DEPRECATED
            '''
            # Assign the image for each face
            uv_faces = mesh.uv_textures[0].data
            for index, face in enumerate(used_faces):
                uv_faces[index].image = material_image_map[face.material_id]
            '''

    if use_armature:
        # Create the skeleton
        armature = bpy.data.armatures.new("%s_amt" % model.name)
        armature.display_type = "STICK"

        skel_obj = bpy.data.objects.new("%s_skel" % model.name, armature)
        skel_obj.show_in_front = True

        # Add the skeleton object to the scene
        scene.collection.objects.link(skel_obj)
        view_layer.objects.active = skel_obj

        bpy.ops.object.mode_set(mode='EDIT')

        for bone in model.bones:
            edit_bone = armature.edit_bones.new(bone.name.lower())
            edit_bone.use_local_location = False

            offset = Vector(bone.offset) * target_scale
            axis = Vector(bone.matrix[1]) * target_scale
            roll = Vector(bone.matrix[2])

            edit_bone.head = offset
            edit_bone.tail = offset + axis
            edit_bone.align_roll(roll)

            if bone.parent != -1:
                parent = armature.edit_bones[bone.parent]
                if self.use_parents is True:
                    edit_bone.parent = parent

        # HACK: Force the pose bone list for the armature to be rebuilt
        bpy.ops.object.mode_set(mode='OBJECT')

        # Add the armature modifier to each mesh object
        for mesh_obj in mesh_objs:
            mesh_obj.parent = skel_obj
            modifier = mesh_obj.modifiers.new('Armature Rig', 'ARMATURE')
            modifier.object = skel_obj
            modifier.use_bone_envelopes = False
            modifier.use_vertex_groups = True

        # Attach the new skeleton to the existing one
        if attach_model and skel_old is not None:
            """
            if 'tag_weapon' in skel_old.pose.bones:
                arm_is_active = True
                bpy.ops.object.mode_set(mode='EDIT')
                matrix = skel_old.pose.bones["tag_weapon"].matrix.copy()
                tag_weapon_mat = matrix
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                arm_is_active = False
            """

            if attach_model:
                skel_obj.parent = skel_old
            if skel_obj.pose.bones[0].name == "j_gun":
                skel_obj.parent_bone = "tag_weapon"
            elif skel_obj.pose.bones[0].name == "tag_weapon":
                 # Todo - add option to manually specify whether or not the user
                 #        wants to attach to the left or right hand
                skel_obj.parent_bone = "tag_weapon_right"
            else:
                if skel_obj.pose.bones[0].name in skel_old.pose.bones:
                    skel_obj.parent_bone = skel_obj.pose.bones[0].name
                else:
                    print(("Warning: Armature '%s' may not"
                           "merge correctly with '%s'") %
                          (skel_obj.name, skel_old.name))
                    skel_obj.parent_bone = skel_old.pose.bones[0].name
            skel_obj.parent_type = 'BONE'
            skel_obj.location = (0, -1, 0)

            # Is this necessary?
            bpy.context.view_layer.update()

            # Merge the skeletons together
            if merge_skeleton:
                join_armatures(skel_old, skel_obj, mesh_objs)
                bpy.ops.object.mode_set(mode='POSE')

    # view_layer.update()
    bpy.ops.object.mode_set(mode='OBJECT')
