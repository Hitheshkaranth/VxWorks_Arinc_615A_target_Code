/* SPDX-License-Identifier: MPL-2.0
 *
 * STUB, NOT A WIND RIVER HEADER.
 *
 * Minimal approximation of the VxWorks 7 kernel header surface that
 * lib/arinc_support/BuildConfig.hpp and BoostVxWorks.hpp consume. It exists
 * only so a host compiler can syntax-check the __VXWORKS__ branch of the
 * production graph, which is otherwise never compiled off-target.
 *
 * It is NOT used by any production translation unit, is NOT shipped in the
 * office handoff, and is NOT a substitute for the licensed VxWorks 24.03 SDK.
 * A pass here does not predict a successful Workbench build; see README.md.
 */
#ifndef SOCKLIB_STUB_H
#define SOCKLIB_STUB_H
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
/* The real sockLib.h reaches mbuf.h, which defines this macro. It rewrites
   Boost.PropertyTree member names unless BuildConfig.hpp removes it. */
#define m_data m_hdr.mh_data
#endif
