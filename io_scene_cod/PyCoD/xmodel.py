# <pep8 compliant>

from itertools import repeat
from time import strftime
from math import sqrt

import re

from .xbin import XBinIO, validate_version


def __clamp_float__(value, clamp_range=(-1.0, 1.0)):
    return max(min(value, clamp_range[1]), clamp_range[0])


def __clamp_multi__(value, clamp_range=(-1.0, 1.0)):
    return tuple([max(min(v, clamp_range[1]), clamp_range[0]) for v in value])

# Black Ops Note
#  NORMAL 0.0 0.0 0.000000000000000000001 <works fine>
#  NORMAL 0.0 0.0 0.0000000000000000000001 <assert>
#  NORMAL 0.0 0.0 0.00000000000000000000001 <Vertex normal = 0 error>


def __clamp_normal__(value):
    value = __clamp_multi__(value)
    if sum([abs(v) for v in value]) == 0:
        return (0.0, 0.0, 1.0)
    return value


def __normalized__(iterable):
    d = 1.0 / sqrt(sum([v * v for v in iterable]))
    return [v * d for v in iterable]


def deserialize_image_string(ref_string):
    if not ref_string:
        return {"color": "$none.tga"}

    out = {}
    for key, value in re.findall(r'\s*(\S+?)\s*:\s*(\S+)\s*', ref_string):
        out[key.lower()] = value.lstrip()

    if not out:
        out = {"color": ref_string}
    return out


def serialize_image_string(image_dict, extended_features=True):
    if extended_features is True:
        out = ""
        prefix = ''
        for key, value in image_dict.items():
            out += "%s%s:%s" % (prefix, key, value)
            prefix = ' '
        return out
    else:
        # For xmodel_export version 5, the material name and image ref
        #  may be the same -
        # in which case - the image dict extension shouldn't be used
        if 'color' in image_dict:  # use the color map
            return image_dict['color']
        elif image_dict != 0:  # if it cant be found, grab the first image
            key, value = image_dict.items()[0]
            return value
        return ""


class Bone(object):
    __slots__ = ('name', 'parent', 'offset', 'matrix', 'scale', 'cosmetic')

    def __init__(self, name, parent=-1, cosmetic=False):
        self.name = name
        self.parent = parent
        self.offset = None
        self.matrix = [None] * 3
        self.scale = (1.0, 1.0, 1.0)
        self.cosmetic = cosmetic


class Vertex(object):
    __slots__ = ("offset", "weights")

    def __init__(self, offset=None, weights=None):
        self.offset = offset
        if weights is None:
            # An array of tuples in the format (bone index, influence)
            self.weights = []
        else:
            self.weights = weights

    def __load_vert__(self, file, vert_count, mesh, vert_tok='VERT'):
        lines_read = 0
        state = 0

        vert_index = -1

        bone_count = 0  # The number of bones influencing this vertex
        bones_read = 0  # The number of bone weights we've read for this vert

        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            for i, split in enumerate(line_split):
                if split[-1:] == ',':
                    line_split[i] = split.rstrip(",")

            if state == 0 and line_split[0] == vert_tok:
                vert_index = int(line_split[1])
                if vert_index >= vert_count:
                    fmt = ("vert_count does not index vert_index -- "
                           "%d not in [0, %d)")
                    raise ValueError(fmt % (vert_index, vert_count))
                state = 1
            elif state == 1 and line_split[0] == "OFFSET":
                self.offset = tuple([float(v)
                                     for v in line_split[1:4]])  # TODO
                state = 2
            elif state == 2 and line_split[0] == "BONES":
                bone_count = int(line_split[1])
                self.weights = [None] * bone_count
                state = 3
            elif state == 3 and line_split[0] == "BONE":
                bone = int(line_split[1])
                influence = float(line_split[2])
                self.weights[bones_read] = ((bone, influence))
                bones_read += 1
                if bones_read == bone_count:
                    state = -1
                    return lines_read

        return lines_read

    def save(self, file, index, vert_tok_suffix=""):
        file.write("VERT%s %d\n" % (vert_tok_suffix, index))
        file.write("OFFSET %f %f %f\n" % self.offset)
        file.write("BONES %d\n" % len(self.weights))
        for weight in self.weights:
            file.write("BONE %d %f\n" % weight)
        file.write("\n")


