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

import bpy
import bmesh
import os
from itertools import repeat

from . import shared as shared
from .PyCoD import xmodel as XModel


def _skip_notice(ob_name, mesh_name, notice):
    vargs = (ob_name, mesh_name, notice)
    print("\nSkipped object \"%s\" (mesh \"%s\"): %s" % vargs)


def mesh_triangulate(mesh, vertex_cleanup):
    '''
    Based on the function in export_obj.py
    Note: This modifies the passed mesh
    '''

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    if vertex_cleanup:
        bmesh.ops.split(bm, use_only_faces=True)
    bm.to_mesh(mesh)
    bm.free()

    mesh.update(calc_tessface=True)


def gather_exportable_objects(self, context,
                              use_selection,
                              use_armature,
                              use_armature_filter=True,
                              quiet=True):
    '''
    Gather relevent objects for export
    Returns a tuple in the format (armature, [objects])

    Args:
        use_selection - Only export selected objects
        use_armature - Include the armature
        use_armature_filter - Only export meshes that are influenced by the active armature
        Automatically include all objects that use the
                              active armature?
    '''  # nopep8

    armature = None
    obs = []

    # Do a quick check to see if the active object is an armature
    #  If it is - use it as the target armature
    if (context.active_object is not None and
            context.active_object.type == 'ARMATURE'):
        armature = context.active_object

    # A list of objects we need to check *after* we find an armature
    # Used when use_armature_filter is enabled because we can't check
    #  the modifiers if we don't know what armature we're using yet
    secondary_objects = []

    def test_armature_filter(object):
        """
        Test an object against the armature filter
        returns True if the object passed
        returns false if the object failed the test
        """
        for modifier in ob.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object == armature:
                return True
        return False

    for ob in bpy.data.objects:
        # Either grab the active armature - or the first armature in the scene
        if (ob.type == 'ARMATURE' and use_armature and
            (armature is None or ob == context.active_object) and
                len(ob.data.bones) > 0):
            armature = ob
            continue

        if ob.type != 'MESH':
            continue

        if use_selection and not ob.select_get():
            continue

        if len(ob.material_slots) < 1:
            if not quiet:
                print("Object '%s' has no materials - skipping..." % ob.name)
            continue

        if use_armature_filter:
            if armature is None:
                # Defer the check for this object until *after* we know
                #  which armature we're using
                secondary_objects.append(ob)
            else:
                if test_armature_filter(ob):
                    obs.append(ob)
            continue
        obs.append(ob)

    # Perform a secondary filter pass on all objects we missed
    #  (before the armature was found)
    if use_armature_filter:
        for ob in secondary_objects:
            if test_armature_filter(ob):
                obs.append(ob)

    # Fallback to exporting only the selected object if we couldn't find any
    if armature is None:
        if len(obs) == 0 and context.active_object is not None:
            if ob.type == 'MESH':
                obs = [context.active_object]

    return armature, obs


def material_gen_image_dict(material):
    '''
    Generate a PyCoD compatible image dict from a given Blender material
    '''
    out = {}
    if not material:
        return out
    unk_count = 0
    for slot in material.texture_slots:
        if slot is None:
            continue
        texture = slot.texture
        if texture is None:
            continue
        if texture.type == 'IMAGE':
            try:
                tex_img = slot.texture.image
                if tex_img.source != 'FILE':
                    image = tex_img.name
                else:
                    image = os.path.basename(tex_img.filepath)
            except:
                image = "<undefined>"

            if slot.use_map_color_diffuse:
                out['color'] = image
            elif slot.use_map_normal:
                out['normal'] = image
            else:
                out['unk_%d' % unk_count] = image
                unk_count += 1
    return out


