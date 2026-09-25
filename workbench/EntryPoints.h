// SPDX-License-Identifier: MPL-2.0
#ifndef ARINC_WORKBENCH_ENTRY_POINTS_H
#define ARINC_WORKBENCH_ENTRY_POINTS_H
#ifdef __cplusplus
extern "C" {
#endif
/* Workbench task entry: blocks until arinc615aStop() is called. */
int arinc615aDemo(void);
/* Run with your target-side JSON file, in a worker/debug task. */
int arinc615aRun(const char *json_filename);
int arinc615aStop(void);
/* Runs basic codec/hash/C++ checks; returns zero on success. */
int arinc615aSelfTest(void);
/* Acceptance-test helpers (see VXWORKS_TEST_PROCEDURE.md). root is a writable
 * target directory, e.g. "/ram0/arinc"; all return zero on success. */
int arinc615aPrepareTest(const char *root_directory);
int arinc615aVerifyTestUpload(const char *root_directory);
int arinc615aWriteFixtures(const char *directory);
#ifdef __cplusplus
}
#endif
#endif
