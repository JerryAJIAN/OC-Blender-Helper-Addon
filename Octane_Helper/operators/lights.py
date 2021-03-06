import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, IntProperty
from .. assets import load_objects

def enable_nodes(obj):
    if(obj.type == 'LIGHT'):
        obj.data.use_nodes = True
    elif(obj.type == 'MESH'):
        for slot in obj.material_slots:
            slot.material.use_nodes = True

def get_enum_emissive_material(self, context):
    lights = context.scene.oc_lights
    index = context.scene.oc_lights_index
    # Return None if no object taged as light
    if(len(lights)==0): return [('None', 'None', '')]
    obj = lights[index].obj
    result = []

    if(obj.type == 'LIGHT'):
        # Search node in the active light object for emissive node
        for node in obj.data.node_tree.nodes:
            if(node.bl_idname=='ShaderNodeOctBlackBodyEmission' or node.bl_idname=='ShaderNodeOctTextureEmission' or node.bl_idname=='ShaderNodeOctToonDirectionLight' or node.bl_idname=='ShaderNodeOctToonPointLight'):
                result.append(('Light', 'Light', ''))
    elif(obj.type == 'MESH'):
        # Return None if no material found in the active light object
        if(len(obj.material_slots)==0): return [('None', 'None', '')]
        # Search materials in the active light object for emissive material
        for slot in obj.material_slots:
            for node in slot.material.node_tree.nodes:
                if(node.bl_idname=='ShaderNodeOctBlackBodyEmission' or node.bl_idname=='ShaderNodeOctTextureEmission' or node.bl_idname=='ShaderNodeOctToonDirectionLight' or node.bl_idname=='ShaderNodeOctToonPointLight'):
                    result.append((slot.material.name, slot.material.name, ''))
    
    # Return result if the emissive material exists otherwise return None
    if(len(result)!=0): return result
    else: return [('None', 'None', '')]

def refresh_lights_list(context, active_last=False, active_current=False):
    context.scene.oc_lights.clear()
    if(not active_current): 
        context.scene.oc_lights_index = 0
    for obj in context.scene.objects:
        if 'oc_light' in obj:
            if(obj['oc_light']!='None' and obj['oc_light']!='' and obj['oc_light']!=None):
                light = context.scene.oc_lights.add()
                light.obj = obj
                light.tag = obj['oc_light']
                if(light.tag == 'Mesh'):
                    light.icon = 'LIGHTPROBE_CUBEMAP'
                elif(light.tag == 'Sphere'):
                    light.icon = 'LIGHT_POINT'
                elif(light.tag == 'Area'):
                    light.icon = 'LIGHT_AREA'
                elif(light.tag == 'Spot'):
                    light.icon = 'MESH_CYLINDER'
                elif(light.tag == 'Point Toon'):
                    light.icon = 'LIGHTPROBE_PLANAR'
                elif(light.tag == 'Directional Toon'):
                    light.icon = 'LIGHT_SPOT'
                else:
                    light.icon = 'QUESTION'
                enable_nodes(obj)
    if(active_last):
        context.scene.oc_lights_index = len(context.scene.oc_lights) - 1

