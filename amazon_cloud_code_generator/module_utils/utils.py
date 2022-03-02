import re
import json
from typing import Iterable, List, Dict

from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
    snake_dict_to_camel_dict
)


def _jsonify(data: Dict) -> Dict:
    identifier = data.get('Identifier', None)
    properties = data.get('Properties', None)
    # Convert the Resource Properties from a str back to json
    data = {
        'identifier': identifier,
        'properties': json.loads(properties)
    }
    return data


def camel_to_snake(name: str, reversible: bool=False) -> str:

    def prepend_underscore_and_lower(m):
        return '_' + m.group(0).lower()

    if reversible:
        upper_pattern = r'[A-Z]'
    else:
        # Cope with pluralized abbreviations such as TargetGroupARNs
        # that would otherwise be rendered target_group_ar_ns
        upper_pattern = r'[A-Z]{3,}s$'

    s1 = re.sub(upper_pattern, prepend_underscore_and_lower, name)
    # Handle when there was nothing before the plural_pattern
    if s1.startswith("_") and not name.startswith("_"):
        s1 = s1[1:]
    if reversible:
        return s1

    # Remainder of solution seems to be https://stackoverflow.com/a/1176023
    first_cap_pattern = r'(.)([A-Z][a-z]+)'
    all_cap_pattern = r'([a-z0-9])([A-Z]+)'
    s2 = re.sub(first_cap_pattern, r'\1_\2', s1)
    return re.sub(all_cap_pattern, r'\1_\2', s2).lower()


def scrub_keys(a_dict: Dict, list_of_keys_to_remove: List[str]) -> Dict:
    """Filter a_dict by removing unwanted key: values listed in list_of_keys_to_remove"""
    if not isinstance(a_dict, dict):
        return a_dict
    return {
        k: v
        for k, v in a_dict.items()
        if k not in list_of_keys_to_remove
    }


def normalize_response(response: Iterable):
    result: List = []

    resource_descriptions = response.get('ResourceDescription', {}) or response.get('ResourceDescriptions', [])
    if isinstance(resource_descriptions, list):
        res = [_jsonify(r_d) for r_d in resource_descriptions]
        _result = [camel_dict_to_snake_dict(r) for r in res]
        result.append(_result)
    else:
        result.append(_jsonify(resource_descriptions))
        result = [camel_dict_to_snake_dict(res) for res in result]
    
    return result


class JsonPatch(list):
    def __str__(self):
        return json.dumps(self)


def list_merge(old, new):
    l = []
    for i in old + new:
        if i not in l:
            l.append(i)
    return l


def op(operation, path, value):
    path = "/{0}".format(path.lstrip("/"))
    return {"op": operation, "path": path, "value": value}


# This is a rather naive implementation. Dictionaries within
# lists and lists within dictionaries will not be merged.
def make_op(path, old, new, strategy):
    if isinstance(old, dict):
        if strategy == "merge":
            new = dict(old, **new)
    elif isinstance(old, list):
        if strategy == "merge":
            new = list_merge(old, new)
    return op("replace", path, new)
