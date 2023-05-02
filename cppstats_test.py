import click
import os
import shutil
import subprocess
import math
from colorama import Fore, Style
from datetime import datetime

ANALYSES = ["general", "generalvalues", "discipline", "featurelocations", "derivative", "interaction"]
OUTPUT_FILE = {
    "general": ["cppstats"],
    "generalvalues": ["merged_scattering_degrees", "merged_tangling_degrees", "metric_values",
                      "nesting_degrees_toplevel_branches"],
    "discipline": ["cppstats_discipline"],
    "featurelocations": ["cppstats_featurelocations", "listoffeatures"],
    "derivative": ["cppstats_derivative"],
    "interaction": ["cppstats_interaction"]
}

INPUT_FILE_NAME = "cppstats_input.txt"

PY2_BRANCH = "py2numpy"
PY3_BRANCH = "py3"
BRANCHES = {2: PY2_BRANCH,
            3: PY3_BRANCH}

PY2_VENV = "venv2/bin/activate"
PY3_VENV = "venv3/bin/activate"
VENVS = {2: PY2_VENV,
         3: PY3_VENV}


def create_result_dir(path, name):
    if not os.path.exists(path):
        os.mkdir(path)

    results_path = os.path.join(path, f"{name}_{datetime.now()}")
    os.mkdir(results_path)
    return results_path


