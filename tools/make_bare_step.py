"""Сделать vendor/crowpanel5_bare.step: STEP CrowPanel без акрилового корпуса (слои BREP_1-358/2-359/3 и винты BREP_4..7)."""
from build123d import *
a = import_step('vendor/crowpanel5_v3.stp')
doc = a.children[0]
skip = {'BREP_1-358','BREP_2-359','BREP_3','BREP_4','BREP_5','BREP_6','BREP_7'}
keep = [c for c in doc.children if c.label not in skip]
bare = Compound(children=keep); bare.label='crowpanel5_bare'
print(bare.bounding_box())
export_step(bare,'vendor/crowpanel5_bare.step')
