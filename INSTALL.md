# cppstats installation


## Overview

cppstats should be runnable under following systems:

* Linux/Ubuntu,
* Mac OS X, and
* Cygwin.

In detail, cppstats was successfully tested under:

- Ubuntu 12.04 64-bit, Python 2.7.3,
- Ubuntu 14.04 64-bit, Python 2.7.6, and
- Cygwin 64-bit, Python 2.7.3 and Python 2.10.3.

Right now, Python 3.x is NOT supported.

Current tested version of srcML:
`srcML Beta (v0.9.5)`


## xUBUNTU

1. checkout repo

    ```bash
    git clone https://github.com/clhunsen/cppstats.git
    ```

2. install needed libraries (+ all dependencies)

    ```bash
    sudo apt-get install astyle  # artistic style (code formatter)
    sudo apt-get install xsltproc  # XSLT 1.0 command line processor
    sudo apt-get install libxml2 libxml2-dev  # library for processing XML
    sudo apt-get install gcc  # GNU compiler collection
    sudo apt-get install python-dev libxml2-dev libxslt-dev zlib1g-dev # cppstats setuptools builds some dependencies from scratch, so these development packages are required
    ```

    - download and install srcML libraries
        - download the deb binary package that is sufficient for your platform from: http://www.srcml.org/#download
        - install the deb package; srcml is available from the command line via 'srcml'

3. install Python package for cppstats and defined Python dependencies

    ```bash
    sudo python setup.py install
    ```
    
    Optionally, you can install it for the current user by appending `--user` to the command.
    
    If you want to install the package in *development mode*, substitute `install` with `develop`.
    
    Run `cppstats --help` for further instructions.

4. supply cppstats with the appropriate paths in `cppstats_input.txt`

    * use full paths like `/local/repos/mpsolve/mpsolve-2.2`
    * each project folder given in the file has to be structured as follows:

        ```
        > /local/repos/cpp-history/mpsolve/mpsolve-2.2/
            > source/ (here are the C source files)
        ```



CYGWIN
------

1. checkout repo

    ```bash
    git clone https://github.com/clhunsen/cppstats.git
    ```

    * **NOTE:** The old branch 'cygwin' is discontinued after version 0.8.
    * Git for Windows:
        * https://github.com/msysgit/msysgit/releases/
        * git bash only
        * checkout as-is, commit as-is

2. install needed libraries (+ all dependencies)

    - https://cygwin.com/install.html
        - install from internet
        - select any mirror
        - do not install any packages yet
        - wait setup to finish

    - **NOTE:** your Windows drives are located at `/cygdrive/`!

    - run following command within cygwin terminal:

        ```bash
        cygstart -- /path/to/cygwin-setup.exe -K http://cygwinports.org/ports.gpg
        ```

    - go through installation process as before, **but** add and select following download site:

        ```
        ftp://ftp.cygwinports.org/pub/cygwinports
        ```

    - install following packages (version number, newer versions should
      also work, except for Python 3.x):

        ```
        - All/Python/
            python (2.7.3-1)
            python-setuptools (15.2-1)
        - All/Libs/
            libxml2 (2.9.1-1)
            libxml2-devel (2.9.1-1)
            libxslt (1.1.27-2)
            libxslt-devel (1.1.27-2)
            zlib (1.2.8-3)
            zlib-devel (1.2.8-3)
        - All/Utils/
            astyle (2.03-1)
        - All/Devel/
            gcc (4.7.3-1)
        + all dependencies you are prompted for
        ```

    - download and install srcML libraries
        - download a binary package that is sufficient for you and your Windows version from: http://www.srcml.org/#download
        - extract into your `$PATH`, so that binaries are available directly
            - e.g., `C:/Program Files/Windows/system32/srcml.exe`

3. install Python package for cppstats and defined Python dependencies

    ```bash
    python setup.py develop --user
    ```

4. supply cppstats with the appropriate paths in `cppstats_input.txt`

    * use relative paths like `data/mpsolve/mpsolve-2.2` and call cppstats relation to these given paths
    * each project folder given in the file has to be structured as follows:

        ```
        > data/mpsolve/mpsolve-2.2
            > source/ (here are the C source files)
        ```
