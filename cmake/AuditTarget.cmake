# SPDX-License-Identifier: MPL-2.0

foreach(required_variable IN ITEMS BUILD_DIR SOURCE_DIR NM_TOOL STATIC_LIBRARY_SUFFIX)
  if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
    message(FATAL_ERROR "Target audit requires ${required_variable}.")
  endif()
endforeach()
if(NOT DEFINED STATIC_LIBRARY_PREFIX)
  set(STATIC_LIBRARY_PREFIX "")
endif()
file(WRITE "${BUILD_DIR}/DEPENDENCY_AUDIT.txt" "ARINC 615A TARGET DEPENDENCY AUDIT: NOT YET PASSED\n")

set(compile_database "${BUILD_DIR}/compile_commands.json")
if(NOT EXISTS "${compile_database}")
  message(FATAL_ERROR
    "Missing ${compile_database}; CMAKE_EXPORT_COMPILE_COMMANDS must remain enabled.")
endif()

file(READ "${compile_database}" compile_json)
string(JSON compile_count LENGTH "${compile_json}")
if(compile_count EQUAL 0)
  message(FATAL_ERROR "The compilation database is empty.")
endif()

set(target_source_count 0)
set(target_objects "")
math(EXPR compile_last "${compile_count} - 1")
foreach(index RANGE 0 ${compile_last})
  # Older CMake (e.g. 3.25) may omit "output"; fall back to the command's -o.
  string(JSON output ERROR_VARIABLE output_error GET "${compile_json}" ${index} output)
  if(output_error)
    string(JSON command GET "${compile_json}" ${index} command)
    string(REGEX MATCH "(^| )-o +([^ ]+)" _ "${command}")
    set(output "${CMAKE_MATCH_2}")
  endif()
  if(NOT output MATCHES
      "CMakeFiles/(arinc_665|tftp|arinc_615a|arinc_615a_tha_target)\\.dir/")
    continue()
  endif()

  math(EXPR target_source_count "${target_source_count} + 1")
  # CMake 4 records absolute outputs; Ninja names its targets relative to the
  # build directory, so `ninja -t deps` needs the relative form.
  if(IS_ABSOLUTE "${output}")
    file(RELATIVE_PATH output "${BUILD_DIR}" "${output}")
  endif()
  list(APPEND target_objects "${output}")
  string(JSON command GET "${compile_json}" ${index} command)
  string(JSON source_file GET "${compile_json}" ${index} file)
  string(TOLOWER "${command}" command_lower)
  string(TOLOWER "${source_file}" source_lower)

  if(NOT command MATCHES "(^|[ ;])-DARINC_ENABLE_COMMAND_LINE=0([ ;]|$)")
    message(FATAL_ERROR
      "Target source was not compiled with ARINC_ENABLE_COMMAND_LINE=0: ${source_file}")
  endif()
  if(command MATCHES "-DARINC_ENABLE_COMMAND_LINE=1")
    message(FATAL_ERROR "Desktop command-line mode leaked into: ${source_file}")
  endif()
  if(NOT command MATCHES "(^|[ ;])-std=c\\+\\+17([ ;]|$)")
    message(FATAL_ERROR "Target source was not compiled as C++17: ${source_file}")
  endif()
  if(command MATCHES "-std=c\\+\\+20")
    message(FATAL_ERROR "C++20 leaked into the VxWorks target graph: ${source_file}")
  endif()

  if(source_lower MATCHES
      "/(helper|arinc[-_]649|arinc_615a_qt|arinc_615a_dla_qt|qt_icon_resources|commands)/")
    message(FATAL_ERROR "Excluded source entered the target build: ${source_file}")
  endif()
  if(command_lower MATCHES
      "(/helper/|/arinc[-_]649/|/arinc_615a(_dla)?_qt/|/qt_icon_resources/|/boost/program_options/|/libxml)")
    message(FATAL_ERROR "Excluded include/dependency entered the target command: ${source_file}")
  endif()
endforeach()

if(target_source_count EQUAL 0)
  message(FATAL_ERROR "No target compilation entries were found to audit.")
endif()

