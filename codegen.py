import argparse
import re

from lxml import etree
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from df_common import SharedState, EXPORT_PREFIX
from df_enum import EnumWrapper

NS_URI = "http://github.com/peterix/dfhack/lowered-data-definition"
NS_PREFIX = "{http://github.com/peterix/dfhack/lowered-data-definition}"

jinja_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "header_templates"),
                        trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True, newline_sequence="\n")
enum_template = jinja_env.get_template("enum.h.jinja")
# To implement:
bitfield_template = None
struct_template = None


def get_arguments() -> tuple[Path, Path, str]:
    arg_parser = argparse.ArgumentParser(prog="codegen.py", description="Generates DFHack headers from XML files.")
    arg_parser.add_argument("input_directory", default=".", nargs="?",
                            help="The directory containing XML files to parse.")
    arg_parser.add_argument("output_directory", default="codegen", nargs="?",
                            help="Directory to output generated header files.")
    arg_parser.add_argument("main_namespace", default="df", nargs="?",
                            help="Namespace generated headers will be within.")
    args = arg_parser.parse_args()
    return Path(args.input_directory), Path(args.output_directory), args.main_namespace


def process_xml_files(shared_state: SharedState, input_directory: Path, output_directory: Path):
    # Import the two XSLT files in the script dir to transform the XML files we read.
    # Each XML file gets transformed by lower-1.xslt, then the result is then transformed by lower-2.xslt.
    script_directory = Path(__file__).parent
    xslt1_transform = etree.XSLT(etree.parse(script_directory / "lower-1.xslt"))
    xslt2_transform = etree.XSLT(etree.parse(script_directory / "lower-2.xslt"))

    xml_doc_list = []
    parser = etree.XMLParser(remove_blank_text=True)
    codegen_out_xml = etree.ElementTree(etree.XML(
        f'<ld:data-definition xmlns:ld="{NS_URI}">\n    </ld:data-definition>', parser))
    for xml_path in sorted(input_directory.glob("df.*.xml")):
        xml_etree = etree.parse(xml_path)
        xml_etree: etree._XSLTResultTree = xslt2_transform(xslt1_transform(xml_etree))
        for element in xml_etree.getroot().iterchildren():
            if element.tag == f"{NS_PREFIX}global-type":
                shared_state.add_type_to_dict(element, xml_path)
            elif element.tag == f"{NS_PREFIX}global-object":
                shared_state.add_global_to_dict(element, xml_path)
            codegen_out_xml.getroot().append(element)

    # codegen_out_xml.write(output_directory / "codegen.out.xml")


def render_enum_header(enum_element: etree._Element, enum_typename: str, shared_state: SharedState) -> str:
    base_type = enum_element.get("base-type") or "int32_t"
    include_cstdint = re.match(r"u?int[136]?[2468]_t", base_type) if base_type else False
    enum_wrapper = EnumWrapper(enum_element, shared_state)
    return enum_template.render(
        comments=enum_wrapper.comments,
        include_cstdint=include_cstdint,
        export_prefix=EXPORT_PREFIX,
        main_namespace=shared_state.main_namespace,
        base_type=base_type,
        enum_typename=enum_typename,
        traits=enum_wrapper.traits,
        enum_items=enum_wrapper.enum_items,
        attributes=enum_wrapper.attributes,
        hard_references=enum_wrapper.hard_references,
    )


def generate_type_headers(shared_state: SharedState, output_directory: Path):
    type_renderers = {
        "enum-type": render_enum_header,
    }

    for type_name, type_element in shared_state.type_dict.items():
        render_func = type_renderers.get(type_element.get(f"{NS_PREFIX}meta"))
        if render_func is None:
            print(f"Error: Unhandled type {type_name} in file {shared_state.type_files_dict[type_name]}!")
            continue

        output = render_func(type_element, type_name, shared_state)
        with open(output_directory / f"{type_name}.h", "w") as header_file:
            header_file.write(output)


def main():
    input_directory, output_directory, main_namespace = get_arguments()
    shared_state = SharedState(main_namespace)
    process_xml_files(shared_state, input_directory, output_directory)
    generate_type_headers(shared_state, output_directory)


if __name__ == "__main__":
    main()
