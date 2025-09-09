bl_info = {
    "name": "Key Bundle",
    "author": "lachrymal.net",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "Graph Editor → Sidebar → Key Bundle",
    "description": "Key any chunks of keyframes with the same interpolation",
    "category": "Animation",
}

from itertools import groupby
import bpy
from bl_math import lerp

DATA_KEY = 'LKRM_KeyBundleCurveData'
def ExtNodeTree():
    if DATA_KEY not in bpy.data.node_groups:
        bpy.data.node_groups.new(DATA_KEY, 'ShaderNodeTree')
        bpy.data.node_groups[DATA_KEY].use_fake_user = True
    return bpy.data.node_groups[DATA_KEY].nodes

curve_node_mapping = {}
def ExtCurveData(curve_name):
    if curve_name not in curve_node_mapping:
        cn = ExtNodeTree().new('ShaderNodeRGBCurve')
        curve_node_mapping[curve_name] = cn.name
    return ExtNodeTree()[curve_node_mapping[curve_name]]
KEY = 'LKRM_KeyBundle'
ExtCurveData(KEY)

def in_range(x, r):
    return r[0] <= x <= r[1]

def get_selected_chunk_ranges_from_fc(fc):
    fc.keyframe_points.sort()
    chunks = groupby(fc.keyframe_points, lambda k: k.select_control_point)
    chunks = [[*keys] for sel, keys in chunks if sel]
    chunks = [(keys[0].co.copy(), keys[-1].co.copy()) for keys in chunks if len(keys) > 1]
    return chunks

def get_fc_with_chunks(context):
    cks = [(fc, get_selected_chunk_ranges_from_fc(fc)) for fc in context.selected_editable_fcurves]
    cks = [(fc, chunks) for fc, chunks in cks if len(chunks) > 0]
    return cks

class GRAPH_OT_lkrm_keybundle(bpy.types.Operator):
    bl_idname = "graph.lkrm_keybundle"
    bl_label = "Key Bundle"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return len(get_fc_with_chunks(bpy.context)) > 0 and context.area.type == 'GRAPH_EDITOR'

    def execute(self, context):
        mapping = ExtCurveData(KEY).mapping
        curve = mapping.curves[3]
        pts = [('AUTO_CLAMPED' if pt.handle_type == 'AUTO' else pt.handle_type, pt.location.copy()) for pt in curve.points.values()]
        pts.sort(key=lambda p: p[1].x)
        for fc, chunks in get_fc_with_chunks(bpy.context):
            for kf in reversed(fc.keyframe_points.values()):
                if any(r[0].x <= kf.co.x <= r[1].x for r in chunks):
                    fc.keyframe_points.remove(kf)

            for bbox in chunks:
                print(pts)
                if pts[0][1].x != 0.0:
                    nk = fc.keyframe_points.insert(
                        bbox[0].x,
                        lerp(bbox[0].y, bbox[1].y, mapping.evaluate(curve, 0.0))
                    )
                    nk.handle_right_type = "VECTOR"
                    
                if pts[-1][1].x != 1.0:
                    nk = fc.keyframe_points.insert(
                        bbox[1].x,
                        lerp(bbox[0].y, bbox[1].y, mapping.evaluate(curve, 1.0))
                    )
                    nk.handle_right_type = "VECTOR"

                for tp, pt in pts:
                    nk = fc.keyframe_points.insert(
                        lerp(bbox[0].x, bbox[1].x, pt.x),
                        lerp(bbox[0].y, bbox[1].y, pt.y)
                    )
                    nk.handle_left_type = "VECTOR" if pt.x in [0.0, 1.0] else tp
                    nk.handle_right_type = "VECTOR" if pt.x in [0.0, 1.0] else tp
                    nk.handle_left.x = nk.co.x
                    nk.handle_right.x = nk.co.x
                    nk.handle_left.y = nk.co.y
                    nk.handle_right.y = nk.co.y
                
        return { 'FINISHED' }

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        self.layout.template_curve_mapping(ExtCurveData(KEY), "mapping")

def menu_func(self, context):
    self.layout.operator(GRAPH_OT_lkrm_keybundle.bl_idname)

def register():
    bpy.utils.register_class(GRAPH_OT_lkrm_keybundle)
    bpy.types.GRAPH_MT_editor_menus.append(menu_func)

def unregister():
    bpy.types.GRAPH_MT_editor_menus.remove(menu_func)
    bpy.utils.unregister_class(GRAPH_OT_lkrm_keybundle)

if __name__ == "__main__":
    register()
