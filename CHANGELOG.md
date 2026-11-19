# Critical changes from porting to Python 3

### General
- Dependencies were updated.
- The dependency to `statlib` has been removed and replaced with `numpy`.

### Interaction Analysis
- The results have been wrong in the Python 2.7.x version of cppstats because duplicate combinations have not been removed 
when counting the combinations with three or more variables. This is fixed in the Python 3 release.

### Testing
- Added a test script that can be used to compare the output of the Python 2 version with the output of the Python 3 version.

To run the test script you need to prepare various things:
1. Clone a project you would like to run the analyses on.
2. Inside the project folder, create a folder named "source" and move everything into there.
  This should look something like this:

*Before:*
```
my_project
|- folder1
|  |- file1.cpp
|- file1.cpp
|- file2.cpp
```

*After:*
```
my_project
|- source
|  |- folder1
|  |  |- file1.cpp
|  |- file1.cpp
|  |- file2.cpp
```

3. Clone the `cppstats` repository.
4. Inside the `cppstats` project folder, create a Python 2 virtual environment and a Python 3 one (called `venv2` and `venv3` respectively).
  Of course, both Python 2 and Python 3 need to be installed on your system.
```shell
python -m venv venv3
virtualenv --python=python2.7 venv2
```

5. Test that the virtual environments are indeed running the correct version. From your `cppstats` folder, run
```shell
source venv2/bin/activate
python --version
deactivate
```
which should yield some Python 2.7.x version. Similarly, try out
```shell
source venv3/bin/activate
python --version
deactivate
```
which should yield some Python 3 (ideally, at least Python 3.10) version.

6. Install all necessary dependencies in both virtual environments (see `setup.py` and `README.md`)

7. Clone the `statlib` repository into the `cppstats` folder. At this point the `cppstats` folder should look something like this:
```
cppstats
|- analyses
|- cppstats
|- lib
|- preparations
|- scripts
|- statlib
|- venv2
|- venv3
|- cppstats.sh
...
```

8. You should now be ready to run the test script. Refer to the command line parameter `--help` for detailed descriptions of 
  the other parameters and options. 

The script will automatically pull the latest versions of `cppstats` for both Python 2 and 3 and also run the specified 
analyses for both versions by using the correct virtual environments.
There is also no need for to change the `cppstats_input.txt` or to run `cppstats.sh` manually. 

### Results
The results are collected and compared. An output can be seen on the command line (with varying degrees of details) and the 
original result files can be found in the `results` folder that is created besides this script.

**Please note** that results for the interaction analysis are not going to match, i.e. this test **will fail**. 
This is caused by the fact that a bug was fixed in the Python 3 version that causes the analysis to not double count particular 
combinations of variables (see `CHANGELOG.md`).



