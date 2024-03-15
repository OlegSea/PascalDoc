from re import findall, split, IGNORECASE
from os import listdir


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


def parse_args(args, additional_args):
    parsed_args = findall(
        "((var\s|const\\s|)([\w\d]*):\s([\w\d]*);*)+", args, IGNORECASE
    )
    parsed_additional_args = findall('(.*)\s*:\s*"(.*)"', additional_args, IGNORECASE)

    pargs = {i[0]: i[1] for i in parsed_additional_args}

    res = {
        "variables": [
            {
                "alloc_type": parse_alloc_type(i[1]),
                "name": i[2],
                "type": i[3],
                "meaning": pargs[i[2]] if i[2] in pargs else "",
            }
            for i in parsed_args
        ],
        "additional_info": {
            k: w for k, w in pargs.items() if k.startswith("__") and k.endswith("__")
        },
    }

    return res


def parse_vars(text, additional_args, is_function=True):
    parsed_vars = findall("\s*(.*):\s*(.*);", text, IGNORECASE)
    parsed_additional_args = findall('(.*)\s*:\s*"(.*)"', additional_args, IGNORECASE)

    pargs = {i[0]: i[1] for i in parsed_additional_args}

    res = []
    for i in parsed_vars:
        for j in split(",\s", i[0]):
            res.append(
                {
                    "alloc_type": "internal" if is_function else "custom",
                    "name": j,
                    "type": i[1],
                    "meaning": pargs[j] if j in pargs else "",
                }
            )

    return res


def strip_module(file):
    _ = file.split("implementation")[1]
    _ = _.split("end.")[0]
    _ = _.split("finalization")[0]
    _ = _.split("initialization")[0]
    return _


def get_functions_from_file(file):
    res = findall(
        "({(?<={)([^}]*)(?=})}\n)*(function|procedure) (.*)\((.*)\)(:(.*)|);\s*(\n*var\n((.*\n)+)(?=(begin)))*",
        file,
        IGNORECASE,
    )

    return [
        {
            "subroutine_type": i[2],
            "name": i[3],
            "return_type": i[6] if i[5] != "" else None,
            "additional_info": parse_args(i[4], i[1])["additional_info"],
            "variables": parse_args(i[4], i[1])["variables"] + parse_vars(i[9], i[1]),
        }
        for i in res
    ]


def parse_main_file(file):
    get_vars = findall(
        "({(?<={)([^}]*)(?=})}\n)*\s*(\n*var((.*\n)+)(?=(begin)|(function)|(procedure)))+",
        file,
    )[0]

    return {
        "subroutine_type": "main",
        "name": "main",
        "variables": parse_vars(get_vars[3], get_vars[1], False),
    }


def parse_file(file):
    modcheck = is_module(file)
    if modcheck:
        file = strip_module(file)
    res = get_functions_from_file(file)
    if not modcheck:
        res += [parse_main_file(file)]
    return res


def parse_folder(folder):
    res = {"files": []}
    for fp in filter(lambda x: x.endswith(".pas"), listdir(folder)):
        with open(folder + fp, "r") as f:
            res["files"].append({"file": fp, "subroutines": parse_file(f.read())})
    return res