class FaceVertex(object):
    __slots__ = ("vertex", "normal", "color", "uv")

    def __init__(self, vertex=None, normal=None, color=None, uv=None):
        self.vertex = vertex
        self.normal = normal
        self.color = color
        self.uv = uv

    def save(self, file, version, index_offset, vert_tok_suffix=""):
        vert_id = self.vertex + index_offset
        normal = __clamp_normal__(self.normal)
        if version == 5:
            file.write("VERT %d %f %f %f %f %f\n" %
                       ((vert_id,) + normal + self.uv))
        else:
            file.write("VERT%s %d\n" % (vert_tok_suffix, vert_id))
            file.write("NORMAL %f %f %f\n" % normal)
            file.write("COLOR %f %f %f %f\n" % self.color)
            file.write("UV 1 %f %f\n\n" % self.uv)


class Face(object):
    __slots__ = ('mesh_id', 'material_id', 'indices')

    def __init__(self, mesh_id, material_id):
        self.mesh_id = mesh_id
        self.material_id = material_id
        self.indices = [None] * 3

    def __load_face__(self, file, version, face_count, vert_tok='VERT'):
        lines_read = 0
        state = 0

        tri_number = -1
        vert_number = -1

        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            for i, split in enumerate(line_split):
                if split[-1:] == ',':
                    line_split[i] = split.rstrip(",")

            # Support both TRI & TRI16
            if state == 0 and line_split[0].startswith("TRI"):
                tri_number += 1
                self.mesh_id = int(line_split[1])
                self.material_id = int(line_split[2])
                state = 1
            elif state == 1 and line_split[0] == vert_tok:
                vert = FaceVertex()
                vert.vertex = int(line_split[1])
                vert_number += 1

                if version == 5:
                    vert.normal = tuple([float(v)
                                         for v in line_split[2:5]])  # TODO
                    vert.uv = (float(line_split[5]), float(line_split[6]))
                    self.indices[vert_number] = vert
                    if vert_number == 2:
                        return lines_read
                    else:
                        continue

                # for Version 6, continue loading the vertex properties for the
                # last vertex
                else:
                    state = 2

            elif state == 2 and line_split[0] == "NORMAL":
                vert.normal = (float(line_split[1]),
                               float(line_split[2]),
                               float(line_split[3]))
                state = 3
            elif state == 3 and line_split[0] == "COLOR":
                vert.color = (float(line_split[1]),
                              float(line_split[2]),
                              float(line_split[3]),
                              float(line_split[4]))
                state = 4
            elif state == 4 and line_split[0] == "UV":
                vert.uv = (float(line_split[2]), float(line_split[3]))
                self.indices[vert_number] = vert
                if vert_number == 2:
                    return lines_read
                else:
                    state = 1

        return lines_read

    def save(self, file, version, index_offset, vert_tok_suffix=""):
        # Only use TRI16 if we're using version 7 or newer, etc.
        if version >= 7 and (self.mesh_id > 255 or self.material_id > 255):
            token = "TRI16"
        else:
            token = "TRI"
        file.write("%s %d %d %d %d\n" %
                   (token, self.mesh_id, self.material_id, 0, 0))
        for i in range(3):
            self.indices[i].save(file, version, index_offset,
                                 vert_tok_suffix=vert_tok_suffix)
        file.write("\n")

    def isValid(self):
        '''
        Checks to make sure that the face consists of 3 vertices,
        all of which refer to different vertex indices
        '''
        if(len(self.indices) != 3):
            return False

        indices = [index.vertex for index in self.indices]

        if indices[0] == indices[1]:
            return False

        if indices[0] == indices[2]:
            return False

        if indices[1] == indices[2]:
            return False

        return True


