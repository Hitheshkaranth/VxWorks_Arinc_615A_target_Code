# SPDX-License-Identifier: MPL-2.0
function(arinc_extract_boost source_root destination)
  set(archive "${source_root}/third_party/boost_1_88_0_headers.tar.gz")
  file(SHA256 "${archive}" actual)
  if(NOT actual STREQUAL "e166e0cdc01b18c9852c59bad215e6e7d1cdb6532543ccec80a3fa43c80387b6")
    message(FATAL_ERROR "Bundled Boost archive is damaged; copy the complete ARINC folder again.")
  endif()
  if(NOT EXISTS "${destination}/boost/version.hpp")
    message(STATUS "Extracting bundled Boost 1.88 headers (offline)")
    file(MAKE_DIRECTORY "${destination}")
    file(ARCHIVE_EXTRACT INPUT "${archive}" DESTINATION "${destination}")
  endif()

  # Whole-file VxWorks fixes from the office build (poll() shim over select(),
  # socketpair() over TCP loopback, #undef of the mbuf.h m_data macro). They
  # are copied over the pristine headers first; socket_types.hpp already holds
  # the selectLib.h branch, so the probe patch below recognises it and skips.
  file(COPY "${source_root}/third_party/boost_vxworks_overlay/boost"
       DESTINATION "${destination}")

  # Boost.Asio 1.88 assumes every non-Windows, non-Symbian platform has
  # sys/poll.h. VxWorks 24.03 uses the select reactor for this target and does
  # not ship that header. Keep the upstream header unchanged in the archive,
  # then apply this deterministic target-only compatibility branch to the
  # extracted offline copy.
  set(socket_types "${destination}/boost/asio/detail/socket_types.hpp")
  file(READ "${socket_types}" socket_types_content)
  set(poll_probe "# elif !defined(__SYMBIAN32__)\n#  include <sys/poll.h>")
  set(vxworks_probe "# elif defined(__VXWORKS__) || defined(__vxworks)\n#  include <selectLib.h>\n# elif !defined(__SYMBIAN32__)\n#  include <sys/poll.h>")
  if(NOT socket_types_content MATCHES "defined\\(__VXWORKS__\\) \\|\\| defined\\(__vxworks\\)")
    string(FIND "${socket_types_content}" "${poll_probe}" poll_probe_position)
    if(poll_probe_position EQUAL -1)
      message(FATAL_ERROR "Bundled Boost.Asio socket_types.hpp has an unexpected layout.")
    endif()
    string(REPLACE "${poll_probe}" "${vxworks_probe}" socket_types_content "${socket_types_content}")
    file(WRITE "${socket_types}" "${socket_types_content}")
  endif()

  # On other POSIX platforms Asio wakes the select reactor through pipe(),
  # which a VxWorks image without INCLUDE_POSIX_PIPES cannot resolve at DKM
  # load. ARINC_ASIO_SOCKET_SELECT_INTERRUPTER (set by BuildConfig.hpp for
  # VxWorks) selects Asio's loopback-socket interrupter, as Cygwin does.
  set(interrupter_marker "defined(ARINC_ASIO_SOCKET_SELECT_INTERRUPTER)")
  foreach(header select_interrupter.hpp socket_select_interrupter.hpp impl/socket_select_interrupter.ipp)
    set(path "${destination}/boost/asio/detail/${header}")
    file(READ "${path}" content)
    if(NOT content MATCHES "ARINC_ASIO_SOCKET_SELECT_INTERRUPTER")
      string(FIND "${content}" "defined(__CYGWIN__)" position)
      if(position EQUAL -1)
        message(FATAL_ERROR "Bundled Boost.Asio ${header} has an unexpected layout.")
      endif()
      string(REPLACE "defined(__CYGWIN__)" "defined(__CYGWIN__) || ${interrupter_marker}" content "${content}")
      file(WRITE "${path}" "${content}")
    endif()
  endforeach()
  foreach(header pipe_select_interrupter.hpp impl/pipe_select_interrupter.ipp)
    set(path "${destination}/boost/asio/detail/${header}")
    file(READ "${path}" content)
    if(NOT content MATCHES "ARINC_ASIO_SOCKET_SELECT_INTERRUPTER")
      string(FIND "${content}" "#if !defined(__CYGWIN__)" position)
      if(position EQUAL -1)
        message(FATAL_ERROR "Bundled Boost.Asio ${header} has an unexpected layout.")
      endif()
      string(REPLACE "#if !defined(__CYGWIN__)" "#if !defined(__CYGWIN__) && !${interrupter_marker}" content "${content}")
      file(WRITE "${path}" "${content}")
    endif()
  endforeach()
endfunction()