def git_reset(verbose, cppstats_path):
    if verbose:
        subprocess.run(f"cd {cppstats_path} ; git reset --hard",
                       shell=True, executable='/bin/bash')
    else:
        subprocess.run(f"cd {cppstats_path} ; git reset --hard",
                       shell=True, executable='/bin/bash',
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


def run_python(analysis, results_path, project_path, cppstats_path, verbose, ver):
    # checkout correct branch
    if verbose:
        print(f"    {Fore.CYAN}Checking out branch and pulling for Python {ver} ({BRANCHES[ver]}){Style.RESET_ALL}")

    git_reset(verbose, cppstats_path)

    if verbose:
        subprocess.run(f"cd {cppstats_path} ; git checkout {BRANCHES[ver]}",
                       shell=True, executable='/bin/bash')
        subprocess.run(f"cd {cppstats_path} ; git pull",
                       shell=True, executable='/bin/bash')
    else:
        subprocess.run(f"cd {cppstats_path} ; git checkout {BRANCHES[ver]}",
                       shell=True, executable='/bin/bash',
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        subprocess.run(f"cd {cppstats_path} ; git pull",
                       shell=True, executable='/bin/bash',
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

    # rewrite the input file
    if verbose:
        print(f"    {Fore.CYAN}Writing input file{Style.RESET_ALL}")
    with open(os.path.join(cppstats_path, INPUT_FILE_NAME), "w") as f:
        f.write(project_path)

    # delete all temporary cppstats files and folders
    if verbose:
        print(f"    {Fore.CYAN}Deleting temporary cppstats files and folders{Style.RESET_ALL}")
    for filename in os.listdir(project_path):
        if filename == "source":
            continue

        file_path = os.path.join(project_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)#
                if verbose:
                    print(f"    Deleting file {filename}")
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                if verbose:
                    print(f"    Deleting folder {filename}")
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

    # execute cppstats
    if verbose:
        print(f"    {Fore.CYAN}Running cppstats{Style.RESET_ALL}")
    if verbose:
        subprocess.run(f"source {os.path.join(cppstats_path, VENVS[ver])} ; cd {cppstats_path} ; "
                       f"./cppstats.sh --kind {analysis} --list",
                       shell=True, executable='/bin/bash')
    else:
        subprocess.run(f"source {os.path.join(cppstats_path, VENVS[ver])} ; cd {cppstats_path} ; "
                       f"./cppstats.sh --kind {analysis} --list",
                       shell=True, executable='/bin/bash',
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

    # copy result files
    if verbose:
        print(f"    {Fore.CYAN}Copying results{Style.RESET_ALL}")

    for filename in OUTPUT_FILE[analysis]:
        csv_filename = os.path.join(project_path, filename + ".csv")
        results_filename = os.path.join(results_path, f"result_py{ver}_{analysis}_{filename}.csv")
        shutil.copy2(csv_filename, results_filename)

    # reset branch
    if verbose:
        print(f"    {Fore.CYAN}Resetting branch '{BRANCHES[ver]}'{Style.RESET_ALL}")

    git_reset(verbose, cppstats_path)

    if verbose:
        print(f"    {Fore.GREEN}Done{Style.RESET_ALL}")


def do_analysis(analysis, results_path, project_path, cppstats_path, verbose):
    analysis_path = os.path.join(results_path, f"analysis_{analysis}")
    os.mkdir(analysis_path)

    print(f"  Python 2 - {analysis}")
    run_python(analysis, analysis_path, project_path, cppstats_path, verbose, 2)

    print(f"  Python 3 - {analysis}")
    run_python(analysis, analysis_path, project_path, cppstats_path, verbose, 3)


def parse_result_file(file, project_name):
    # read file  without newlines at the end
    with open(file, "r") as f:
        lines = list(map(lambda l: l[:-1], f.readlines()))

    # read the separator, it is written in the first line in double quotes, e.g. ","
    if "sep=" in lines[0]:
        sep = lines[0].split('=')[1][0]
    else:
        sep = ";"  # see below; there is no discipline in the discipline analysis

    # filter out paths in the first column
    result = []
    for line in lines:
        fst = line.split(sep)[0]
        if project_name in fst:
            line = line.replace(fst, project_name)
        result.append(line)
    return lines


def compute_difference(analysis, results_path, verbose, project_name, file_py2, file_py3, filename, i, n):
    match = True
    line_with_col_names = 1
    # parse the two result files

    if verbose:
        print(f"  Comparing results: {filename} ({i}/{n})")
        print(f"    {Fore.CYAN}Reading result files{Style.RESET_ALL}")
    result_py2 = parse_result_file(file_py2, project_name)
    result_py3 = parse_result_file(file_py3, project_name)

    if verbose:
        print(f"    {Fore.CYAN}Comparing result files{Style.RESET_ALL}")
    # compare them by length; if the two files have different amounts of lines, then the comparison fails
    if len(result_py2) != len(result_py3):
        print(f"    {Fore.RED}Length mismatch{Style.RESET_ALL}")
        print(f"    Python 2 produced {len(result_py2)} lines")
        print(f"    Python 3 produced {len(result_py3)} lines")
        match = False

    # get the separator char from the first line
    if "sep=" in result_py2[0] and "sep=" in result_py3[0]:
        sep_py2 = result_py2[0].split('=')[1][0]
        sep_py3 = result_py3[0].split('=')[1][0]
        if len(sep_py2) != len(sep_py3):
            print(f"    {Fore.RED}Separator mismatch{Style.RESET_ALL}")
            print(f"    Python 2 uses '{sep_py2}'")
            print(f"    Python 3 uses '{sep_py3}'")
            match = False

        sep = sep_py2
    else:  # in discipline (ironically...), there is no separator written at the top
        sep = ";"
        line_with_col_names = 0

    # get number of columns
    col_names = result_py2[line_with_col_names].split(sep)
    py2_cols = len(result_py2[1].split(sep))
    py3_cols = len(result_py3[1].split(sep))
    # compare them by length; if the two files have different amounts of columns, then the comparison fails
    if py2_cols != py3_cols:
        print(f"    {Fore.RED}Column mismatch{Style.RESET_ALL}")
        print(f"    Python 2 produced {py2_cols} columns")
        print(f"    Python 3 produced {py3_cols} columns")
        match = False

    if match:
        if (filename == "merged_tangling_degrees" or
                filename == "merged_scattering_degrees" or
                filename == "cppstats_derivative"):
            match = line_subset_difference(analysis, results_path, verbose, project_name, result_py2,
                                           result_py3, filename, line_with_col_names, py2_cols, sep, col_names)
        else:
            match = default_difference(analysis, results_path, verbose, project_name, result_py2, result_py3, filename,
                                       line_with_col_names, py2_cols, sep, col_names)

    if match:
        print(f"  {Fore.GREEN}Success - {analysis} / {filename}: {Style.RESET_ALL}Results are matching")
    else:
        print(f"  {Fore.RED}Fail - {analysis} / {filename}: {Style.RESET_ALL}Results are not matching")


def divide_line(line):
    if ";" in line:
        l = line.split(";")
        values = l[0].split(",") + [l[1]]
        values = sorted(values)
        return values
    else:
        values = line.split(",")
        values = sorted(values)
        return values


def line_subset_difference(analysis, results_path, verbose, project_name, result_py2, result_py3,
                           filename, line_with_col_names, py2_cols, sep, col_names):
    match = True

    # Transform both line lists into lists of sorted lists of line components:
    # y,x,z;x&&z -> ["x", "x&&z", "y", "z"]
    result_py2 = sorted(list(map(lambda line: divide_line(line), result_py2)))
    result_py3 = sorted(list(map(lambda line: divide_line(line), result_py3)))

    if verbose:
        for i in range(len(result_py2)):
            print(f"  {result_py2[i]}")
            print(f"  {result_py3[i]}\n")

    # first, check whether all lines from the py2 output are in the py3 output as well
    for l in range(2, len(result_py2)):
        line_py2 = result_py2[l]

        if line_py2 in result_py3:
            if verbose:
                print(f"    {Fore.GREEN}Line match     Py2 <= Py3{Style.RESET_ALL} "
                      f"{Fore.CYAN}Line {l + 1}{Style.RESET_ALL}")
        else:
            match = False
            print(f"    {Fore.RED}Line missing   Py2 <= Py3{Style.RESET_ALL} "
                  f"{Fore.CYAN}Line {l + 1}{Style.RESET_ALL}")

    # first, check whether all lines from the py2 output are in the py3 output as well
    for l in range(2, len(result_py3)):
        line_py3 = result_py3[l]

        if line_py3 in result_py2:
            if verbose:
                print(f"    {Fore.GREEN}Line match     Py2 >= Py3{Style.RESET_ALL} "
                      f"{Fore.CYAN}Line {l + 1}{Style.RESET_ALL}")
        else:
            match = False
            print(f"    {Fore.RED}Line missing   Py2 >= Py3{Style.RESET_ALL} "
                  f"{Fore.CYAN}Line {l + 1}{Style.RESET_ALL}")

    return match


def default_difference(analysis, results_path, verbose, project_name, result_py2, result_py3, filename,
                       line_with_col_names, py2_cols, sep, col_names):
    match = True

    # compare them line by line
    for l in range(1, len(result_py2)):
        line_py2 = result_py2[l]
        line_py3 = result_py3[l]

        # compare column by column
        for c in range(0, py2_cols):
            try:
                col_py2 = line_py2.split(sep)[c]
            except:
                print(f"    {Fore.RED}Column mismatch{Style.RESET_ALL}")
                print(f"    Line {l} in the output of Python 2 does not "
                      f"have enough columns ({c - 1} instead of {py2_cols})")
                match = False
                continue
            try:
                col_py3 = line_py3.split(sep)[c]
            except:
                print(f"    {Fore.RED}Column mismatch{Style.RESET_ALL}")
                print(f"    Line {l} in the output of Python 3 does not "
                      f"have enough columns ({c - 1} instead of {py2_cols})")
                match = False
                continue

            # try to parse a float
            try:
                float_py2 = float(col_py2)
                float_py3 = float(col_py3)

                if not math.isclose(float_py2, float_py3):
                    print(f"    {Fore.RED}Float value mismatch{Style.RESET_ALL}")
                    print(f"    {Fore.CYAN}Line {l + 1}, Column {c + 1} ({col_names[c]}){Style.RESET_ALL} - "
                          f"Python 2: {col_py2} - Python 3: {col_py3}")
                    match = False
                else:
                    if verbose:
                        print(f"    {Fore.GREEN}Float value match{Style.RESET_ALL}"
                              f"    {Fore.CYAN}Line {l + 1}, Column {c + 1} ({col_names[c]}){Style.RESET_ALL} - "
                              f"Python 2: {col_py2} - Python 3: {col_py3}")
            except:
                # if the conversion to float fails, then compare strings
                if col_py2 != col_py3:
                    print(f"    {Fore.RED}Value mismatch{Style.RESET_ALL}")
                    print(f"    {Fore.CYAN}Line {l + 1}, Column {c + 1} ({col_names[c]}){Style.RESET_ALL} - "
                          f"Python 2: '{col_py2}' - Python 3: '{col_py3}'")
                    match = False
                else:
                    if verbose:
                        print(f"    {Fore.GREEN}Value match{Style.RESET_ALL}"
                              f"    {Fore.CYAN}Line {l + 1}, Column {c + 1} ({col_names[c]}){Style.RESET_ALL} - "
                              f"Python 2: '{col_py2}' - Python 3: '{col_py3}'")

    return match


@click.command()
@click.option("-v", "--verbose", "verbose",
              is_flag=True,
              show_default=True,
              default=False,
              help="Print more output.")
@click.option("-n", "--notests", "notests",
              is_flag=True,
              show_default=True,
              default=False,
              help="If set, the tests are not executed.")
@click.option("-a", "--analysis", "analysis",
              default="general",
              type=click.Choice(["all"] + ANALYSES),
              help="The kind of analysis to execute.")
@click.option("-r", "--result-path", "result_path",
              default="results",
              type=click.Path(exists=False, file_okay=False, dir_okay=True, readable=True),
              help="The path where the results are to be stored.")
@click.option("-p", "--project-path", "project_path",
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
              help="The path where the project lies.",
              required=True)
@click.option("-c", "--cppstats-path", "cppstats_path",
              default="../cppstats",
              type=click.Path(exists=False, file_okay=False, dir_okay=True, readable=True),
              help="The path where cppstats lies.")
def main(analysis, result_path, project_path, cppstats_path, verbose, notests):
    analyses = [analysis] if analysis != "all" else ANALYSES

    # delete trailing / from path
    if project_path[-1] == "/":
        project_path = project_path[:-2]

    project_name = project_path.split("/")[-1]
    result_path = create_result_dir(result_path, project_name)

    i = 1
    for a in analyses:
        print(f"Running analysis {analysis} on project '{project_name}' ({i}/{len(analyses)})")
        do_analysis(a, result_path, project_path, cppstats_path, verbose)

        if notests:
            continue

        j = 1
        for filename in OUTPUT_FILE[a]:
            out_py2 = os.path.join(result_path, f"analysis_{a}", f"result_py2_{a}_{filename}.csv")
            out_py3 = os.path.join(result_path, f"analysis_{a}", f"result_py3_{a}_{filename}.csv")
            compute_difference(a, result_path, verbose, project_name, out_py2, out_py3, filename, j,
                               len(OUTPUT_FILE[a]))
            j += 1
        i += 1


if __name__ == "__main__":
    main()
