from pathlib import Path
from typing import Optional
import re

from lxml import etree

PRIMITIVE_TYPES_SET = {
    "int8_t", "uint8_t", "int16_t", "uint16_t",
    "int32_t", "uint32_t", "int64_t", "uint64_t",
    "long",
    "s-float", "d-float",
    "bool", "flag-bit",
    "padding", "static-string",
}

PRIMITIVE_ALIASES_DICT = {
    "s-float": "float",
    "d-float": "double",
    "static-string": "char",
    "flag-bit": "void",
    "padding": "static-string",
}

EXPORT_PREFIX = "DFHACK_EXPORT"
NS_URI = "http://github.com/peterix/dfhack/lowered-data-definition"
NS_PREFIX = "{http://github.com/peterix/dfhack/lowered-data-definition}"


# Static functions:

def is_primitive_type(tag_name: str) -> bool:
    return tag_name in PRIMITIVE_TYPES_SET


def primitive_type_name(tag_name: str) -> str:
    if tag_name not in PRIMITIVE_TYPES_SET:
        raise Exception(f"Not primitive: {tag_name}")
    return PRIMITIVE_ALIASES_DICT.get(tag_name) if PRIMITIVE_ALIASES_DICT.get(tag_name) else tag_name


def get_primitive_base(element: etree._Element, default="uint32_t") -> tuple[str, bool]:
    """
    Verifies a type is primitive, returning the type-name attribute or default
    if the element doesn't have a type-name attribute.
    Also returns a bool that indicates if the type is in cstdint.
    """
    base_type = element.get("base-type") or default
    include_cstdint = bool(re.match(r"u?int[136]?[2468]_t", base_type))
    if not is_primitive_type(base_type):
        raise Exception(f"Must be primitive: {base_type}")
    return base_type, include_cstdint


def get_comment(element: etree._Element, tag=True, attribute=False) -> list[str]:
    comment_list = []
    comment_element = element.find("./comment")
    if comment_element is not None and tag:
        comment_text = comment_element.text
        comment_list.extend([comment.strip() for comment in comment_text.split("\n") if comment != ""])

    if attribute:
        if element.get("comment"):
            comment_list.append(element.get("comment"))
        if element.get("since"):
            comment_list.append("Since " + element.get("since"))

    return comment_list


def check_name(name_to_check: str) -> str:
    """
    Checks for invalid characters in name_to_check
    """
    if not re.match(r"^[_a-zA-Z][_a-zA-Z0-9]*$", name_to_check):
        raise Exception(f"Invalid identifier: {name_to_check}")
    return name_to_check


def ensure_name(name_to_check: Optional[str], anon_count: int) -> tuple[str, int]:
    """
    Checks if name_to_check is None. If it is, an anonymous name is generated
    with the number given in anon_count and returned. If not, name_to_check is
    passed back.
    """
    returned_name = name_to_check
    if not name_to_check:
        returned_name = "anon" + (f"_{anon_count}" if anon_count != 0 else '')
        anon_count += 1
    return check_name(returned_name), anon_count


def check_bad_attrs(element: etree._Element, allow_size=False, allow_align=False) -> None:
    if not allow_size and element.get("size"):
        raise Exception(f"Cannot use size for {element}")
    if element.get("offset"):
        raise Exception(f"Cannot use offset for {element}")
    if not allow_align and element.get("alignment"):
        raise Exception(f"Cannot use alignment for {element}")


class SharedState:
    """
    Holds shared state needed between the different modules used by codegen.py
    as well as various functions that require access to this state.
    """

    def __init__(self, main_namespace: str):
        self.type_dict: dict[str, etree._Element] = {}
        self.type_files_dict: dict[str, Path] = {}
        self.global_dict: dict[str, etree._Element] = {}
        self.global_files_dict: dict[str, Path] = {}
        self.main_namespace = main_namespace

    # lxml's Element type has a prefixed underscore but _Element isn't
    # actually a "private" type
    def add_type_to_dict(self, element: etree._Element, source_xml_path: Path) -> None:
        type_name = element.get("type-name")
        if not type_name:
            raise Exception(f"type-name not defined for {element} in file {source_xml_path}")

        if type_name in self.type_dict:
            raise Exception(f"Duplicate definition of global {type_name}")
        check_bad_attrs(element)
        self.type_dict[type_name] = element
        self.type_files_dict[type_name] = source_xml_path

    def add_global_to_dict(self, element: etree._Element, source_xml_path: Path) -> None:
        name = element.get("name")
        if not name:
            raise Exception(f"Global {element} without a name in file {source_xml_path}")

        if name in self.global_dict:
            raise Exception(f"Duplicate definition of global {name}")
        check_bad_attrs(element)
        self.global_dict[name] = element
        self.global_files_dict[name] = source_xml_path

    def decode_type_name_ref(self, element: etree._Element, force_type: str = None, attr_name: str = "type-name") \
            -> tuple[str, Optional[etree._Element]]:
        """
        Copied from codegen.pl.
        'Interpret the type-name field of a tag'
        :param force_type:
        :param element:
        :param attr_name:
        :return (reference_type, reference_element): The full typename of the given reference, and also it's element
        """
        type_name = element.get(attr_name)
        if not type_name:
            return "", None

        if type_name in PRIMITIVE_TYPES_SET:
            if force_type and force_type != "primitive":
                raise Exception(f"Cannot use type {type_name} as {attr_name} here: {element}.")
            return primitive_type_name(type_name), None
        else:
            if force_type and force_type != self.type_dict[type_name].get(f"{NS_PREFIX}meta"):
                raise Exception(f"Cannot use type {type_name} as {attr_name} here: {element}.")
            rtype = self.main_namespace + "::" + type_name
            return rtype, self.type_dict[type_name]

    def get_fully_qualified_name(self, element: etree._Element, name: str, namespace=True) -> str:
        names = []
        if namespace:
            names.append(self.main_namespace)
        for parent in element.xpath("ancestor::*"):
            if parent.tag == f"{NS_PREFIX}global-type":
                names.append(parent.get("type-name"))
            elif parent.tag == f"{NS_PREFIX}global-object":
                names.append("global")
            elif td_name := parent.get(f"{NS_PREFIX}typedef-name"):
                names.append(td_name)
        if name:
            names.append(name)

        return "::".join(names)
