# SPDX-License-Identifier: MPL-2.0
cmake_minimum_required(VERSION 3.24)
project(arinc_615a LANGUAGES C CXX)

include(GNUInstallDirs)
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
option(ARINC615A_THA_BUILD_TEST_APPLICATION "Build the original desktop CLI" OFF)
option(ARINC_BUILD_TESTS "Build host regression tests; never included in the DKM" OFF)
option(ARINC_ENABLE_COMMAND_LINE "Retain Boost.Program_options APIs for desktop callers" ${ARINC615A_THA_BUILD_TEST_APPLICATION})
set(ARINC665_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/arinc_665" CACHE PATH "Bundled ARINC 665 sources")
if(CMAKE_SYSTEM_NAME STREQUAL "VxWorks" AND (ARINC615A_THA_BUILD_TEST_APPLICATION OR ARINC_ENABLE_COMMAND_LINE OR ARINC_BUILD_TESTS))
  message(FATAL_ERROR "The VxWorks DKM uses runFromFile/run(configuration); desktop CLI and host tests must be OFF.")
endif()
if(ARINC615A_THA_BUILD_TEST_APPLICATION AND NOT ARINC_ENABLE_COMMAND_LINE)
  message(FATAL_ERROR "The desktop test application requires ARINC_ENABLE_COMMAND_LINE=ON.")
endif()
include(cmake/OfflineLibraries.cmake)
arinc_configure_support("${CMAKE_CURRENT_SOURCE_DIR}")
arinc_add_665("${ARINC665_SOURCE_DIR}")
arinc_add_tftp()
arinc_add_615a()

set(tha_dir "${CMAKE_CURRENT_SOURCE_DIR}/app/arinc_615a_unit_test/arinc_615a_test_tha")
add_library(arinc_615a_tha_target STATIC
  "${tha_dir}/arinc_615a_test_tha.cpp"
  "${tha_dir}/ThaC.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/workbench/EntryPoints.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/workbench/TestSupport.cpp"
  "${tha_dir}/DownloadOperationConfiguration.cpp"
  "${tha_dir}/InformationOperationConfiguration.cpp"
  "${tha_dir}/OperationConfiguration.cpp"
  "${tha_dir}/TargetDataLoaderConfiguration.cpp"
  "${tha_dir}/TargetInformationOperation.cpp"
  "${tha_dir}/TargetMediaDefinedDownloadOperation.cpp"
  "${tha_dir}/TargetOperatorDefinedDownloadOperation.cpp"
  "${tha_dir}/TargetUploadOperation.cpp"
  "${tha_dir}/UploadOperationConfiguration.cpp")
target_include_directories(arinc_615a_tha_target PUBLIC "$<BUILD_INTERFACE:${tha_dir}>" "$<INSTALL_INTERFACE:include/arinc_615a_tha>")
target_link_libraries(arinc_615a_tha_target PUBLIC arinc_615a arinc_665)
if(ARINC_ENABLE_COMMAND_LINE)
  target_sources(arinc_615a_tha_target PRIVATE "${tha_dir}/ThaCommandLine.cpp")
endif()

# Keep the target build independent of the original desktop-only dependency
# graph.  This audit inspects the actual compilation database, generated
# dependency data, and target archives instead of relying on source layout or
# documentation alone.
add_custom_target(arinc_target_audit
  COMMAND "${CMAKE_COMMAND}"
    "-DBUILD_DIR=${CMAKE_BINARY_DIR}"
    "-DSOURCE_DIR=${CMAKE_SOURCE_DIR}"
    "-DNM_TOOL=${CMAKE_NM}"
    "-DMAKE_PROGRAM=${CMAKE_MAKE_PROGRAM}"
    "-DGENERATOR=${CMAKE_GENERATOR}"
    "-DSTATIC_LIBRARY_PREFIX=${CMAKE_STATIC_LIBRARY_PREFIX}"
    "-DSTATIC_LIBRARY_SUFFIX=${CMAKE_STATIC_LIBRARY_SUFFIX}"
    -P "${CMAKE_SOURCE_DIR}/cmake/AuditTarget.cmake"
  DEPENDS arinc_615a_tha_target arinc_615a arinc_665 tftp
  COMMENT "Auditing the offline ARINC 615A target dependency closure"
  VERBATIM)

# The __VXWORKS__ branch of BuildConfig.hpp and BoostVxWorks.hpp is never
# compiled by an ordinary host build, so it would otherwise reach the office
# untested.  This target compiles the whole production graph with the VxWorks
# macros defined, against stub SDK headers, and asserts that Boost selects the
# VxWorks platform profile, the select reactor and the patched Asio include
# chain.  It is a host syntax check, not a substitute for a Workbench build.
if(NOT CMAKE_SYSTEM_NAME STREQUAL "VxWorks"
   AND CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  find_package(Python3 COMPONENTS Interpreter)
  if(Python3_FOUND)
    add_custom_target(arinc_vxworks_preflight
      COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_SOURCE_DIR}/tests/vxworks_preflight/preflight.py"
        "--build" "${CMAKE_BINARY_DIR}"
        "--compiler" "${CMAKE_CXX_COMPILER}"
        "--sysroot" "${CMAKE_OSX_SYSROOT}"
      COMMENT "Syntax-checking the VxWorks branch of the production graph"
      VERBATIM)
  endif()
endif()

if(ARINC615A_THA_BUILD_TEST_APPLICATION)
  add_executable(arinc_615a_test_tha "${tha_dir}/main.cpp")
  target_link_libraries(arinc_615a_test_tha PRIVATE arinc_615a_tha_target)
  configure_file("${tha_dir}/arinc_615a_test_tha.json.template" arinc_615a_test_tha.json COPYONLY)
endif()
install(TARGETS arinc_615a_tha_target arinc_615a arinc_665 tftp arinc_build_config EXPORT arinc-offline-targets ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
if(TARGET arinc_cli_options)
  install(TARGETS arinc_cli_options EXPORT arinc-offline-targets ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
endif()
install(EXPORT arinc-offline-targets NAMESPACE Arinc:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/arinc-offline)
install(DIRECTORY "${tha_dir}/" DESTINATION include/arinc_615a_tha FILES_MATCHING PATTERN "*.hpp" PATTERN "*.h")
install(DIRECTORY lib/arinc_615a lib/tftp lib/arinc_support lib/arinc_checksum DESTINATION include
  FILES_MATCHING PATTERN "*.hpp" PATTERN "*.h" PATTERN "*.ipp"
  PATTERN "test" EXCLUDE PATTERN "host" EXCLUDE
  PATTERN "BoostAsioProgramOptions.hpp" EXCLUDE)
if(ARINC_ENABLE_COMMAND_LINE)
  install(FILES lib/arinc_support/BoostAsioProgramOptions.hpp DESTINATION include/arinc_support)
endif()
install(DIRECTORY "${ARINC665_SOURCE_DIR}/lib/arinc_665/" DESTINATION include/arinc_665
  FILES_MATCHING PATTERN "*.hpp" PATTERN "test" EXCLUDE PATTERN "media" EXCLUDE PATTERN "utils" EXCLUDE)
install(DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/include/" DESTINATION include)
install(FILES
  third_party_licenses/boost.BSL-1.0.txt
  third_party_licenses/checksums.MPL-2.0.txt
  third_party_licenses/tftp.MPL-2.0.txt
  DESTINATION ${CMAKE_INSTALL_DATADIR}/arinc/licenses)
# The local arinc_support headers retain the license of the source they were
# adapted from, but there is no external Helper archive or include dependency.
install(FILES third_party_licenses/helper.MPL-2.0.txt
  DESTINATION ${CMAKE_INSTALL_DATADIR}/arinc/licenses
  RENAME arinc_support.MPL-2.0.txt)
install(FILES LICENSE DESTINATION ${CMAKE_INSTALL_DATADIR}/arinc/licenses RENAME arinc_615a.LICENSE)
install(FILES "${ARINC665_SOURCE_DIR}/LICENSE" DESTINATION ${CMAKE_INSTALL_DATADIR}/arinc/licenses RENAME arinc_665.LICENSE)
install(FILES "${CMAKE_BINARY_DIR}/DEPENDENCY_AUDIT.txt"
  DESTINATION ${CMAKE_INSTALL_DATADIR}/arinc OPTIONAL)
if(ARINC_BUILD_TESTS)
  enable_testing()
  include(cmake/RegressionTests.cmake)
endif()
include(cmake/WorkbenchPackage.cmake)
