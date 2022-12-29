from pathlib import Path
from typing import Optional

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


# Static functions:

def is_primitive_type(tag_name: str) -> bool:
    return tag_name in PRIMITIVE_TYPES_SET


def primitive_type_name(tag_name: str) -> str:
    if tag_name not in PRIMITIVE_TYPES_SET:
        raise Exception(f"Not primitive: {tag_name}")
    return PRIMITIVE_ALIASES_DICT.get(tag_name) if PRIMITIVE_ALIASES_DICT.get(tag_name) else tag_name


def get_comment(element: etree._Element, attribute=False) -> list[str]:
    comment_list = []
    comment_element = element.find("./comment")
    if comment_element is not None:
        comment_text = comment_element.text
        comment_list.extend([comment.strip() for comment in comment_text.split("\n") if comment != ""])

    if attribute:
        if element.get("comment"):
            comment_list.append(element.get("comment"))
        if element.get("since"):
            comment_list.append("Since " + element.get("since"))

    return comment_list


class SharedState:
    """
    Holds shared state needed between the different modules used by codegen.py
    as well as various functions that require access to this state.
    """

    def __init__(self, type_dict: dict[str, etree._Element], type_files_dict: dict[str, Path],
                 global_dict: dict[str, etree._Element], global_files_dict: dict[str, Path], main_namespace: str):
        self.type_dict = type_dict
        self.type_files_dict = type_files_dict
        self.global_dict = global_dict
        self.global_files_dict = global_files_dict
        self.main_namespace = main_namespace

    def decode_type_name_ref(self, element: etree._Element, force_type: str = None, attr_name: str = None) \
            -> tuple[str, Optional[etree._Element]]:
        """
        Copied from codegen.pl.
        'Interpret the type-name field of a tag'
        :param force_type:
        :param element:
        :param attr_name:
        :return (reference_type, reference_element): The full typename of the given reference, and also it's element
        """
        if not attr_name:
            attr_name = "type-name"
        type_name = element.get(attr_name)
        if not type_name:
            return "", None

        if type_name in PRIMITIVE_TYPES_SET:
            if force_type and force_type != "primitive":
                raise Exception(f"Cannot use type {type_name} as {attr_name} here: {element}.")
            return primitive_type_name(type_name), None
        else:
            if force_type and force_type != self.type_dict[type_name] != element.get("ld:meta"):
                raise Exception(f"Cannot use type {type_name} as {attr_name} here: {element}.")
            rtype = self.main_namespace + "::" + type_name
            return rtype, self.type_dict[type_name]
