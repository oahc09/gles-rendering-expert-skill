"""Finite single-sample precision admission, logical budgets not measured bandwidth."""
FORMATS={'RGBA8':4,'RGBA16F':8,'RGBA32F':16}
def choose(width,height,layers,extensions,quality,target_contract,budget):
    for name,value in (('width',width),('height',height),('layers',layers)):
        if type(value)!=int or not 1<=value<=65536:raise ValueError('positive bounded integer '+name)
    if target_contract not in ('original_unorm','linear'):raise ValueError('explicit target contract required')
    if not isinstance(extensions,(list,tuple,set)) or any(not isinstance(e,str) for e in extensions):raise ValueError('extension list required')
    if not isinstance(quality,dict) or set(quality)!=set(FORMATS) or any(type(v)!=bool for v in quality.values()):raise ValueError('independent quality result per format required')
    if not isinstance(budget,dict) or set(budget)!={'max_allocation_bytes','max_logical_transfer_bytes','max_renderbuffer_size'}:raise ValueError('explicit memory/transfer/device dimension budgets required')
    for key,value in budget.items():
        if type(value)!=int or value<0:raise ValueError('nonnegative integer budget '+key)
    ext=set(extensions);rows=[]
    for fmt,bpp in FORMATS.items():
        pixel_count=width*height;isfloat=fmt!='RGBA8'
        allocation=pixel_count*(bpp+(4 if isfloat else 0))
        # Conservative full-frame per-layer destination read/write plus final
        # float target read/RGBA8 write. Excludes unknown physical traffic.
        transfer=2*pixel_count*bpp*layers+(pixel_count*(bpp+4) if isfloat else 0)
        reasons=[]
        if fmt=='RGBA16F' and not ext.intersection({'GL_EXT_color_buffer_float','GL_EXT_color_buffer_half_float'}):reasons.append('COLOR_RENDERABILITY_NOT_ADVERTISED')
        if fmt=='RGBA32F':
            if 'GL_EXT_color_buffer_float' not in ext:reasons.append('COLOR_RENDERABILITY_NOT_ADVERTISED')
            if 'GL_EXT_float_blend' not in ext:reasons.append('FLOAT32_BLEND_NOT_ADVERTISED')
        if max(width,height)>budget['max_renderbuffer_size']:reasons.append('RENDERBUFFER_DIMENSION_LIMIT')
        if allocation>budget['max_allocation_bytes']:reasons.append('LOGICAL_ALLOCATION_BUDGET')
        if transfer>budget['max_logical_transfer_bytes']:reasons.append('LOGICAL_TRANSFER_BUDGET')
        if not quality[fmt]:reasons.append('TARGET_QUALITY_REJECTED')
        rows.append({'format':fmt,'bytes_per_pixel':bpp,'logical_allocation_bytes':allocation,'logical_transfer_upper_bytes':transfer,'allocation_ratio_to_rgba8':allocation/(pixel_count*4),'quality_target':target_contract,'rejections':reasons,'eligible':not reasons})
    feasible=[r for r in rows if r['eligible']]
    selected=min(feasible,key=lambda r:(r['logical_allocation_bytes'],r['logical_transfer_upper_bytes']))['format'] if feasible else None
    return {'status':'ADMITTED_FOR_CORRECTNESS_NOT_PERFORMANCE' if selected else 'UNAVAILABLE',
            'selected':selected,'target_contract':target_contract,'candidates':rows,
            'physical_residency_bytes':None,'physical_bandwidth_bytes':None,'gpu_time_ms':None,
            'performance_acceptance':'NOT_MEASURED','quality_authenticity':'CALLER_MUST_BIND_TO_ACTUAL_TARGET_READBACK',
            'runtime_requirements':['FBO completeness','compile/link success','GL error checks','actual selected-format readback'],
            'scope':'Single-sample whole attachment, full-frame per-layer logical transfer bound; not tile/DRAM, alias lifetime, compression, physical residency or GPU speedup'}
