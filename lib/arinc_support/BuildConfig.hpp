// SPDX-License-Identifier: MPL-2.0
#ifndef ARINC_BUILD_CONFIG_HPP
#define ARINC_BUILD_CONFIG_HPP
// Force-include for a native Workbench managed DKM build.
#ifndef ARINC_ENABLE_COMMAND_LINE
#define ARINC_ENABLE_COMMAND_LINE 0
#endif
#define BOOST_ALL_NO_LIB
#define BOOST_ASIO_NO_DEPRECATED
#if defined(__VXWORKS__) || defined(__vxworks)
#include <vxWorks.h>
#include <sockLib.h>
#include <ioLib.h>
#include <sysLib.h>
#include <selectLib.h>
// sockLib.h pulls in mbuf.h, whose m_data macro rewrites Boost.PropertyTree
// member names in every later header.
#ifdef m_data
#undef m_data
#endif
#ifndef _WRS_KERNEL
#error "Select a VxWorks Downloadable Kernel Module project, not an RTP project."
#endif
// Avoid obsolete Boost platform stubs for truncate/symlink/readlink. Modern
// VxWorks supplies its own POSIX/UNIX compatibility declarations.
#define BOOST_PLATFORM_CONFIG <arinc_support/BoostVxWorks.hpp>
#define BOOST_ASIO_DISABLE_EPOLL
#define BOOST_ASIO_DISABLE_KQUEUE
#define BOOST_ASIO_DISABLE_DEV_POLL
#define BOOST_ASIO_DISABLE_SERIAL_PORT
#define BOOST_ASIO_DISABLE_LOCAL_SOCKETS
#define BOOST_ASIO_HAS_PTHREADS 1
// Boost.Asio's default POSIX wake-up for the select reactor calls pipe(), which
// needs INCLUDE_POSIX_PIPES. The office image omits it, so a DKM load would
// leave pipe() unresolved. Wake the reactor through a loopback TCP pair
// instead (patched into the bundled Asio headers; see BundledBoost.cmake).
#define ARINC_ASIO_SOCKET_SELECT_INTERRUPTER 1
#endif
#endif
