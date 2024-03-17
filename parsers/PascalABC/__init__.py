from re import findall, split, IGNORECASE, compile
from os import listdir

basic_types = [
    "shortint",
    "smallint",
    "integer",
    "longint",
    "int64",
    "byte",
    "word",
    "longword",
    "cardinal",
    "uint64",
    "BigInteger",
    "real",
    "double",
    "single" "decimal",
    "boolean",
    "string",
    "char",
]


def find_custom_types(file):
    type_blocks = "\n".join(
        [
            i[0]
            for i in findall(
                "type((.*\n)+)(?=(begin)|(function)|(procedure)|(implementation))", file
            )
        ]
    )

    return {i[0]: i[1] for i in findall("\s*(.*)\s=\s(.*);", type_blocks)}


def replace_custom_types(type, custom_types):
    return custom_types[type] if type in custom_types else type


def is_module(file):
    return findall("\n*unit ([\w\d]+);", file, IGNORECASE) != []


def parse_alloc_type(alloc_type):
    match (alloc_type):
        case "var ":
            return "rw_pointer"
        case "const ":
            return "r_pointer"
        case "":
            return "copy"


def parse_arrays(variable):
    r = compile(
        f"^(()|((array\s*(\[([\d\.,]*)\])*\sof\s)*)|(set\sof))\s*({'|'.join(basic_types)})$"
    )
    res = findall(r, variable)
    print(variable, res)
    return variable


def parse_args(args, additional_args, return_type, custom_types):
    parsed_args = findall(
        "((var\s|const\\s|)([\w\d]*):\s([\w\d]*);*)+", args, IGNORECASE
    )
    parsed_additional_args = findall('(.*)\s*:\s*"(.*)"', additional_args, IGNORECASE)

    pargs = {i[0].lower(): i[1] for i in parsed_additional_args}

    res = {
        "variables": [
            {
                "alloc_type": parse_alloc_type(i[1]),
                "name": i[2],
                "type": parse_arrays(replace_custom_types(i[3], custom_types)),
                "meaning": pargs[i[2].lower()] if i[2].lower() in pargs else "",
            }
            for i in parsed_args
        ],
        "additional_info": {
            k: w for k, w in pargs.items() if k.startswith("__") and k.endswith("__")
        },
    }

    if return_type:
        res["variables"].append(
            {
                "alloc_type": "result",
                "name": "Result",
                "type": replace_custom_types(return_type, custom_types),
                "meaning": pargs["result"] if "result" in pargs else "",
            }
        )

    return res


def parse_vars(text, additional_args, custom_types, is_main=False):
    parsed_vars = findall("\s*(.*):\s*(.*);", text, IGNORECASE)
    parsed_additional_args = findall('(.*)\s*:\s*"(.*)"', additional_args, IGNORECASE)

    pargs = {i[0]: i[1] for i in parsed_additional_args}

    res = []
    for i in parsed_vars:
        for j in split(",\s", i[0]):
            res.append(
                {
                    "alloc_type": "internal" if not is_main else "custom",
                    "name": j,
                    "type": replace_custom_types(i[1], custom_types),
                    "meaning": pargs[j.lower()] if j.lower() in pargs else "",
                }
            )

    return res


def strip_module(file):
    _ = file.split("implementation")[1]
    _ = _.split("end.")[0]
    _ = _.split("finalization")[0]
    _ = _.split("initialization")[0]
    return _


def get_functions_from_file(file, custom_types):
    search = findall(
        "({(?<={)([^}]*)(?=})}\n)*(function|procedure) (.*)\((.*)\)(:(.*)|);\s*(\n*var\n((.*\n)+)(?=(begin)))*",
        file,
        IGNORECASE,
    )

    res = []

    for i in search:
        return_type = i[6] if i[5] != "" else None
        parsed_args = parse_args(i[4], i[1], return_type, custom_types)
        res.append(
            {
                "subroutine_type": i[2],
                "name": i[3],
                "return_type": i[6] if i[5] != "" else None,
                "additional_info": parsed_args["additional_info"],
                "variables": parsed_args["variables"]
                + parse_vars(i[9], i[1], custom_types),
            }
        )

    return res


def parse_main_file(file, custom_types):
    get_vars = findall(
        "({(?<={)([^}]*)(?=})}\n)*\s*(\n*var((.*\n)+)(?=(begin)|(function)|(procedure)))+",
        file,
    )[0]

    return {
        "subroutine_type": "main",
        "name": "main",
        "variables": parse_vars(get_vars[3], get_vars[1], custom_types, False),
    }


def parse_file(file, custom_types):
    modcheck = is_module(file)
    if modcheck:
        file = strip_module(file)
    res = get_functions_from_file(file, custom_types)
    if not modcheck:
        res += [parse_main_file(file, custom_types)]
    return res


def parse_folder(folder):
    custom_types = {}
    for fp in filter(lambda x: x.endswith(".pas"), listdir(folder)):
        with open(folder + fp, "r") as f:
            custom_types = custom_types | find_custom_types(f.read())

    res = {"files": []}
    for fp in filter(lambda x: x.endswith(".pas"), listdir(folder)):
        with open(folder + fp, "r") as f:
            res["files"].append(
                {"file": fp, "subroutines": parse_file(f.read(), custom_types)}
            )
    return res