class Material(object):
    __slots__ = (
        'name', 'type', 'images', 'color',
        'color_ambient', 'color_specular', 'color_reflective',
        'transparency', 'incandescence',
        'coeffs', 'glow',
        'refractive', 'reflective',
        'blinn', 'phong'
    )

    def __init__(self, name, material_type, images):
        self.name = name
        self.type = material_type
        self.images = images
        self.color = (0.0, 0.0, 0.0, 1.0)
        self.color_ambient = (0.0, 0.0, 0.0, 1.0)
        self.color_specular = (-1.0, -1.0, -1.0, 1.0)
        self.color_reflective = (-1.0, -1.0, -1.0, 1.0)
        self.transparency = (0.0, 0.0, 0.0, 1.0)
        self.incandescence = (0.0, 0.0, 0.0, 1.0)
        self.coeffs = (0.8, 0.0)
        self.glow = (0.0, 0)
        self.refractive = (6, 1.0)
        self.reflective = (-1, 1.0)
        self.blinn = (-1.0, -1.0)
        self.phong = -1.0

    def save(self, file, version, material_index, extended_features=True):
        imgs = serialize_image_string(
            self.images, extended_features=extended_features)
        if version == 5:
            file.write('MATERIAL %d "%s"\n' % (material_index, imgs))
        else:
            file.write('MATERIAL %d "%s" "%s" "%s"\n' %
                       (material_index, self.name, self.type, imgs))
            file.write("COLOR %f %f %f %f\n" % self.color)
            file.write("TRANSPARENCY %f %f %f %f\n" % self.transparency)
            file.write("AMBIENTCOLOR %f %f %f %f\n" % self.color_ambient)
            file.write("INCANDESCENCE %f %f %f %f\n" % self.incandescence)
            file.write("COEFFS %f %f\n" % self.coeffs)
            file.write("GLOW %f %d\n" % self.glow)
            file.write("REFRACTIVE %d %f\n" % self.refractive)
            file.write("SPECULARCOLOR %f %f %f %f\n" % self.color_specular)
            file.write("REFLECTIVECOLOR %f %f %f %f\n" % self.color_reflective)
            file.write("REFLECTIVE %d %f\n" % self.reflective)
            file.write("BLINN %f %f\n" % self.blinn)
            file.write("PHONG %f\n\n" % self.phong)


class Mesh(object):
    __slots__ = ('name', 'verts', 'faces', 'bone_groups',
                 'material_groups', '__vert_tok')

    def __init__(self, name):
        self.name = name

        self.verts = []
        self.faces = []

        self.bone_groups = []
        self.material_groups = []

        # Used for handling VERT vs VERT32 without using a ton of if statements
        self.__vert_tok = 'VERT'

    def __load_verts__(self, file, model):
        lines_read = 0
        vert_count = 0

        bones = model.bones
        # version = model.version
        self.bone_groups = [[] for i in repeat(None, len(bones))]

        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            if line_split[0] == 'NUMVERTS':
                self.__vert_tok = 'VERT'
            elif line_split[0] == 'NUMVERTS32':
                self.__vert_tok = 'VERT32'
            else:
                continue

            vert_count = int(line_split[1])
            self.verts = [Vertex() for i in range(vert_count)]
            break

        vert_tok = self.__vert_tok
        for vertex in self.verts:
            lines_read += vertex.__load_vert__(file,
                                               vert_count, self, vert_tok)

        return lines_read

    def __load_faces__(self, file, version):
        lines_read = 0
        face_count = 0

        self.material_groups = []

        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            for i, split in enumerate(line_split):
                if split[-1:] == ',':
                    line_split[i] = split.rstrip(",")

            if line_split[0] == "NUMFACES":
                face_count = int(line_split[1])
                self.faces = [Face(None, None) for i in range(face_count)]
                break

        vert_tok = self.__vert_tok
        for face in self.faces:
            lines_read += face.__load_face__(file, version,
                                             face_count, vert_tok=vert_tok)

        return lines_read