class ExportMesh(object):
    '''
    Internal class used for handling the conversion of mesh data into
    a PyCoD compatible format
    '''
    __slots__ = ('mesh', 'object', 'matrix', 'weights', 'materials')

    def __init__(self, obj, mesh, model_materials):
        self.mesh = mesh
        self.object = obj
        self.matrix = obj.matrix_world
        self.weights = [[] for i in repeat(None, len(mesh.vertices))]

        # Used to map mesh materials indices to our model material indices
        self.materials = []
        self.gen_material_indices(model_materials)

    def clear(self):
        self.mesh.user_clear()
        bpy.data.meshes.remove(self.mesh)

    def add_weights(self, bone_table, weight_min_threshold=0.0):
        ob = self.object
        if ob.vertex_groups is None:
            for i in range(len(self.weights)):
                self.weights[i] = [(0, 1.0)]
        else:
            # group_map[group_index] yields bone index or None
            group_map = [None] * len(ob.vertex_groups)
            for group_index, group in enumerate(ob.vertex_groups):
                if group.name in bone_table:
                    group_map[group_index] = bone_table.index(group.name)

            for vert_index, vert in enumerate(self.mesh.vertices):
                for group in vert.groups:
                    bone_index = group_map[group.group]
                    if bone_index is not None:
                        if group.weight < weight_min_threshold:
                            continue  # Skip weights below the weight threshold
                        self.weights[vert_index].append(
                            (bone_index, group.weight))

            # Any verts without weights will get a 1.0 weight to the root bone
            for weights in self.weights:
                if len(weights) == 0:
                    weights.append((0, 1.0))

    def gen_material_indices(self, model_materials):
        self.materials = [None] * len(self.mesh.materials)
        for material_index, material in enumerate(self.mesh.materials):
            if material in model_materials:
                self.materials[material_index] = model_materials.index(material)  # nopep8
            else:
                self.materials[material_index] = len(model_materials)
                model_materials.append(material)

    def to_xmodel_mesh(self,
                       use_alpha=False,
                       use_alpha_mode='PRIMARY',
                       global_scale=1.0):

        mesh = XModel.Mesh(self.mesh.name)

        if self.mesh.has_custom_normals:
            self.mesh.calc_normals_split()
        else:
            self.mesh.calc_normals()

        uv_layer = self.mesh.uv_layers.active
        vc_layer = self.mesh.tessface_vertex_colors.active

        # Get the vertex layer to use for alpha
        if not use_alpha:
            vca_layer = None
        elif use_alpha_mode == 'PRIMARY':
            vca_layer = vc_layer
        elif use_alpha_mode == 'SECONDARY':
            vca_layer = vc_layer
            # Get the first vertex color layer that isn't active
            #  If one can't be found, fallback to the active layer
            for layer in self.mesh.tessface_vertex_colors:
                if layer is not vc_layer:
                    vca_layer = layer
                    break

        alpha_default = 1.0

        # mesh.calc_tessface()  # Is this needed?

        for vert_index, vert in enumerate(self.mesh.vertices):
            mesh_vert = XModel.Vertex()
            mesh_vert.offset = tuple(vert.co * global_scale)
            mesh_vert.weights = self.weights[vert_index]
            mesh.verts.append(mesh_vert)

        for polygon in self.mesh.polygons:
            face = XModel.Face(0, 0)
            face.material_id = self.materials[polygon.material_index]
            if vc_layer is not None:
                vert_colors = vc_layer.data[polygon.index]
                poly_colors = [vert_colors.color1,
                               vert_colors.color2, vert_colors.color3]

                # Calculate alpha values for the verts for this polygon
                if vca_layer is None:
                    alphas = [alpha_default] * 3
                else:
                    vert_colors = vca_layer.data[polygon.index]
                    alphas = [sum(vert_colors.color1) / 3,
                              sum(vert_colors.color2) / 3,
                              sum(vert_colors.color3) / 3]

                colors = [tuple(c) + (a,) for c, a in zip(poly_colors, alphas)]
            else:
                colors = [(1.0, 1.0, 1.0, alpha_default)] * 4
            for i, loop_index in enumerate(polygon.loop_indices):
                loop = self.mesh.loops[loop_index]
                uv = uv_layer.data[loop_index].uv
                vert = XModel.FaceVertex(
                    loop.vertex_index,
                    loop.normal,
                    colors[i],
                    (uv.x, 1.0 - uv.y))
                face.indices[i] = vert

            # Fix winding order (again)
            tmp = face.indices[2]
            face.indices[2] = face.indices[1]
            face.indices[1] = tmp

            mesh.faces.append(face)

        return mesh


