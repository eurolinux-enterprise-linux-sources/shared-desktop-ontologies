# Try to find DocBook XSL-NS stylesheet
# Once done, it will define:
#
#  DOCBOOKXSLNS_FOUND - system has the required DocBook XML-NS DTDs
#  DOCBOOKXSLNS_DIR - the directory containing the stylesheets
#  used to process DocBook XML-NS

# Copyright (c) 2010, Luigi Toscano, <luigi.toscano@tiscali.it>
# Copyright (c) 2011, Daniele E. Domenichelli <daniele.domenichelli@gmail.com>
#
# Redistribution and use is allowed according to the terms of the BSD license.
# For details see the accompanying COPYING-CMAKE-SCRIPTS file.

set (_STYLESHEET_PATH_LIST
    share/xml/docbook/stylesheet/docbook-xsl-ns
    share/xml/docbook/xsl-stylesheets
    share/sgml/docbook/xsl-stylesheets
    share/sgml/docbook/xsl-ns-stylesheet
    share/xsl/docbook-xsl-ns
)

find_path (DOCBOOKXSLNS_DIR lib/lib.xsl
   PATHS ${CMAKE_SYSTEM_PREFIX_PATH}
   PATH_SUFFIXES ${_STYLESHEET_PATH_LIST}
)

if (NOT DOCBOOKXSLNS_DIR)
   # hacks for systems that put the version in the stylesheet dirs
   set (_STYLESHEET_PATH_LIST)
   foreach (_STYLESHEET_PREFIX_ITER ${CMAKE_SYSTEM_PREFIX_PATH})
      file(GLOB _STYLESHEET_SUFFIX_ITER RELATIVE ${_STYLESHEET_PREFIX_ITER}
           ${_STYLESHEET_PREFIX_ITER}/share/xml/docbook/xsl-stylesheets-*
      )
      if (_STYLESHEET_SUFFIX_ITER)
         list (APPEND _STYLESHEET_PATH_LIST ${_STYLESHEET_SUFFIX_ITER})
      endif ()
   endforeach ()

   find_path (DOCBOOKXSLNS_DIR VERSION
      PATHS ${CMAKE_SYSTEM_PREFIX_PATH}
      PATH_SUFFIXES ${_STYLESHEET_PATH_LIST}
   )
endif (NOT DOCBOOKXSLNS_DIR)


include(FindPackageHandleStandardArgs)
find_package_handle_standard_args (DocBookXSLNS
                                   "Could NOT find DocBook XSL-NS stylesheets"
                                   DOCBOOKXSLNS_DIR)

mark_as_advanced (DOCBOOKXSLNS_DIR)
