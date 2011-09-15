import bpy

file = open(r"C:\Dokumente und Einstellungen\DN\Eigene Dateien\out.txt", "w")
#file = open(r"C:\Users\SAM\Documents\blender-cod\test_obj.XMODEL_EXPORT", "w")

# Apply modifier settings - PREVIEW or RENDER:
modifier_quality = 'PREVIEW'

num_verts = 0
num_faces = 0
objects = []

o_count = 0
v_count = 0


# Count verts, faces, objects, etc.
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    
    m = o.to_mesh(scene=bpy.context.scene, apply_modifiers=True, settings=modifier_quality)
    matrix = o.matrix_world
    
    if len(m.vertices) < 3 or len(m.faces) < 1 or not m.uv_textures:
        continue
       
    num_verts += len(m.vertices)
    num_faces += len(m.faces)
    objects.append(o.name)
    

if (num_verts or num_faces or len(objects)) == 0:
    file.write("// No valid data to export!\n")
    #return

# Write header
file.write("MODEL\n")
file.write("VERSION 6\n")


# Write static rig
file.write("\nNUMBONES 1\n")
file.write("BONE 0 -1 \"tag_origin\"\n")

file.write("\nBONE 0\n")
file.write("OFFSET 0.000000 0.000000 0.000000\n")
file.write("SCALE 1.000000 1.000000 1.000000\n")
file.write("X 1.000000 0.000000 0.000000\n")
file.write("Y 0.000000 1.000000 0.000000\n")
file.write("Z 0.000000 0.000000 1.000000\n")


# Write vertex data
file.write("\nNUMVERTS %i\n" % num_verts)

# Retrieve verts which belong to a face only
verts = []
for f in m.faces:
    for v in f.vertices:
        verts.append(v)

# Uniquify & sort
keys = {}
for e in verts:
    keys[e] = 1
verts = list(keys.keys())

 
for vert in verts:
    v = m.vertices[vert]
    
    x=matrix[0][0]*v.co[0]+matrix[1][0]*v.co[1]+matrix[2][0]*v.co[2]+matrix[3][0]
    y=matrix[0][1]*v.co[0]+matrix[1][1]*v.co[1]+matrix[2][1]*v.co[2]+matrix[3][1]
    z=matrix[0][2]*v.co[0]+matrix[1][2]*v.co[1]+matrix[2][2]*v.co[2]+matrix[3][2]
    
    file.write("VERT %i\n" % v.index)
    file.write("OFFSET %.6f, %.6f, %.6f\n" % (x, y, z))
    file.write("BONES 1\n") # Static rig for now
    file.write("BONE 0 1.000000\n\n")

# Write face data
file.write("\nNUMFACES %i\n" % num_faces)

for o in bpy.data.objects:
    if o.type != 'MESH':
        continue

    m = o.to_mesh(scene=bpy.context.scene, apply_modifiers=True, settings=modifier_quality)
    
    # Models must have at least a single triangle and UV-mapping!
    if len(m.vertices) < 3 or len(m.faces) < 1 or not m.uv_textures:
        continue

    for f in m.faces:
        
        # TODO: Remap!
        mat = f.material_index
        
        if m.vertex_colors:
            col = m.vertex_colors.active.data[f.index]
        
        file.write("TRI %i %i 0 0\n" % (o_count, mat))
        
        # Reverse vert order per triangle and pray for proper face orientation
        for vi, v in sorted(enumerate(f.vertices), reverse=True):
            no = m.vertices[v].normal # Invert? orientation seems to have no effect...
            
            uv = m.uv_textures.active
            uv1 = uv.data[f.index].uv[vi][0]
            uv2 = 1 - uv.data[f.index].uv[vi][1] # Flip!
            
            file.write("VERT %i\n" % (v+v_count))
            file.write("NORMAL %.6f %.6f %.6f\n" % (no[0], no[1], no[2]))
            
            if m.vertex_colors:
                
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
    
    o_count += 1        
    v_count += len(m.vertices)


# Write object data
file.write("\nNUMOBJECTS %i\n" % len(objects))

for i_ob, ob in enumerate(objects):
    file.write("OBJECT %i \"%s\"\n" % (i_ob, ob))
    
    
# Write material data (static for now)
file.write("\nNUMMATERIALS 1\n")
file.write("MATERIAL 0 \"test_mat\" \"Lambert\" \"test_mat.tga\"\n")
file.write("COLOR 0.000000 0.000000 0.000000 1.000000\n")
file.write("TRANSPARENCY 0.000000 0.000000 0.000000 1.000000\n")
file.write("AMBIENTCOLOR 0.000000 0.000000 0.000000 1.000000\n")
file.write("INCANDESCENCE 0.000000 0.000000 0.000000 1.000000\n")
file.write("COEFFS 0.800000 0.000000\n")
file.write("GLOW 0.000000 0\n")
file.write("REFRACTIVE 6 1.000000\n")
file.write("SPECULARCOLOR -1.000000 -1.000000 -1.000000 1.000000\n")
file.write("REFLECTIVECOLOR -1.000000 -1.000000 -1.000000 1.000000\n")
file.write("REFLECTIVE -1 -1.000000\n")
file.write("BLINN -1.000000 -1.000000\n")
file.write("PHONG -1.000000\n")