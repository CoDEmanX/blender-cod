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

plugin_preferences = None


def get_metadata_string(filepath):
    import bpy
    msg = "// Exported using Blender v%s\n" % bpy.app.version_string
    msg += "// Export filename: '%s'\n" % filepath.replace("\\", "/")
    if bpy.data.filepath is None:
        source_file = "<none>"
    else:
        source_file = bpy.data.filepath.replace('\\', '/')
    msg += "// Source filename: '%s'\n" % source_file
    return msg


def calculate_unit_scale_factor(scene, apply_unit_scale=False):
    '''
    Calcualte the conversion factor to convert from
     Blender units (Usually 1 meter) to inches (CoD units).
    If no explicit unit system is set in the scene settings, we fallback to the
     global Blender-CoD scale units. If that option is disabled we use a 1:1
     scale factor to convert from Blender Units to Inches
     (Assuming 1 BU is 1 inch)
    '''
    if not apply_unit_scale:
        return 1.0

    if scene.unit_settings.system != 'NONE':
        return plugin_preferences.scale_length / 0.0254
    else:
        return scene.unit_settings.scale_length / 0.0254
