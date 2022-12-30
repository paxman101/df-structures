from lxml import etree

from df_common import SharedState, get_comment, get_primitive_base, check_bad_attrs, ensure_name, NS_PREFIX


class BitfieldWrapper:
    """
    Takes root bitfield element and generates necessary info for the jinja
    template.
    """

    def __init__(self, bitfield_element: etree._Element, shared_state: SharedState):
        self.bitfield_element = bitfield_element
        self.shared_state = shared_state
        self.type_dict = shared_state.type_dict
        self.bitfield_comments = get_comment(self.bitfield_element, attribute=True)
        self.base_type, self.include_cstdint = get_primitive_base(bitfield_element)
        self.full_name = shared_state.get_fully_qualified_name(self.bitfield_element,
                                                               self.bitfield_element.get("type-name"), namespace=False)
        self.hard_references = set()

        self.fields = []
        self.init_fields()

        self.hard_references = sorted(self.hard_references)

    def init_fields(self) -> None:
        """
        Each field element within the Bitfield type is added to the
        self.fields as a dictionary that maps a string of each
        attribute name of the field to the value of that attribute.
        """
        anon_count = 1
        index = 0

        for field_element in self.bitfield_element.iterfind(f"./{NS_PREFIX}field"):
            if field_element.get(f"{NS_PREFIX}meta") != "number" or \
                    field_element.get(f"{NS_PREFIX}subtype") != "flag-bit":
                raise Exception(f"Invalid bitfield member: {field_element}")

            field_name, anon_count = ensure_name(field_element.get("name"), anon_count)
            check_bad_attrs(field_element)
            field_size = int(field_element.get("count")) if field_element.get("count") else 1
            field_base = self.base_type

            enum_type, enum_element = self.shared_state.decode_type_name_ref(field_element, force_type="enum-type")
            if len(enum_type):
                enum_base_type, _ = get_primitive_base(enum_element, "int32_t")
                if enum_base_type != field_base:
                    raise Exception(f"Bitfield item {field_name} of {self.bitfield_element.get('type-name')} has"
                                    f"a different base type: {enum_base_type}")
                if enum_element is not None and enum_element.get("type-name") != self.bitfield_element.get("type-name"):
                    self.hard_references.add(enum_element.get("type-name"))
                field_base = enum_type

            prefix_comments = get_comment(field_element, attribute=False)
            since = field_element.get("since")
            comment = field_element.get("comment")
            field_index = index
            index += field_size
            field_value = ((1 << field_size) - 1) << field_index

            field_dict = {
                "name": field_name,
                "size": field_size,
                "base": field_base,
                "index": field_index,
                "value": field_value,
                "prefix_comments": prefix_comments,
                "comment": comment,
                "since": since,
            }
            self.fields.append(field_dict)