set(archive_names arinc_665 tftp arinc_615a arinc_615a_tha_target)
set(undefined_symbols "")
set(archive_report "")
foreach(archive_name IN LISTS archive_names)
  set(archive
    "${BUILD_DIR}/${STATIC_LIBRARY_PREFIX}${archive_name}${STATIC_LIBRARY_SUFFIX}")
  if(NOT EXISTS "${archive}")
    message(FATAL_ERROR "Required target archive is missing: ${archive}")
  endif()
  file(SIZE "${archive}" archive_size)
  string(APPEND archive_report "  ${archive_name}: ${archive_size} bytes\n")

  execute_process(
    COMMAND "${NM_TOOL}" -u -C "${archive}"
    RESULT_VARIABLE nm_result
    OUTPUT_VARIABLE nm_output
    ERROR_VARIABLE nm_error)
  if(NOT nm_result EQUAL 0)
    message(FATAL_ERROR "Unable to inspect ${archive} with ${NM_TOOL}: ${nm_error}")
  endif()
  string(APPEND undefined_symbols "\n===== ${archive_name} =====\n${nm_output}")
endforeach()

file(WRITE "${BUILD_DIR}/target-undefined-symbols.txt" "${undefined_symbols}")
if(undefined_symbols MATCHES
    "(Helper::|Arinc649|arinc_649|arinc-649|boost::program_options|program_options|spdlog::|fmt::|xmlpp::|QCoreApplication|QApplication|QWidget|QString|libgit)")
  message(FATAL_ERROR
    "An excluded external symbol was found. See ${BUILD_DIR}/target-undefined-symbols.txt")
endif()

set(dependency_scan "not available for generator '${GENERATOR}'")
if(GENERATOR MATCHES "Ninja" AND DEFINED MAKE_PROGRAM AND EXISTS "${MAKE_PROGRAM}")
  execute_process(
    COMMAND "${MAKE_PROGRAM}" -C "${BUILD_DIR}" -t deps ${target_objects}
    RESULT_VARIABLE deps_result
    OUTPUT_VARIABLE dependency_output
    ERROR_VARIABLE deps_error)
  if(NOT deps_result EQUAL 0)
    message(FATAL_ERROR "Ninja dependency inspection failed: ${deps_error}")
  endif()
  file(WRITE "${BUILD_DIR}/target-header-dependencies.txt" "${dependency_output}")
  if(dependency_output MATCHES "deps not found" OR NOT dependency_output MATCHES "#deps [1-9]")
    message(FATAL_ERROR "Ninja header dependencies are missing; rebuild before auditing.")
  endif()
  string(TOLOWER "${dependency_output}" dependency_output_lower)
  if(dependency_output_lower MATCHES
      "(/helper/|/arinc[-_]649/|/arinc_615a(_dla)?_qt/|/qt_icon_resources/|/boost/program_options/|/commands/|/libxml)")
    message(FATAL_ERROR
      "An excluded header dependency was found. See ${BUILD_DIR}/target-header-dependencies.txt")
  endif()
  set(dependency_scan "passed (Ninja compiler dependency database)")
endif()

file(WRITE "${BUILD_DIR}/DEPENDENCY_AUDIT.txt"
  "ARINC 615A TARGET DEPENDENCY AUDIT: PASS\n"
  "\n"
  "Source: ${SOURCE_DIR}\n"
  "Build:  ${BUILD_DIR}\n"
  "Target translation units checked: ${target_source_count}\n"
  "Header dependency scan: ${dependency_scan}\n"
  "\n"
  "Required target archives:\n${archive_report}"
  "\n"
  "Verified absent from the target build:\n"
  "  external Helper library\n"
  "  ARINC 649\n"
  "  Qt and GUI sources\n"
  "  Boost.Program_options and desktop commands\n"
  "  spdlog, fmt, libxml++, and libgit\n"
  "\n"
  "Boost 1.88+ headers remain an intentional SDK/header dependency.\n"
  "ARINC 665, TFTP, local support headers, and checksum sources are intentional.\n"
  "Production translation units were compiled as C++17.\n"
  "A matching VxWorks 24.03 SDK/VSB/BSP build and on-target test are still required.\n")

message(STATUS
  "ARINC target dependency audit passed; report: ${BUILD_DIR}/DEPENDENCY_AUDIT.txt")