# Classes
class OctaneLightsManager(Operator):
    bl_label = 'Lights Manager'
    bl_idname = 'octane.lights_manager'
    bl_description = 'A panel that manages all emissive objects which have been marked as light sources'
    bl_options = {'REGISTER'}

    emissive_material: EnumProperty(
        name='Emissive Material',
        items=get_enum_emissive_material
    )

    def draw(self, context):
        lights = context.scene.oc_lights
        index = context.scene.oc_lights_index
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('octane.add_light_sphere', text='Sphere', icon='LIGHT_POINT')
        row.operator('octane.add_light_area', text='Area', icon='LIGHT_AREA')
        row.operator('octane.add_light_spot', text='Spot', icon='LIGHT_SPOT')
        row = col.row(align=True)
        row.operator('octane.add_light_toon_point', text='Point (Toon)', icon='LIGHTPROBE_PLANAR')
        row.operator('octane.add_light_toon_spot', text='Directional (Toon)', icon='LIGHT_SPOT')

        layout.template_list('OCTANE_UL_light_list', '', context.scene, 'oc_lights', context.scene, 'oc_lights_index')
        split = layout.split(factor = 0.2)
        split.operator('octane.select_lights', text='Select').index = index
        split.prop(self, 'emissive_material', text='')
        if(self.emissive_material!='None' and self.emissive_material!='' and self.emissive_material!=None):
            obj = lights[index].obj
            if(obj.type=='LIGHT'):
                ntree = obj.data.node_tree
                if(obj.data.type == 'SPHERE'):
                    layout.prop(obj.data, 'sphere_radius', text='Radius')
                elif(obj.data.type == 'AREA'):
                    layout.prop(obj.data, 'shape', text='Shape')
                    if obj.data.shape in {'SQUARE', 'DISK'}:
                        layout.prop(obj.data, 'size', text='Size')
                    elif obj.data.shape in {'RECTANGLE', 'ELLIPSE'}:
                        layout.prop(obj.data, 'size', text='Size X')
                        layout.prop(obj.data, 'size_y', text='Size Y')
            else:
                ntree = bpy.data.materials[self.emissive_material].node_tree

            outNode = ntree.get_output_node('octane')
            if(outNode.inputs['Surface'].is_linked):
                if(outNode.inputs['Surface'].links[0].from_node.bl_idname=='ShaderNodeOctDiffuseMat'):
                    rootNode = outNode.inputs['Surface'].links[0].from_node
                    layout.template_node_view(ntree, rootNode, rootNode.inputs['Emission'])
                else:
                    rootNode = outNode
                    layout.template_node_view(ntree, rootNode, rootNode.inputs['Surface'])

    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        refresh_lights_list(context)
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class OctaneSetLight(Operator):
    bl_label = 'Mark as a Light Source'
    bl_idname = 'octane.set_light'
    bl_description = 'To mark selected objects as light sources with a tag, so they can be managed by the Lights Manager'
    bl_options = {'REGISTER', 'UNDO'}

    types = [
        ('None', 'None', ''),
        ('Mesh', 'Mesh', ''),
        ('Sphere', 'Sphere', ''),
        ('Area', 'Area', ''),
        ('Spot', 'Spot', ''),
        ('Point Toon', 'Point Toon', ''),
        ('Directional Toon', 'Directional Toon', '')
    ]
    light_type: EnumProperty(items=types, name='Type', default='None')

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'light_type', text='')
    
    def execute(self, context):
        for obj in context.selected_objects:
            if(self.light_type != 'None'):
                obj['oc_light'] = self.light_type
            else:
                if('oc_light' in obj):
                    del obj['oc_light']
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if 'oc_light' in context.active_object:
            if(context.active_object['oc_light'] in [item[0] for item in self.types]):
                self.light_type = context.active_object['oc_light']
            else:
                self.light_type = 'None'

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class OctaneAddLightSphere(Operator):
    bl_label = 'Add a sphere light'
    bl_idname = 'octane.add_light_sphere'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.light_add(type='SPHERE')
        context.active_object['oc_light'] = 'Sphere'
        refresh_lights_list(context, True)
        return {'FINISHED'}

class OctaneAddLightArea(Operator):
    bl_label = 'Add a area light'
    bl_idname = 'octane.add_light_area'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.light_add(type='AREA')
        context.active_object['oc_light'] = 'Area'
        refresh_lights_list(context, True)
        return {'FINISHED'}

class OctaneAddLightSpot(Operator):
    bl_label = 'Add a spot light (fake)'
    bl_idname = 'octane.add_light_spot'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = load_objects('Spot', 'lights')
        for obj in objs:
            obj['oc_light'] = 'Spot'
        refresh_lights_list(context, True)
        return {'FINISHED'}

class OctaneAddLightToonPoint(Operator):
    bl_label = 'Add a point toon light'
    bl_idname = 'octane.add_light_toon_point'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.light_add(type='POINT')
        context.active_object['oc_light'] = 'Point Toon'
        context.active_object.name = 'Point_Toon' + context.active_object.name[5:]
        refresh_lights_list(context, True)
        return {'FINISHED'}

class OctaneAddLightToonSpot(Operator):
    bl_label = 'Add a directional toon light'
    bl_idname = 'octane.add_light_toon_spot'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.light_add(type='SUN')
        context.active_object['oc_light'] = 'Directional Toon'
        context.active_object.name = 'Directional_Toon' + context.active_object.name[3:]
        refresh_lights_list(context, True)
        return {'FINISHED'}

class OctaneSelectLights(Operator):
    bl_label = 'Select Lights'
    bl_idname = 'octane.select_lights'
    bl_description = 'Select lights [-1 : All lights; n : Light by index]'
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name='Index', default=-1, min=-1)
    
    def draw(self, context):
        layout = self.layout
        lights = context.scene.oc_lights
        if(self.index == -1):
            layout.label(text='All Lights')
        elif(self.index >=len(lights)):
            layout.label(text='Does not exist')
        else:
            layout.label(text='[{}/{}] {}'.format(self.index + 1, len(lights), lights[self.index].obj.name))
        layout.prop(self, 'index')

    def execute(self, context):
        refresh_lights_list(context, active_current=True)
        bpy.ops.object.select_all(action='DESELECT')
        lights = context.scene.oc_lights
        if(self.index == -1):
            for light in lights:
                light.obj.select_set(True)
                #context.view_layer.objects.active = light.obj
        elif(0 <= self.index < len(lights)):
            lights[self.index].obj.select_set(True)
            context.view_layer.objects.active = lights[self.index].obj
        return {'FINISHED'}
    
    def invoke(self, context, event):
        #self.index = -1
        return self.execute(context)