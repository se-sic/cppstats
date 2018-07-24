# cppstats


## License & Copyright
* Copyright (C) 2009-2015 University of Passau, Germany

All rights reserved.

cppstats is covered by the GNU Lesser General Public License.
The full license text is distributed with this software. See the `LICENSE.LESSER` file.

### Main Developers

* Jörg Liebig <joliebig@fim.uni-passau.de>, University of Passau
* Claus Hunsen <hunsen@fim.uni-passau.de>, University of Passau

### Further Contributors

* Andreas Ringlstetter <andreas.ringlstetter@gmail.com>, OTH Regensburg

## What is it?

cppstats is a suite of analyses for measuring C preprocessor-based variability in software product lines.

Currently, cppstats supports following analyses:

* `general`,
* `generalvalues`,
* `discipline`,
* `featurelocations`,
* `derivative`, and
* `interaction`.

For detailed information on each kind of analysis, please refer to the corresponding paragraph below in this file.

For further information, please see the tool's homepage at: http://www.fosd.net/cppstats

Details of the latest version can be found on the cppstats project site at GitHub under https://github.com/clhunsen/cppstats/.


## System Requirements

* srcML (http://www.srcml.org/)
* astyle (http://astyle.sourceforge.net/)
* libxml2 (http://www.xmlsoft.org/)
* xsltproc (http://xmlsoft.org/XSLT/xsltproc2.html)
* gcc (https://gcc.gnu.org/)
* Python requirements from `setup.py`


## Installation

cppstats should be runnable under following systems:

* Linux/Ubuntu,
* Mac OS X, and
* Cygwin.

Please see the file called `INSTALL.md` for detailed instructions for each
system.

In detail, cppstats was successfully tested under:

* Ubuntu 12.04, Python 2.7.*, and
* Cygwin, Python 2.7.*.

Right now, Python 3.x is **NOT** supported.


## Quick Start

- Install cppstats using `sudo python setup.py install`.

- Supply cppstats with the appropriate paths in `cppstats_input.txt`

    * use full paths like `/local/repos/mpsolve/mpsolve-2.2`
    * each project folder given in the file has to be structured as follows:

        ```
        > /local/repos/cpp-history/mpsolve/mpsolve-2.2/
            > source/ (here are the C source files)
        ```

- Then run:
    ```
    $ cppstats --kind <K>
    ```

    `<K>` must be one of the analyses listed in the introduction. Also, have a look on `cppstats --help` for further command line options.

- The output files for each analysis are written to the folders given in the file `cppstats_input.txt`.


## Analyses

* `GENERAL`
    - Measurement of CPP-related metrics regarding scattering,
      tangling, and nesting
    - returns a list of metrics for each file, and a list of metric
      values for the whole project folder

* `GENERALVALUES`
     - Calculation of scattering, tangling, and nesting values
     - allows deactivation of the rewriting of `#ifdefs` to get a 'pure' result
         - rewriting changes `#else` branches from no used constant to the
           negation of the corresponding `#if` clause
     - returns a list for each characteristic, which `#ifdef` or configuration
       constant has which value (merged and unmerged)
         - unmerged: each `#ifdef` expression is counted once per file
         - merged: each `#ifdef` expression is counted once per project

* `DISCIPLINE`
    - Analysis of the discipline of used CPP annotations
    - returns the number of occurences for the categories listed below
        - (1) check top level siblings (compilation unit)'
        - (2) check sibling (excludes check top level siblings; NOT CLASSIFIED)'
        - (4) check if-then enframement (wrapper)'
        - (8) check case enframement (conditional)'
        - (16) check else-if enframement (conditional)
        - (32) check param/argument enframement (parameter)
        - (64) check expression enframement (expression)
        - (128) check else enframement (NOT CLASSIFIED)

* `FEATURELOCATIONS`
    - Analysis of the locations of CPP annotation blocks in the given
      file or project folder
    - returns a table with the following headers:
        - file
        - starting line
        - end line
        - type of the annotation (`#if`, `#elif`, `#else`)
        - the `#ifdef` expression
        -- involved configuration constants

* `DERIVATIVE`
    - Analysis of all derivatives in the given project folder
    - returns all CPP annotations that involve shared code (expression
      contains `&&`)

* `INTERACTION`
    - Analysis of pair-wise interactions of configurations constants
      that have been used alltogether in one expression (# of constants
      involved >= 3)
    - (A, B, C) -> |(A, B)? (A, C)? (B, C)? ...|

## General Notes

* When cppstats computes general stats (`--kind general` parameter), the reported granularity
  function level (GRANFL) also accounts for conditional elements within an array initialization 
  or conditional field initializations when creating a struct variable. Example (for array):

  ```c
  static const struct squashfs_decompressor *decompressor[] = {
    &squashfs_zlib_comp_ops,
    &squashfs_lzma_unsupported_comp_ops,
    #if defined(CONFIG_SQUASHFS_LZO)
    &squashfs_lzo_comp_ops,
    #else
    &squashfs_lzo_unsupported_comp_ops,
    #endif
    &squashfs_unknown_comp_ops
  };
  ```

  The rationale behind such decision is that array/struct instance initializations can be interpreted 
  as constructor procedure calls.
