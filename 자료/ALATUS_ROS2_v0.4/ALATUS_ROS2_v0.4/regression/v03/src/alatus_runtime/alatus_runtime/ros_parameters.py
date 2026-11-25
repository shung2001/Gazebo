"""Humble-specific declarations; startup-only parameters have enforced read_only descriptors."""
from rcl_interfaces.msg import ParameterDescriptor, FloatingPointRange, IntegerRange, SetParametersResult
from .parameter_specs import SPECS
from .parameters import validate

def configure(node,key):
    specs=SPECS[key]
    for name,spec in specs.items():
        descriptor=ParameterDescriptor(description=spec['description'],read_only=not spec['mutable'])
        bounds=spec['bounds']
        if bounds and spec['type']=='float64':
            descriptor.floating_point_range=[FloatingPointRange(from_value=float(bounds[0]),to_value=float(bounds[1]),step=0.0)]
        elif bounds and spec['type']=='int64':
            descriptor.integer_range=[IntegerRange(from_value=bounds[0],to_value=bounds[1],step=1)]
        node.declare_parameter(name,spec['default'],descriptor)
    values=validate(key,{name:node.get_parameter(name).value for name in specs})
    def check(changes):
        candidate={name:node.get_parameter(name).value for name in specs}
        try:
            for parameter in changes:
                if parameter.name=='use_sim_time':
                    raise ValueError('use_sim_time: restart the complete pipeline to change clock')
                if parameter.name not in specs: raise ValueError('Unknown parameter '+parameter.name)
                if not specs[parameter.name]['mutable']: raise ValueError(parameter.name+': startup-only')
                candidate[parameter.name]=parameter.value
            validate(key,candidate)
            return SetParametersResult(successful=True)
        except ValueError as error:
            return SetParametersResult(successful=False,reason=str(error))
    node.add_on_set_parameters_callback(check)
    return values
