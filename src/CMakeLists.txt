# required by cmake
cmake_minimum_required(VERSION 2.6)

project(shared-desktop-ontologies NONE)


# set the version to be used by SharedDesktopOntologiesConfig.cmake
# ===============================================================================================
set(SHAREDDESKTOPONTOLOGIES_VERSION_MAJOR 0)
set(SHAREDDESKTOPONTOLOGIES_VERSION_MINOR 11)
set(SHAREDDESKTOPONTOLOGIES_VERSION_RELEASE 0)
set(SHAREDDESKTOPONTOLOGIES_VERSION "${SHAREDDESKTOPONTOLOGIES_VERSION_MAJOR}.${SHAREDDESKTOPONTOLOGIES_VERSION_MINOR}.${SHAREDDESKTOPONTOLOGIES_VERSION_RELEASE}")


# set the root dir to be used by SharedDesktopOntologiesConfig.cmake
# ===============================================================================================
set(SHAREDDESKTOPONTOLOGIES_ROOT_DIR "${CMAKE_INSTALL_PREFIX}/share/ontology")

# find packages needed to generate the documentation
# ===============================================================================================
set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake/modules")
find_package(DocBookXSLNS)

# generate SharedDesktopOntologiesConfig.cmake for easy utilisation of the package by other cmake build systems
# ===============================================================================================
configure_file(SharedDesktopOntologiesConfig.cmake.in ${CMAKE_CURRENT_BINARY_DIR}/SharedDesktopOntologiesConfig.cmake @ONLY)
configure_file(SharedDesktopOntologiesConfigVersion.cmake.in ${CMAKE_CURRENT_BINARY_DIR}/SharedDesktopOntologiesConfigVersion.cmake @ONLY)
install(FILES
  ${CMAKE_CURRENT_BINARY_DIR}/SharedDesktopOntologiesConfig.cmake
  ${CMAKE_CURRENT_BINARY_DIR}/SharedDesktopOntologiesConfigVersion.cmake
  DESTINATION ${CMAKE_INSTALL_PREFIX}/share/cmake/SharedDesktopOntologies)


# optionally install the pkgconfig stuff
# ===============================================================================================
if(NOT WIN32)
  set(PKGCONFIG_INSTALL_DIR "share/pkgconfig/" CACHE STRING "Base directory for pkgconfig files")
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/shared-desktop-ontologies.pc.cmake ${CMAKE_CURRENT_BINARY_DIR}/shared-desktop-ontologies.pc @ONLY)
  install(FILES ${CMAKE_CURRENT_BINARY_DIR}/shared-desktop-ontologies.pc DESTINATION ${PKGCONFIG_INSTALL_DIR})
endif(NOT WIN32)


# install all the ontologies
# ===============================================================================================
macro(INSTALL_ONTOLOGY _dir _name _group)
  # the basic stuff
  set(ONTO_INSTALL_DIR ${CMAKE_INSTALL_PREFIX}/share/ontology/${_group})
  configure_file("${_dir}/${_name}.trig.in" "${CMAKE_CURRENT_BINARY_DIR}/${_dir}/${_name}.trig")
  configure_file("${_dir}/${_name}.ontology.in" "${CMAKE_CURRENT_BINARY_DIR}/${_dir}/${_name}.ontology")

  # the documentation with a bit of hacky magic
  if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${_dir}/${_name}-main.docbook)
    # we need to copy over the docbook files to make sure xsltproc finds the includes
    configure_file("${_dir}/${_name}-main.docbook" "${CMAKE_CURRENT_BINARY_DIR}/docs/${_name}-main.docbook")
    configure_file("${_dir}/${_name}-authors.docbook" "${CMAKE_CURRENT_BINARY_DIR}/docs/${_name}-authors.docbook")

    # remember a few things in lists so we can reuse them later on when building the html pages
    list(APPEND ontology_trig_sources "${CMAKE_CURRENT_BINARY_DIR}/${_dir}/${_name}.trig")
    list(APPEND ontology_docbook_references "${CMAKE_CURRENT_BINARY_DIR}/docs/${_name}-reference.docbook")
  endif()
  install(FILES "${CMAKE_CURRENT_BINARY_DIR}/${_dir}/${_name}.ontology" DESTINATION ${ONTO_INSTALL_DIR})
  install(FILES "${CMAKE_CURRENT_BINARY_DIR}/${_dir}/${_name}.trig" DESTINATION ${ONTO_INSTALL_DIR})
endmacro(INSTALL_ONTOLOGY)

# base ontologies
install_ontology(base rdf core)
install_ontology(base rdfs core)

option(ENABLE_DCMI
       "enable DCMI ontologies. This installs DCMI ontologies (http:  dublincore.org )." ON)
if(ENABLE_DCMI)
  install_ontology(base dcterms dc)
  install_ontology(base dctype dc)
  install_ontology(base dces dc)
endif(ENABLE_DCMI)

# Nepomuk base ontologies
install_ontology(nrl nrl nepomuk)
install_ontology(nao nao nepomuk)

# NIE
install_ontology(nie nie nie)
install_ontology(nfo nfo nie)
install_ontology(ncal ncal nie)
install_ontology(nmo nmo nie)
install_ontology(nco nco nie)
install_ontology(nexif nexif nie)
install_ontology(nmm nmm nie)
install_ontology(nid3 nid3 nie)

# Nepomuk extras
install_ontology(pimo pimo pimo)
install_ontology(tmo tmo pimo)
install_ontology(nso nso nepomuk)
install_ontology(ndo ndo nepomuk)
install_ontology(nuao nuao nepomuk)


# Generate the documentation
# Caution: we need to put this command at the end since it depends on the ontology_docbook_references variable which
# is only populated by the install_ontology calls above
# ===============================================================================================
# TODO: how about adding the additional files required for the docs to the install_ontology macro instead of this hack?
file(GLOB_RECURSE _doc_files_the_hacky_way_ "${CMAKE_CURRENT_SOURCE_DIR}/*.png" "${CMAKE_CURRENT_SOURCE_DIR}/*.ttl")
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/docs/ontology.docbook.template ${CMAKE_CURRENT_BINARY_DIR}/docs/ontology.docbook.template @ONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/docs/sdo.docbook ${CMAKE_CURRENT_BINARY_DIR}/docs/sdo.docbook)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/docs/sdo-docbook.xsl.cmake ${CMAKE_CURRENT_BINARY_DIR}/docs/sdo-docbook.xsl)
add_custom_target(
  docsprep
  COMMENT "Preparing Ontology Documentation Files..."
  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
  COMMAND mkdir -p ${CMAKE_CURRENT_BINARY_DIR}/docs/html
  COMMAND cp ${CMAKE_CURRENT_SOURCE_DIR}/docs/sdo.css ${CMAKE_CURRENT_BINARY_DIR}/docs/html
  COMMAND cp ${_doc_files_the_hacky_way_} ${CMAKE_CURRENT_BINARY_DIR}/docs/html
)
add_custom_target(
  docrefs
  COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/docs/build-ontology-reference.py ${CMAKE_CURRENT_BINARY_DIR}/docs ${ontology_trig_sources}
  COMMENT "Writing Ontology References..."
  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/docs
)
add_custom_target(
  docs
  COMMAND xsltproc --xinclude ${CMAKE_CURRENT_BINARY_DIR}/docs/sdo-docbook.xsl ${CMAKE_CURRENT_BINARY_DIR}/docs/sdo.docbook
  COMMENT "Writing Ontology Documentation..."
  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/docs
)
add_dependencies(docrefs docsprep)
add_dependencies(docs docrefs)
