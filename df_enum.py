from lxml import etree

from df_common import SharedState, get_comment


class EnumWrapper:
    """
    Unfortunately, even after the transformations with XSLT, there is still a
    lot of processing that we must do on the XML elements. It's definitely
    possible to reduce the needed processing by allowing slightly different
    from existing header files to be generated, but right now 100% compatibility
    with codegen.pl is desired as a baseline.

    This class takes an enum root element and generates all the necessary data
    that our enum template needs to render.
    """

    def __init__(self, enum_element: etree._Element, shared_state: SharedState):
        self.enum_element = enum_element
        self.shared_state = shared_state
        self.type_dict = shared_state.type_dict
        self.comments = get_comment(self.enum_element, attribute=True)
        self.traits = {
            "base": 0,
            "count": 0,
            "is_complex": False,
        }
        self.attributes: dict[str, dict] = {
        }
        self.hard_references: set[str] = set()

        self.enum_items = []
        self.init_enum_items()

        self.init_attributes()
        self.hard_references = sorted(self.hard_references)

    def init_enum_items(self) -> None:
        """
        Each enum-item element within the enum type is added to the
        self.enum_items list as a dictionary that maps a string of each
        attribute name of the enum-item to the value of that attribute.

        Attributes of enum-items include:
        name: Name of the enum-item (given anon name if not given)
        comments: List of comments of the enum-item
        set_value: Given value of the enum-item (None if not given)
        real_value: Calculated value of the enum-item equal to last_value+1
                    (Or equal to set-value if set-value is given)

        This function also various traits belonging to the overall enum type:
        base: The value of the first enum-item (0 by default)
        count: The total number of enum-items
        is_complex: Whether the enum is "complex"
        last_item_value: value of the last enum-item
        """
        anon_count = 1
        last_value = -1

        for child_element in self.enum_element.getchildren():
            if child_element.tag != "enum-item":
                continue

            enum_item = dict()
            if child_element.get("name"):
                enum_item["name"] = child_element.get("name")
            else:
                enum_item["name"] = "anon_" + (str(anon_count) if anon_count != 0 else '')
                anon_count += 1

            enum_item["comments"] = get_comment(child_element, attribute=True)

            enum_item["set_value"] = int(child_element.get("value")) if child_element.get("value") else None
            enum_item["real_value"] = enum_item["set_value"] if enum_item["set_value"] else 0
            if enum_item["set_value"]:
                if self.traits["count"] == 0:
                    self.traits["base"] = enum_item["set_value"]
                else:
                    self.traits["is_complex"] = True
            else:
                enum_item["real_value"] = last_value + 1

            if self.traits["count"] > 0 and enum_item["real_value"] < last_value:
                raise Exception(f"illegal enum value in {self.enum_element.get('type-name')} "
                                f"{enum_item['name']} = {enum_item['set_value']} < {last_value}")

            self.traits["count"] += 1
            last_value = enum_item["real_value"]

            self.enum_items.append(enum_item)

        self.traits["last_item_value"] = last_value

    def init_attributes(self) -> None:
        """
        Attributes are made up of a dictionary that maps their name to another
        dictionary that contains the values of the "attributes" of these
        attributes.

        "attribute" values include:
        attr_type: Type of the attribute
        default_val: The default value of the attribute (0 if one is not given)
        is_list: Bool for if this attribute is a list (used for static file)
        use_key: Bool for if this attribute uses key (?) (for static file)
        field_meta: Used for static file
        attr_prefix: Prefix for this attribute
        """
        for attr in self.enum_element.iterfind(f"enum-attr"):
            attr_name = attr.get("name")
            if not attr_name:
                raise Exception(f"Unnamed enum-attr in {self.enum_element.get('type-name')}")
            if attr_name in self.attributes:
                raise Exception(f"Duplicate attribute {attr_name}.")

            attr_type, new_reference = self.shared_state.decode_type_name_ref(attr)
            if new_reference is not None and new_reference.get("type-name") != self.enum_element.get("type-name"):
                self.hard_references.add(new_reference.get("type-name"))

            default_value = attr.get("default-value")
            attr_prefix = ""

            base_type_name = attr_type.partition("::")[2]
            if attr_type:
                attr_prefix = f"{base_type_name}::" if base_type_name else ""
                default_value = f"{attr_prefix}{default_value}" if default_value else f"({attr_type})0"
            else:
                attr_type = "const char*"
                default_value = f'"{default_value}"' if default_value else "NULL"

            field_meta = [f"FLD(PRIMITIVE, {attr_name})", f"identity_traits<{attr_type}>::get()", 0, 0]

            is_list = attr.get("is-list")
            use_key = False
            if is_list:
                attr_type = f"enum_list_attr<{attr_type}>"
                default_value = "{ 0, NULL }"
                field_meta = [f"FLD(CONTAINER, {attr_name})", f"identity_traits<{attr_type}>::get()", 0, 0]
            elif attr.get("use-key-name") == "true":
                use_key = True

            attr_dict = {
                "attr_type": attr_type,
                "default_value": default_value,
                "is_list": is_list,
                "use_key": use_key,
                "field_meta": field_meta,
                "attr_prefix": attr_prefix,
                "base_type_name": base_type_name,
            }
            self.attributes[attr_name] = attr_dict