class Model(XBinIO, object):
    __slots__ = ('name', 'bones', 'meshes', 'materials')
    supported_versions = [5, 6, 7]

    def __init__(self, name='$model'):
        super(XBinIO, self).__init__()
        self.name = name

        self.bones = []
        self.meshes = []
        self.materials = []

    def __load_header__(self, file):
        lines_read = 0
        state = 0
        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            if state == 0 and line_split[0] == "MODEL":
                state = 1
            elif state == 1 and line_split[0] == "VERSION":
                self.version = int(line_split[1])
                if self.version not in Model.supported_versions:
                    fmt = "Invalid model version: %d - must be one of %s"
                    vargs = (self.version, repr(Model.supported_versions))
                    raise ValueError(fmt % vargs)
                return lines_read

        return lines_read

    def __load_bone__(self, file, bone_count):
        lines_read = 0

        # keeps track of the importer state for a given bone
        state = 0

        bone_index = -1
        bone = None

        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            for i, split in enumerate(line_split):
                if split[-1:] == ',':
                    line_split[i] = split.rstrip(",")

            if state == 0 and line_split[0] == "BONE":
                bone_index = int(line_split[1])
                if bone_index >= bone_count:
                    fmt = ("bone_count does not index bone_index -- "
                           "%d not in [0, %d)")
                    raise ValueError(fmt % (bone_index, bone_count))
                state = 1
            elif state == 1 and line_split[0] == "OFFSET":
                bone = self.bones[bone_index]
                bone.offset = (float(line_split[1]),
                               float(line_split[2]),
                               float(line_split[3]))
                state = 2
            # SCALE ... is ignored as its always 1
            elif state == 2 and line_split[0] == "X":
                x = (float(line_split[1]),
                     float(line_split[2]),
                     float(line_split[3]))
                bone.matrix[0] = x
                state = 3
            elif state == 3 and line_split[0] == "Y":
                y = (float(line_split[1]),
                     float(line_split[2]),
                     float(line_split[3]))
                bone.matrix[1] = y
                state = 4
            elif state == 4 and line_split[0] == "Z":
                z = (float(line_split[1]),
                     float(line_split[2]),
                     float(line_split[3]))
                bone.matrix[2] = z
                state = -1
                return lines_read

        return lines_read

    def __load_bones__(self, file):
        lines_read = 0
        bone_count = 0
        bones_read = 0
        cosmetic_count = 0
        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            # TODO: Reordering these token checks may improve performance
            if line_split[0] == "NUMCOSMETICS":
                cosmetic_count = int(line_split[1])
            elif line_split[0] == "NUMBONES":
                bone_count = int(line_split[1])
                self.bones = [Bone(None)] * bone_count
            elif line_split[0] == "BONE":
                index = int(line_split[1])
                parent = int(line_split[2])
                cosmetic = (index >= (bone_count - cosmetic_count))
                self.bones[index] = Bone(line_split[3].strip('"'),
                                         parent, cosmetic)
                bones_read += 1
                if bones_read == bone_count:
                    break

        for _ in range(bone_count):
            lines_read += self.__load_bone__(file, bone_count)

        return lines_read

    def __load_meshes__(self, file):
        lines_read = 0
        mesh_count = 0
        meshes_read = 0
        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            if line_split[0] == "NUMOBJECTS":
                mesh_count = int(line_split[1])
                self.meshes = [None] * mesh_count
            elif line_split[0] == "OBJECT":
                index = int(line_split[1])
                self.meshes[index] = Mesh(line_split[2].strip('"'))
                meshes_read += 1
                if meshes_read == mesh_count:
                    return lines_read

        return lines_read

    # Generate actual submesh data from the default mesh
    def __generate_meshes__(self, default_mesh):
        bone_count = len(self.bones)
        mtl_count = len(self.materials)
        for mesh in self.meshes:
            mesh.bone_groups = [[] for i in range(bone_count)]
            mesh.material_groups = [[] for i in range(mtl_count)]

        # An array of vertex mappings for each mesh
        # used in the format vertex_map[mesh][original_vertex]
        # yields either None (unset) or the new vertex id
        vertex_map = [[None] * len(default_mesh.verts)
                      for i in range(len(self.meshes))]

        for face in default_mesh.faces:
            mesh_id = face.mesh_id
            mtl_id = face.material_id
            mesh = self.meshes[mesh_id]
            for ind in face.indices:
                vert_id = vertex_map[mesh_id][ind.vertex]
                if vert_id is None:
                    vert_id = len(mesh.verts)
                    vertex_map[mesh_id][ind.vertex] = vert_id
                    vert = default_mesh.verts[ind.vertex]
                    mesh.verts.append(vert)
                    for bone_id, weight in vert.weights:
                        mesh.bone_groups[bone_id].append((vert_id, weight))
                ind.vertex = vert_id
                mesh.material_groups[mtl_id].append(vert_id)
            mesh.faces.append(face)

        # Remove duplicates
        for mesh in self.meshes:
            for group_index, group in enumerate(mesh.bone_groups):
                mesh.bone_groups[group_index] = list(set(group))
            for group_index, group in enumerate(mesh.material_groups):
                mesh.material_groups[group_index] = list(set(group))

    def __load_materials__(self, file, version):
        lines_read = 0

        material_count = None
        material = None

        for line in file:
            lines_read += 1

            line_split = line.split()
            if not line_split:
                continue

            for i, split in enumerate(line_split):
                if split[-1:] == ',':
                    line_split[i] = split.rstrip(",")

            if material_count is None and line_split[0] == "NUMMATERIALS":
                material_count = int(line_split[1])
                self.materials = [None] * material_count
            elif line_split[0] == "MATERIAL":
                index = int(line_split[1])
                if version == 5:
                    # Legacy XModel materials don't explicitly have a name
                    #  field, so we simply auto-generate a name
                    name = "Material_%d" % index
                    material_type = "Lambert"
                    images = deserialize_image_string(line_split[2].strip('"'))
                else:
                    name = line_split[2].strip('"')
                    material_type = line_split[3].strip('"')
                    images = deserialize_image_string(line_split[4].strip('"'))
                material = Material(name, material_type, images)
                self.materials[index] = Material(name, material_type, images)
                material = self.materials[index]

                if version == 5:
                    continue

            # All of the properties below are only present in version 6
            elif line_split[0] == "COLOR":
                material.color = (float(line_split[1]),
                                  float(line_split[2]),
                                  float(line_split[3]),
                                  float(line_split[4]))
            elif line_split[0] == "TRANSPARENCY":
                material.transparency = (float(line_split[1]),
                                         float(line_split[2]),
                                         float(line_split[3]),
                                         float(line_split[4]))
            elif line_split[0] == "AMBIENTCOLOR":
                material.color_ambient = (float(line_split[1]),
                                          float(line_split[2]),
                                          float(line_split[3]),
                                          float(line_split[4]))
            elif line_split[0] == "INCANDESCENCE":
                material.incandescence = (float(line_split[1]),
                                          float(line_split[2]),
                                          float(line_split[3]),
                                          float(line_split[4]))
            elif line_split[0] == "COEFFS":
                material.coeffs = (float(line_split[1]), float(line_split[2]))
            elif line_split[0] == "GLOW":
                material.glow = (float(line_split[1]), int(line_split[2]))
            elif line_split[0] == "REFRACTIVE":
                material.refractive = (int(line_split[1]),
                                       float(line_split[2]))
            elif line_split[0] == "SPECULARCOLOR":
                material.color_specular = (float(line_split[1]),
                                           float(line_split[2]),
                                           float(line_split[3]),
                                           float(line_split[4]))
            elif line_split[0] == "REFLECTIVECOLOR":
                material.color_reflective = (float(line_split[1]),
                                             float(line_split[2]),
                                             float(line_split[3]),
                                             float(line_split[4]))
            elif line_split[0] == "REFLECTIVE":
                material.reflective = (
                    int(line_split[1]), float(line_split[2]))
            elif line_split[0] == "BLINN":
                material.blinn = (float(line_split[1]), float(line_split[2]))
            elif line_split[0] == "PHONG":
                material.phong = float(line_split[1])

        return lines_read

    def normalize_weights(self):
        """
        Normalize the bone weights for all verts (in all meshes)
        """
        for mesh in self.meshes:
            for vert in mesh.verts:
                vert.weights = __normalized__(vert.weights)

    def LoadFile_Raw(self, path, split_meshes=True):
        file = open(path, "r")
        # file automatically keeps track of what line its on across calls
        self.__load_header__(file)
        self.__load_bones__(file)

        # A global mesh containing all of the vertex and face data for the
        # entire model
        default_mesh = Mesh("$default")

        default_mesh.__load_verts__(file, self)
        default_mesh.__load_faces__(file, self.version)

        if split_meshes:
            self.__load_meshes__(file)
        self.__load_materials__(file, self.version)

        if split_meshes:
            self.__generate_meshes__(default_mesh)
        else:
            self.meshes = [default_mesh]
        file.close()

    # Write an xmodel_export file, by default it uses the objects self.version
    def WriteFile_Raw(self, path, version=None,
                      header_message="",
                      extended_features=True,
                      strict=False):
        # If there is no current version, fallback to the argument
        version = validate_version(self, version)

        if version not in Model.supported_versions:
            self.version = None
            vargs = (version, repr(Model.supported_versions))
            raise ValueError(
                "Invalid model version: %d - must be one of %s" % vargs)

        # Used to offset the vertex indices for each mesh
        vert_offsets = [0]
        for mesh in self.meshes:
            prev_index = len(vert_offsets) - 1
            vert_offsets.append(vert_offsets[prev_index] + len(mesh.verts))

        vert_count = vert_offsets[len(vert_offsets) - 1]

        if strict:
            # TODO: Add cosmetic hierarchy validation
            assert len(self.materials) < 256
            assert len(self.meshes) < 256
            if version < 7:
                assert vert_count <= 0xFFFF

        file = open(path, "w")
        file.write("// Export time: %s\n\n" % strftime("%a %b %d %H:%M:%S %Y"))

        if header_message != '':
            file.write(header_message)

        file.write("MODEL\n")
        file.write("VERSION %d\n\n" % version)

        # Bone Hierarchy
        file.write("NUMBONES %d\n" % len(self.bones))

        # NOTE: Cosmetic bones are only used by version 7 and later
        if version == 7:
            cosmetics = len([bone for bone in self.bones if bone.cosmetic])
            if cosmetics > 0:
                file.write("NUMCOSMETICS %d\n" % cosmetics)

                # Cosmetic bones MUST be written AFTER the standard bones in
                #  the bone info list, so we need to generate a sorted list
                #  of index/bone pairs
                bone_enum = sorted(enumerate(self.bones),
                                   key=lambda kvp: kvp[1].cosmetic)

                # Allocate space for the bone map before any
                #  modifications to self.bones
                bone_map = [None] * len(self.bones)

                # Update the bone list & build old->new index map
                index_map, self.bones = zip(*bone_enum)
                for new, old in enumerate(index_map):
                    bone_map[old] = new

                # Rebuild the parent indices for all non-root bones
                for bone in self.bones:
                    if bone.parent != -1:
                        bone.parent = bone_map[bone.parent]

                # Rebuild the weight tables for all vertices
                for mesh in self.meshes:
                    for vert in mesh.verts:
                        vert.weights = [(bone_map[old_index], weight)
                                        for old_index, weight in vert.weights]

        # Write the actual bone info
        for bone_index, bone in enumerate(self.bones):
            file.write("BONE %d %d \"%s\"\n" %
                       (bone_index, bone.parent, bone.name))

        file.write("\n")

        # Bone Transform Data
        for bone_index, bone in enumerate(self.bones):
            file.write("BONE %d\n" % bone_index)
            file.write("OFFSET %f %f %f\n" %
                       (bone.offset[0], bone.offset[1], bone.offset[2]))
            file.write("SCALE %f %f %f\n" % (1.0, 1.0, 1.0))
            file.write("X %f %f %f\n" % __clamp_multi__(bone.matrix[0]))
            file.write("Y %f %f %f\n" % __clamp_multi__(bone.matrix[1]))
            file.write("Z %f %f %f\n\n" % __clamp_multi__(bone.matrix[2]))
        file.write("\n")

        # Vertices
        vert_tok_suffix = "32" if version == 7 and vert_count > 0xFFFF else ""
        file.write("NUMVERTS%s %d\n" % (vert_tok_suffix, vert_count))
        for mesh_index, mesh in enumerate(self.meshes):
            vert_offset = vert_offsets[mesh_index]
            for vert_index, vert in enumerate(mesh.verts):
                vert.save(file, vert_index + vert_offset, vert_tok_suffix)

        # Faces
        face_count = sum([len(mesh.faces) for mesh in self.meshes])
        file.write("NUMFACES %d\n" % face_count)
        for mesh_index, mesh in enumerate(self.meshes):
            vert_offset = vert_offsets[mesh_index]
            for face in mesh.faces:
                face.save(file, version, vert_offset, vert_tok_suffix)

        # Meshes
        file.write("NUMOBJECTS %d\n" % len(self.meshes))
        for mesh_index, mesh in enumerate(self.meshes):
            file.write("OBJECT %d \"%s\"\n" % (mesh_index, mesh.name))
        file.write("\n")

        # Materials
        file.write("NUMMATERIALS %d\n" % len(self.materials))
        for material_index, material in enumerate(self.materials):
            material.save(file, version, material_index,
                          extended_features=extended_features)

        file.close()

    @staticmethod
    def FromFile_Raw(filepath, split_meshes=True):
        '''
        Load from an XMODEL_EXPORT file and return the resulting Model()
        '''
        model = Model()
        model.LoadFile_Raw(filepath, split_meshes)
        return model

    def LoadFile_Bin(self, path, split_meshes=True,
                     is_compressed=True, dump=False):
        file = open(path, "rb")

        if is_compressed:
            file = XBinIO.__decompress_internal__(file, dump)

        default_mesh = self.__xbin_loadfile_internal__(file, 'MODEL')

        if split_meshes:
            self.__generate_meshes__(default_mesh)
        else:
            self.meshes = [default_mesh]
        file.close()

    def WriteFile_Bin(self, path, version=None,
                      extended_features=True, header_message=""):
        # If there is no current version, fallback to the argument
        version = validate_version(self, version)
        return self.__xbin_writefile_model_internal__(path,
                                                      version,
                                                      extended_features,
                                                      header_message)

    @staticmethod
    def FromFile_Bin(filepath, split_meshes=True,
                     is_compressed=True, dump=False):
        '''
        Load from an XMODEL_BIN file and return the resulting Model()
        '''
        model = Model()
        model.LoadFile_Bin(filepath, split_meshes, is_compressed, dump)
        return model
