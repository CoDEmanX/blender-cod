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
from mathutils import *

from . import shared as shared
from .PyCoD import xanim as XAnim


def get_mat_offs(bone):
    # Based on the following: http://blender.stackexchange.com/a/44980
    mat_offs = bone.matrix.to_4x4()
    mat_offs.translation = bone.head
    mat_offs.translation.y += bone.parent.length

    return mat_offs


def get_mat_rest(pose_bone, mat_pose_parent, mat_local_parent):
    # Based on the following: http://blender.stackexchange.com/a/44980
    bone = pose_bone.bone

    if pose_bone.parent:
        mat_offs = get_mat_offs(bone)

        # --------- rotscale
        if (not bone.use_inherit_rotation and not bone.use_inherit_scale):
            mat_rotscale = mat_local_parent @ mat_offs

        elif not bone.use_inherit_rotation:
            mat_size = Matrix.Identity(4)
            for i in range(3):
                mat_size[i][i] = mat_pose_parent.col[i].magnitude
            mat_rotscale = mat_size @ mat_local_parent @ mat_offs

        elif not bone.use_inherit_scale:
            mat_rotscale = mat_pose_parent.normalized() @ mat_offs

        else:
            mat_rotscale = mat_pose_parent @ mat_offs

        # --------- location
        if not bone.use_local_location:
            mat_a = Matrix.Translation(mat_pose_parent @ mat_offs.translation)

            mat_b = mat_pose_parent.copy()
            mat_b.translation = Vector()

            mat_loc = mat_a @ mat_b

        elif (not bone.use_inherit_rotation or not bone.use_inherit_scale):
            mat_loc = mat_pose_parent @ mat_offs

        else:
            mat_loc = mat_rotscale.copy()

    else:
        mat_rotscale = bone.matrix_local
        if not bone.use_local_location:
            mat_loc = Matrix.Translation(bone.matrix_local.translation)
        else:
            mat_loc = mat_rotscale.copy()

    return mat_rotscale, mat_loc


def calc_basis(pose_bone, matrix, parent_mtx, parent_mtx_local):
    # Based on the following: http://blender.stackexchange.com/a/44980
    mat_rotscale, mat_loc = get_mat_rest(pose_bone,
                                         parent_mtx,
                                         parent_mtx_local)
    basis = (matrix.to_3x3().inverted() @ mat_rotscale.to_3x3()).transposed()
    basis.resize_4x4()
    basis.translation = mat_loc.inverted() @ matrix.translation
    return basis


def find_active_armature(context):
    ob = bpy.context.active_object
    if ob is None:
        return None

    if ob.type == 'ARMATURE':
        return ob

    return ob.find_armature()


def load(self, context, apply_unit_scale=False, **keywords):
    # Used to ensure that all anims are the same framerate when batch importing
    scale_framerate_to_match_first_anim = False

    if not keywords['use_notetracks']:
        keywords['use_notetrack_file'] = False
    # elif fps_scale_type is 'CUSTOM':
    #   we just use the argument fps_scale_target_fps

    # Apply unit conversion factor to the scale
    if apply_unit_scale:
        unit_scale_factor = shared.calculate_unit_scale_factor(context.scene)
        keywords['global_scale'] *= unit_scale_factor

    armature = find_active_armature(context)
    path = os.path.dirname(keywords['filepath'])

    if armature is None:
        return "No active armature found"

    # Ensure that the object has animation data
    if armature.animation_data is None:
        armature.animation_data_create()

    for i, f in enumerate(self.files):
        keywords['filepath'] = os.path.join(path, f.name)
        anim = load_anim(self, context, armature, **keywords)

        if type(anim) is XAnim.Anim:
            # All animations after the first one will have their framerate
            #  refactored to match the first one that we loaded in the loop
            if i == 0 and scale_framerate_to_match_first_anim:
                keywords['fps_scale_type'] = 'CUSTOM'
                keywords['fps_scale_target_fps'] = anim.framerate
                keywords['update_scene_fps'] = False


