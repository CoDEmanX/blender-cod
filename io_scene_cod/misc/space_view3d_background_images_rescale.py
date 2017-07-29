bl_info = {
    "name": "Background Image Rescale",
    "author": "CoDEmanX",
    "version": (1, 0),
    "blender": (2, 65, 0),
    "location": "View3D > Properties (N) > Background Images",
    "description": "Scale backgrounds to a pixel-per-unit factor for accurate reference images",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "3D View"}

import bpy

class VIEW3D_OT_background_image_rescale(bpy.types.Operator):
    """Scale background images of current view to a pixel-per-unit factor"""
    bl_idname = "view3d.background_image_rescale"
    bl_label = "Rescale"
    
    @classmethod
    def poll(cls, context):
        return (context.space_data.type == 'VIEW_3D' and
                context.space_data.background_images)

    def execute(self, context):
        factor = context.scene.background_image_scale_factor
        backgrounds = context.space_data.background_images
        
        for bg in backgrounds:
            bg_attr = 'image' if bg.source == 'IMAGE' else 'clip'
            bg_file = getattr(bg, bg_attr)
            
            if bg_file is not None:
                bg.size = bg_file.size[0] / factor / 2
                
        return {'FINISHED'}


def menu_func(self, context):
    layout = self.layout
    
    layout.label("Rescale all by factor:")
    
    row = layout.row(align=True)
    
    sub = row.column()
    sub.scale_x = 2
    sub.prop(context.scene, "background_image_scale_factor")
    
    row.operator("view3d.background_image_rescale")


def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.background_image_scale_factor = bpy.props.IntProperty(
        name="Pixels / unit",
        description="Pixel-per-unit factor for scaling, larger numbers for smaller images",
        default=100,
        min=1,
        max=10000,
        soft_max = 1000
    )
    bpy.types.VIEW3D_PT_background_image.append(menu_func)


def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.background_image_scale_factor
    bpy.types.VIEW3D_PT_background_image.remove(menu_func)

if __name__ == "__main__":
    register()
