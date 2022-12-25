import argparse
from lxml import etree
from pathlib import Path


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


def read_xml_files(input_directory: Path):
    type_dict = dict()
    global_dict = dict()

    def check_bad_attrs(element):
        pass

    def add_type_to_dict(element):
        pass

    def add_global_to_dict(element):
        pass

    # Import the two XSLT files in the script dir to transform the XML files we read.
    # Each XML file gets transformed by lower-1.xslt, then the result is then transformed by lower-2.xslt.
    script_directory = Path(__file__).parent
    xslt1_transform = etree.XSLT(etree.parse(script_directory / "lower-1.xslt"))
    xslt2_transform = etree.XSLT(etree.parse(script_directory / "lower-2.xslt"))

    xml_doc_list = list()
    ns_prefix = "{http://github.com/peterix/dfhack/lowered-data-definition}"
    for xml_path in sorted(input_directory.glob("df.*.xml")):
        xml_etree = etree.parse(xml_path)
        xml_etree = xslt2_transform(xslt1_transform(xml_etree))
        xml_doc_list.append(xml_etree)
        for global_type in xml_etree.iterfind(f"{ns_prefix}global-type"):
            add_type_to_dict(global_type)
        for global_object in xml_etree.iterfind(f"{ns_prefix}global-object"):
            add_global_to_dict(global_object)


def main():
    input_directory, output_directory, main_namespace = get_arguments()
    read_xml_files(input_directory)


if __name__ == "__main__":
    main()