def load_anim(self, context, armature,
              filepath,
              global_scale=1.0,
              use_actions=True,
              use_actions_skip_existing=False,
              use_notetracks=True,
              use_notetrack_file=True,
              fps_scale_type='DISABLED',
              fps_scale_target_fps=30,
              update_scene_fps=False,
              anim_offset=0
              ):
    '''
    Load a specific XAnim file
    returns the XAnim() on success or an error message / None on failure
    '''

    # TEMP: Used to update the scene frame range based on the anim
    update_scene_range = False

    # Load the anim
    anim = XAnim.Anim()
    ext = os.path.splitext(filepath)[-1].upper()
    if ext == '.XANIM_BIN':
        anim.LoadFile_Bin(filepath)
    else:
        anim.LoadFile_Raw(filepath, use_notetrack_file)

    scene = context.scene
    ob = armature

    bpy.ops.object.mode_set(mode='POSE')

    if use_actions:
        actionName = os.path.basename(os.path.splitext(filepath)[0])

        # Skip existing actions
        if use_actions_skip_existing and actionName in bpy.data.actions:
            # Should we print a notification here?
            return

        action = bpy.data.actions.new(actionName)
        ob.animation_data.action = action
        ob.animation_data.action.use_fake_user = True

    if update_scene_fps:
        scene.render.fps = anim.framerate

    if fps_scale_type == 'SCENE':
        fps_scale_target_fps = scene.render.fps

    if fps_scale_type == 'DISABLED':
        frame_scale = 1
    else:
        frame_scale = fps_scale_target_fps / anim.framerate

    if update_scene_range:
        frames = [frame.frame for frame in anim.frames]
        scene.frame_start = min(frames) * frame_scale
        scene.frame_end = max(frames) * frame_scale

        # Adjust the frame shift so that if the first frame doesn't move when
        #  the anim gets scaled, apply the anim_offset on top of that
        frame_shift = anim_offset - scene.frame_start
        scene.frame_start = scene.frame_start - frame_shift
        scene.frame_end = scene.frame_end - frame_shift
    else:
        frame_shift = anim_offset

    # Used to store bone metadata & matrix info for each animated bone
    class MappedBone(object):
        __slots__ = ('bone', 'part_index', 'matrix', 'matrix_local', 'parent')

        def __init__(self, pose_bone, part_index):
            self.bone = pose_bone
            self.part_index = part_index
            self.matrix = Matrix()
            self.matrix_local = pose_bone.bone.matrix_local
            self.parent = None

        def map_parent(self, bone_map):
            # Traverses the parents of the current bone recursively until -
            # one that is present in the anim is found
            # If none can be found, self.parent is set to None
            bone_names = [mapped_bone.bone.name for mapped_bone in bone_map]

            bone = self.bone
            while bone is not None:
                if bone.name in bone_names:
                    parent_index = bone_names.index(bone.name)
                    self.parent = bone_map[parent_index]
                    return
                bone = bone.parent
            self.parent = None
            return

    # Map the PoseBones to their corresponding part numbers, parents, etc.
    # The order of PoseBones in bone_map should match ob.pose.bones -
    # which stores them in hierarchical order, meaning a bone's parent -
    # will always be *earlier* in the list than the child
    bone_map = []
    part_names = [part.name.lower() for part in anim.parts]
    for bone_index, bone in enumerate(ob.pose.bones):
        if bone.name in part_names:
            part_index = part_names.index(bone.name)
            # Don't add bones that didn't have a matching part in the anim
            if part_index is not None:
                mapped_bone = MappedBone(bone, part_index)
                mapped_bone.map_parent(bone_map)

                bone_map.append(mapped_bone)
            else:
                # If the bone isn't used in the anim
                #  simply reset it to its rest pose
                bone.matrix_basis.identity()

    # Load the keyframes
    for frame in anim.frames:
        f = frame.frame * frame_scale + frame_shift

        for mapped_bone in bone_map:
            # Because a bone's parent is always *before* the child in bone_map
            #  it should always have an valid parent matrix
            #  (unless there is no parent)
            mapped_bone_parent = mapped_bone.parent
            if mapped_bone_parent is not None:
                parent_matrix = mapped_bone_parent.matrix
                parent_local_matrix = mapped_bone_parent.matrix_local
            else:
                parent_matrix = Matrix()
                parent_local_matrix = parent_matrix

            part = frame.parts[mapped_bone.part_index]
            mtx = Matrix(part.matrix).transposed().to_4x4()
            mtx.translation = Vector(part.offset) * global_scale

            # Store this bone's current matrix for its children to access
            mapped_bone.matrix = mtx.copy()

            bone = mapped_bone.bone
            matrix_basis = calc_basis(bone,
                                      mtx,
                                      parent_matrix,
                                      parent_local_matrix)
            bone.matrix_basis = matrix_basis.copy()

            bone.keyframe_insert("location", index=-1, frame=f)
            bone.keyframe_insert("rotation_quaternion", index=-1, frame=f)

    # Load the notes
    if use_notetracks:
        if use_actions:
            markers = action.pose_markers
        else:
            markers = context.scene.timeline_markers

        for anim_note in anim.notes:
            name = anim_note.string
            frame = anim_note.frame * frame_scale - frame_shift
            note = markers.new(name, frame=frame)

    context.view_layer.update()
    return anim