def save(self, context, filepath,
         target_format='XMODEL_EXPORT',
         version='6',
         use_selection=False,
         global_scale=1.0,
         apply_unit_scale=False,
         apply_modifiers=True,
         modifier_quality='PREVIEW',
         use_vertex_colors=True,
         use_vertex_colors_alpha=True,
         use_vertex_colors_alpha_mode='SECONDARY',
         use_vertex_cleanup=False,
         use_armature=True,
         use_weight_min=False,
         use_weight_min_threshold=0.010097,
         ):

    # Disabled for now
    use_armature_pose = False
    use_frame_start = 0
    use_frame_end = 1

    # Apply unit conversion factor to the scale
    if apply_unit_scale:
        global_scale /= shared.calculate_unit_scale_factor(context.scene)

    # There's no context object right after object deletion, need to set one
    if context.object:
        last_mode = context.object.mode
    else:
        last_mode = 'OBJECT'

        for ob in bpy.data.objects:
            if ob.type == 'MESH':
                context.scene.objects.active = ob
                break
        else:
            return "No mesh to export."

    # HACK: Force an update, so that bone tree is properly sorted
    #  for hierarchy table export
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    # ob.update_from_editmode()  # Would this work instead?

    armature, objects = gather_exportable_objects(self, context,
                                                  use_selection,
                                                  use_armature,
                                                  quiet=False)

    # If we were unable to detect any valid rigged objects
    # we'll use the selected mesh.
    if len(objects) == 0:
        return "There are no objects to export"

    # Set up the argument keywords for save_model
    keywords = {
        "target_format": target_format,
        "version": int(version),
        "global_scale": global_scale,
        "apply_modifiers": apply_modifiers,
        "modifier_quality": modifier_quality,
        "use_vertex_colors": use_vertex_colors,
        "use_vertex_colors_alpha": use_vertex_colors_alpha,
        "use_vertex_colors_alpha_mode": use_vertex_colors_alpha_mode,
        "use_vertex_cleanup": use_vertex_cleanup,
        "use_armature": use_armature & (not use_armature_pose),
        "use_weight_min": use_weight_min,
        "use_weight_min_threshold": use_weight_min_threshold,
    }

    # Export single model
    if not use_armature_pose:
        result = save_model(self, context, filepath,
                            armature, objects, **keywords)

    # Export pose models
    else:
        # Remember frame to set it back after export
        last_frame_current = context.scene.frame_current

        # Determine how to iterate over the frames
        if use_frame_start < use_frame_end:
            frame_order = 1
            frame_min = use_frame_start
            frame_max = use_frame_end
        else:
            frame_order = -1
            frame_min = use_frame_end
            frame_max = use_frame_start

        # String length of highest frame number for filename padding
        frame_strlen = len(str(frame_max))

        filepath_split = os.path.splitext(self.filepath)

        frame_range = range(
            use_frame_start, use_frame_end + frame_order, frame_order)
        for i_frame, frame in enumerate(frame_range, frame_min):
            # Set frame for export - Don't do it directly to frame_current,
            #  as to_mesh() won't use updated frame!
            context.scene.frame_set(frame)

            # Generate filename including padded frame number
            vargs = (filepath_split[0], frame_strlen,
                     i_frame, filepath_split[1])
            filepath_frame = "%s_%.*i%s" % vargs

            # Disable Armature for Pose animation export
            #  bone.tail_local not available for PoseBones
            result = save_model(self, context, filepath_frame,
                                armature, objects, **keywords)

            # Abort on error
            if result is not None:
                context.scene.frame_set(last_frame_current)
                return result

        # Restore the frame the scene was at before we started exporting
        context.scene.frame_set(last_frame_current)

    # Restore mode to its previous state
    bpy.ops.object.mode_set(mode=last_mode, toggle=False)

    return result


def save_model(self, context, filepath, armature, objects,
               target_format,
               version,
               global_scale,
               apply_modifiers,
               modifier_quality,
               use_vertex_colors,
               use_vertex_colors_alpha,
               use_vertex_colors_alpha_mode,
               use_vertex_cleanup,
               use_armature,
               use_weight_min,
               use_weight_min_threshold,
               ):
    # Disabled
    use_armature_pose = False

    scene = context.scene

    model = XModel.Model("$export")

    meshes = []
    materials = []

    for ob in objects:
        # Set up modifiers whether to apply deformation or not
        mod_states = []
        for mod in ob.modifiers:
            mod_states.append(mod.show_viewport)
            if mod.type == 'ARMATURE':
                mod.show_viewport = (mod.show_viewport and
                                     use_armature_pose)
            else:
                mod.show_viewport = (mod.show_viewport and
                                     apply_modifiers)

        # to_mesh() applies enabled modifiers only
        try:
            # NOTE There's no way to get a 'render' depsgraph for now
            depsgraph = context.evaluated_depsgraph_get()
            mesh = ob.evaluated_get(depsgraph).to_mesh()
        except RuntimeError:
            mesh = None

        if mesh is None:
            continue

        # Triangulate the mesh (Appears to keep split normals)
        #  Also remove all loose verts (Vertex Cleanup)
        mesh_triangulate(mesh, use_vertex_cleanup)

        # Should we have an arg for this? It seems to be automatic...
        use_split_normals = True
        if use_split_normals:
            mesh.calc_normals_split()

        # Restore modifier settings
        for i, mod in enumerate(ob.modifiers):
            mod.show_viewport = mod_states[i]

        # Skip invalid meshes
        if len(mesh.vertices) < 3:
            _skip_notice(ob.name, mesh.name, "Less than 3 vertices")
            mesh.user_clear()
            bpy.data.meshes.remove(mesh)
            continue
        if len(mesh.tessfaces) < 1:
            _skip_notice(ob.name, mesh.name, "No faces")
            mesh.user_clear()
            bpy.data.meshes.remove(mesh)
            continue

        if not mesh.tessface_uv_textures:
            _skip_notice(ob.name, mesh.name, "No UV texture, not unwrapped?")
            mesh.user_clear()
            bpy.data.meshes.remove(mesh)
            continue

        meshes.append(ExportMesh(ob, mesh, materials))

    # Build the bone hierarchy & transform matrices
    if use_armature and armature is not None:
        armature_matrix = armature.matrix_world
        bone_table = [b.name for b in armature.data.bones]
        for bone_index, bone in enumerate(armature.data.bones):
            if bone.parent is not None:
                if bone.parent.name in bone_table:
                    bone_parent_index = bone_table.index(bone.parent.name)
                else:
                    # TODO: Add some sort of useful warning for when we try
                    #  to export a bone that isn't actually in the bone table
                    print("WARNING")
                    bone_parent_index = 0
            else:
                bone_parent_index = -1

            model_bone = XModel.Bone(bone.name, bone_parent_index)

            # Is this the way to go?
            #  Or will it fix the root only, but mess up all other roll angles?
            if bone_index == 0:
                matrix = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
                offset = (0, 0, 0)
            else:
                mtx = (armature_matrix @
                       bone.matrix_local).to_3x3().transposed()
                matrix = [tuple(mtx[0]), tuple(mtx[1]), tuple(mtx[2])]
                offset = (armature_matrix @ bone.head_local) * global_scale

            model_bone.offset = tuple(offset)
            model_bone.matrix = matrix
            model.bones.append(model_bone)
    else:
        # If there are no bones, or there is no armature
        #  create a dummy bone for tag_pos
        dummy_bone_name = "tag_origin"
        dummy_bone = XModel.Bone(dummy_bone_name, -1)
        dummy_bone.offset = (0, 0, 0)
        dummy_bone.matrix = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
        model.bones.append(dummy_bone)
        bone_table = [dummy_bone_name]

    # Generate bone weights for verts
    if not use_weight_min:
        use_weight_min_threshold = 0.0
    for mesh in meshes:
        mesh.add_weights(bone_table, use_weight_min_threshold)
        model.meshes.append(
            mesh.to_xmodel_mesh(use_vertex_colors_alpha,
                                use_vertex_colors_alpha_mode,
                                global_scale))

    missing_count = 0
    for material in materials:
        imgs = material_gen_image_dict(material)
        try:
            name = material.name
        except:
            name = "material" + str(missing_count)
            missing_count = missing_count + 1

        mtl = XModel.Material(name, "Lambert", imgs)
        model.materials.append(mtl)

    header_msg = shared.get_metadata_string(filepath)
    if target_format == 'XMODEL_BIN':
        model.WriteFile_Bin(filepath, version=version,
                            header_message=header_msg)
    else:
        model.WriteFile_Raw(filepath, version=version,
                            header_message=header_msg)

    # Remove meshes, which were made by to_mesh()
    for mesh in meshes:
        mesh.clear()

    # Do we need this view_layer.update?
    context.view_layer.update()
